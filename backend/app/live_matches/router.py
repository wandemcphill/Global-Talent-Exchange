from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status

from app.auth.dependencies import get_current_match_user, get_current_social_user
from app.broadcast_network.commentary_service import CommentaryOrchestratorService
from app.broadcast_rights.service import BroadcastRightsError, BroadcastRightsService
from app.commentary.schemas import CommentaryStreamResponse
from app.commentary.service import CommentaryService
from app.live_matches.highlights import SmartHighlightService
from app.live_matches.schemas import (
    MatchHighlightResponseView,
    MatchHighlightShareItemView,
    MatchHighlightSharePackageView,
    LiveMatchSpeedModeView,
    SpectatorSessionView,
)
from app.live_matches.service import LiveMatchError, ensure_live_match_hub
from app.infinite_league.service import ensure_infinite_league_runtime
from app.match_engine.schemas import MatchReplayPayloadView
from app.models.manager_duel import ManagerDuel
from app.models.user import User
from app.realtime.service import commentary_topic, match_topic
from app.replay_archive.service import ensure_replay_archive
from app.services.device_fingerprint_service import DeviceFingerprintService
from app.ticketing.service import TicketingError, TicketingService

router = APIRouter(tags=["live-matches"])
legacy_router = APIRouter(prefix="/matches", tags=["live-matches"])
api_router = APIRouter(prefix="/api/matches", tags=["live-matches"])
match_router = APIRouter(prefix="/match", tags=["live-matches"])
api_match_router = APIRouter(prefix="/api/match", tags=["live-matches"])


def _generated_match_access_payload() -> dict[str, object]:
    return {
        "has_access": True,
        "access_source": "infinite_league",
        "viewing_fee_coin": 0,
        "premium_features": {
            "generated_commentary": True,
            "instant_replay": True,
        },
    }


def _bootstrap_infinite_league_stream(app, hub, match_id: str) -> bool:
    stream = ensure_infinite_league_runtime(app).live_stream(match_id)
    if stream is None:
        return False
    hub.start_synthetic_stream(
        match_id=stream.match_id,
        home_team_id=stream.home_team_id,
        away_team_id=stream.away_team_id,
        home_team_name=stream.home_team_name,
        away_team_name=stream.away_team_name,
        base_home_possession=stream.base_home_possession,
        base_away_possession=stream.base_away_possession,
        events=stream.events,
        atmosphere_profile=stream.atmosphere_profile,
        sync_strategy=stream.sync_strategy,
        checkpoint_interval_seconds=stream.checkpoint_interval_seconds,
        max_latency_ms=stream.max_latency_ms,
        read_only=True,
    )
    return True


def _build_session_view(match_id: str, item, access: dict[str, object] | None = None) -> SpectatorSessionView:
    payload = dict(access or {})
    return SpectatorSessionView(
        id=item.id,
        match_id=item.match_id,
        user_id=item.user_id,
        joined_at=item.joined_at,
        read_only=True,
        channel=f"match:{match_id}:events",
        websocket_path=f"/api/matches/{match_id}/stream?session_id={item.id}",
        commentary_websocket_path=f"/api/matches/{match_id}/commentary/stream?session_id={item.id}",
        audio_stem_websocket_path=f"/api/matches/{match_id}/audio/stems/stream?session_id={item.id}",
        presence_channel=f"match:{match_id}:events",
        presence_websocket_path=f"/ws/spectate/{match_id}",
        tts_websocket_path="/tts/live?voice=default",
        replay_route=f"/api/matches/{match_id}/replay",
        speed_modes=[
            LiveMatchSpeedModeView(key="normal", label="Normal", target_duration_seconds=90),
            LiveMatchSpeedModeView(key="fast", label="Fast", target_duration_seconds=30),
            LiveMatchSpeedModeView(key="turbo", label="Turbo", target_duration_seconds=10),
        ],
        access_source=payload.get("access_source"),
        rights_owner_id=payload.get("rights_owner_id"),
        viewing_fee_coin=payload.get("viewing_fee_coin") or 0,
        premium_features=dict(payload.get("premium_features") or {}),
        sponsored_overlays=list(payload.get("sponsored_overlays") or []),
        stadium_ads=list(payload.get("stadium_ads") or []),
        channel_context=dict(payload.get("channel_context") or {}),
        sync_strategy=str(payload.get("sync_strategy") or "deterministic_playback"),
        watch_party_enabled=bool(payload.get("watch_party_enabled", True)),
        reactions_enabled=bool(payload.get("reactions_enabled", True)),
    )


def _merge_session_access(base: dict[str, object] | None, overlay: dict[str, object] | None) -> dict[str, object] | None:
    if base is None and overlay is None:
        return None
    merged = dict(base or {})
    if overlay is None:
        return merged
    premium_features = dict(merged.get("premium_features") or {})
    premium_features.update(dict(overlay.get("premium_features") or {}))
    if premium_features:
        merged["premium_features"] = premium_features
    channel_context = dict(merged.get("channel_context") or {})
    channel_context.update(dict(overlay.get("channel_context") or {}))
    if channel_context:
        merged["channel_context"] = channel_context
    for key in ("sponsored_overlays", "stadium_ads"):
        base_items = list(merged.get(key) or [])
        base_items.extend(list(overlay.get(key) or []))
        if base_items:
            merged[key] = base_items
    for key in ("access_source", "rights_owner_id", "viewing_fee_coin", "sync_strategy", "watch_party_enabled", "reactions_enabled"):
        if key in overlay and overlay.get(key) is not None:
            merged[key] = overlay[key]
    return merged


def _resolve_attendee_access(
    request: Request,
    *,
    session,
    match_id: str,
    user_id: str,
) -> dict[str, object] | None:
    if session is not None:
        try:
            return TicketingService(session, app=request.app).resolve_attendee_access(
                match_id=match_id,
                user_id=user_id,
                consume=True,
            )
        except TicketingError:
            return None
    runtime = getattr(request.app.state, "ticketing_runtime", None)
    if runtime is None:
        return None
    return runtime.resolve_attendee_access_for_user_id(match_id=match_id, user_id=user_id, consume=True)


def _commentary_payload(events) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for event in events:
        line = str(event.commentary or event.metadata.get("description") or "").strip()
        if not line:
            continue
        payload.append(
            {
                "source_event_id": event.source_event_id,
                "sequence_id": event.sequence_id or event.sequence,
                "minute": event.minute,
                "event_type": str(event.source_event_type or event.metadata.get("raw_event_type") or event.event_type),
                "line": line,
                "team": event.team or event.metadata.get("team_name"),
                "player": event.player or event.metadata.get("player_name"),
                "context": dict(event.metadata.get("commentary_context") or {}),
                "cue": event.experience.commentary.model_dump(mode="json") if event.experience is not None and event.experience.commentary is not None else None,
            }
        )
    return payload


def _commentary_snapshot_payload(app, hub, *, match_id: str, user_id: str, status: str) -> dict[str, object]:
    session_factory = getattr(app.state, "session_factory", None)
    if session_factory is None:
        return {"match_id": match_id, "status": status}
    with session_factory() as session:
        selection = CommentaryService(session, cache_backend=hub.cache_backend).resolve_selection_view(
            user_id=user_id,
            match_id=match_id,
        )
        return {
            "match_id": match_id,
            "status": status,
            "selection": selection.model_dump(mode="json"),
        }


def _commentary_response(
    app,
    hub,
    *,
    match_id: str,
    user_id: str,
    status: str,
    events,
    cursor: int,
    include_audio: bool = False,
) -> CommentaryStreamResponse | None:
    session_factory = getattr(app.state, "session_factory", None)
    if session_factory is None:
        return None
    with session_factory() as session:
        return CommentaryService(session, cache_backend=hub.cache_backend).render_stream(
            match_id=match_id,
            status=status,
            user_id=user_id,
            events=list(events),
            cursor=cursor,
            include_audio=include_audio,
        )


@legacy_router.post("/{match_id}/spectate", response_model=SpectatorSessionView)
@api_router.post("/{match_id}/spectate", response_model=SpectatorSessionView)
def join_spectate(
    match_id: str,
    request: Request,
    pay_to_view: bool = Query(default=False),
    current_user: User = Depends(get_current_match_user),
) -> SpectatorSessionView:
    access_payload: dict[str, object] | None = None
    hub = ensure_live_match_hub(request.app)
    is_generated_match = _bootstrap_infinite_league_stream(request.app, hub, match_id)
    if is_generated_match:
        access_payload = _generated_match_access_payload()
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        with session_factory() as session:
            if not is_generated_match:
                try:
                    service = BroadcastRightsService(session)
                    access_payload = service.resolve_match_access(
                        actor=current_user,
                        match_id=match_id,
                        pay_to_view=pay_to_view,
                    )
                    if not bool(access_payload.get("has_access", False)):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail={
                                "message": "Broadcast rights access is restricted for this match.",
                                "access": access_payload,
                            },
                        )
                except BroadcastRightsError as exc:
                    session.rollback()
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
            try:
                spectator_session = hub.join_spectate(match_id, current_user.id)
            except LiveMatchError as exc:
                session.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            access_payload = _merge_session_access(
                access_payload,
                _resolve_attendee_access(
                    request,
                    session=session,
                    match_id=match_id,
                    user_id=current_user.id,
                ),
            )
            session.commit()
            return _build_session_view(match_id, spectator_session, access_payload)
    try:
        spectator_session = hub.join_spectate(match_id, current_user.id)
    except LiveMatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    access_payload = _merge_session_access(
        access_payload,
        _resolve_attendee_access(
            request,
            session=None,
            match_id=match_id,
            user_id=current_user.id,
        ),
    )
    return _build_session_view(match_id, spectator_session, access_payload)


@legacy_router.get("/{match_id}/highlights", response_model=MatchHighlightResponseView)
@api_router.get("/{match_id}/highlights", response_model=MatchHighlightResponseView)
def read_match_highlights(match_id: str, request: Request) -> MatchHighlightResponseView:
    service = SmartHighlightService(getattr(request.app.state, "session_factory", None))
    highlights = service.list_highlights(match_id)
    if highlights:
        return MatchHighlightResponseView(highlights=highlights)

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        with session_factory() as session:
            duel = session.get(ManagerDuel, match_id)
            if duel is not None:
                replay_payload = (duel.metadata_json or {}).get("replay_payload")
                if isinstance(replay_payload, dict):
                    rebuilt = service.persist_from_replay_payload(
                        match_id,
                        MatchReplayPayloadView.model_validate(replay_payload),
                    )
                    return MatchHighlightResponseView(highlights=rebuilt)

    archive = ensure_replay_archive(request.app)
    record = archive.repository.get_latest_record(f"replay:{match_id}")
    if record is not None:
        rebuilt = service.persist_from_archive_timeline(match_id, record.timeline)
        return MatchHighlightResponseView(highlights=rebuilt)
    generated = ensure_infinite_league_runtime(request.app).highlight_response(match_id)
    if generated is not None:
        return generated
    return MatchHighlightResponseView(highlights=[])


@api_router.get("/{match_id}/highlights/share-package", response_model=MatchHighlightSharePackageView)
def get_match_highlight_share_package(
    match_id: str,
    request: Request,
    _: User = Depends(get_current_social_user),
) -> MatchHighlightSharePackageView:
    service = SmartHighlightService(getattr(request.app.state, "session_factory", None))
    highlights = service.list_highlights(match_id, limit=5)
    fingerprint = DeviceFingerprintService().build(headers=request.headers).fingerprint
    return MatchHighlightSharePackageView(
        match_id=match_id,
        fingerprint=fingerprint,
        hashtags=["#GTEX", "#MatchHighlight", "#Football"],
        recommended_aspect_ratios=["1:1", "9:16", "16:9"],
        export_route="/media-engine/share-exports",
        items=[
            MatchHighlightShareItemView(
                minute=item.minute,
                type=item.type,
                description=item.description,
                share_title=f"{item.type.replace('_', ' ').title()} in minute {item.minute}",
                share_caption=f"Minute {item.minute}: {item.description} #GTEX #MatchHighlight",
            )
            for item in highlights
        ],
    )


@legacy_router.get("/{match_id}/commentary/stream", response_model=CommentaryStreamResponse)
@api_router.get("/{match_id}/commentary/stream", response_model=CommentaryStreamResponse)
@match_router.get("/{match_id}/commentary/stream", response_model=CommentaryStreamResponse)
@api_match_router.get("/{match_id}/commentary/stream", response_model=CommentaryStreamResponse)
def get_match_commentary_stream(
    match_id: str,
    request: Request,
    session_id: str,
    include_audio: bool = Query(default=False),
    cursor: int = Query(default=0, ge=0),
    _: User = Depends(get_current_match_user),
) -> CommentaryStreamResponse:
    hub = ensure_live_match_hub(request.app)
    try:
        spectator_session = hub.validate_session(match_id, session_id)
    except LiveMatchError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    state = hub.get_state(match_id)
    if state is None and _bootstrap_infinite_league_stream(request.app, hub, match_id):
        state = hub.get_state(match_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match stream was not found.")

    events, next_cursor = hub.get_events_since(match_id, cursor)
    response = _commentary_response(
        request.app,
        hub,
        match_id=match_id,
        user_id=spectator_session.user_id,
        status=state.snapshot.status,
        events=events,
        cursor=next_cursor,
        include_audio=include_audio,
    )
    if response is not None:
        return response
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Commentary service is unavailable.")


@legacy_router.websocket("/{match_id}/stream")
@api_router.websocket("/{match_id}/stream")
async def stream_match(match_id: str, websocket: WebSocket, session_id: str) -> None:
    app = websocket.scope["app"]
    hub = ensure_live_match_hub(app)
    try:
        hub.validate_session(match_id, session_id)
    except LiveMatchError:
        await websocket.close(code=4404)
        return

    state = hub.get_state(match_id)
    if state is None and _bootstrap_infinite_league_stream(app, hub, match_id):
        state = hub.get_state(match_id)
    if state is None:
        await websocket.close(code=4404)
        return

    await _stream_realtime_topics(
        websocket,
        user_id=None,
        topics=(match_topic(match_id),),
    )


@legacy_router.websocket("/{match_id}/commentary/stream")
@api_router.websocket("/{match_id}/commentary/stream")
async def stream_match_commentary(match_id: str, websocket: WebSocket, session_id: str) -> None:
    app = websocket.scope["app"]
    hub = ensure_live_match_hub(app)
    try:
        spectator_session = hub.validate_session(match_id, session_id)
    except LiveMatchError:
        await websocket.close(code=4404)
        return

    state = hub.get_state(match_id)
    if state is None and _bootstrap_infinite_league_stream(app, hub, match_id):
        state = hub.get_state(match_id)
    if state is None:
        await websocket.close(code=4404)
        return

    await _stream_realtime_topics(
        websocket,
        user_id=spectator_session.user_id,
        topics=(commentary_topic(match_id),),
    )


@legacy_router.websocket("/{match_id}/audio/stems/stream")
@api_router.websocket("/{match_id}/audio/stems/stream")
async def stream_match_audio_stems(match_id: str, websocket: WebSocket, session_id: str) -> None:
    app = websocket.scope["app"]
    hub = ensure_live_match_hub(app)
    try:
        hub.validate_session(match_id, session_id)
    except LiveMatchError:
        await websocket.close(code=4404)
        return

    state = hub.get_state(match_id)
    if state is None and _bootstrap_infinite_league_stream(app, hub, match_id):
        state = hub.get_state(match_id)
    if state is None:
        await websocket.close(code=4404)
        return

    orchestrator = CommentaryOrchestratorService()
    await websocket.accept()
    cursor = 0
    await websocket.send_json(
        {
            "channel": state.channel,
            "kind": "audio_manifest_update",
            "payload": orchestrator.build_manifest(match_id=match_id).model_dump(mode="json"),
        }
    )
    try:
        while True:
            state = hub.get_state(match_id)
            if state is None:
                break
            events, cursor = hub.get_events_since(match_id, cursor)
            if events:
                await websocket.send_json(
                    {
                        "channel": state.channel,
                        "kind": "audio_stems",
                        "payload": [item.model_dump(mode="json") for item in orchestrator.build_frames(events)],
                    }
                )
            if not state.is_live and cursor >= state.event_count:
                break
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    await websocket.close()


router.include_router(legacy_router)
router.include_router(api_router)
router.include_router(match_router)
router.include_router(api_match_router)


async def _stream_realtime_topics(
    websocket: WebSocket,
    *,
    user_id: str | None,
    topics: tuple[str, ...],
) -> None:
    realtime = websocket.scope["app"].state.realtime
    client_id = await realtime.connect(websocket, user_id=user_id, topics=topics)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            text = (message.get("text") or "").strip().lower()
            if text == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
    except WebSocketDisconnect:
        return
    finally:
        await realtime.disconnect(client_id)


__all__ = ["router"]
