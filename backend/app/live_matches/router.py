from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.auth.dependencies import get_current_user
from app.live_matches.highlights import SmartHighlightService
from app.live_matches.schemas import MatchHighlightResponseView, SpectatorSessionView
from app.live_matches.service import LiveMatchError, ensure_live_match_hub
from app.match_engine.schemas import MatchReplayPayloadView
from app.models.manager_duel import ManagerDuel
from app.models.user import User
from app.replay_archive.service import ensure_replay_archive

router = APIRouter(tags=["live-matches"])
legacy_router = APIRouter(prefix="/matches", tags=["live-matches"])
api_router = APIRouter(prefix="/api/matches", tags=["live-matches"])


def _build_session_view(match_id: str, item) -> SpectatorSessionView:
    return SpectatorSessionView(
        id=item.id,
        match_id=item.match_id,
        user_id=item.user_id,
        joined_at=item.joined_at,
        read_only=True,
        channel=f"match:{match_id}",
        websocket_path=f"/api/matches/{match_id}/stream?session_id={item.id}",
    )


@legacy_router.post("/{match_id}/spectate", response_model=SpectatorSessionView)
@api_router.post("/{match_id}/spectate", response_model=SpectatorSessionView)
def join_spectate(
    match_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SpectatorSessionView:
    hub = ensure_live_match_hub(request.app)
    try:
        session = hub.join_spectate(match_id, current_user.id)
    except LiveMatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _build_session_view(match_id, session)


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
    return MatchHighlightResponseView(highlights=[])


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
    if state is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    cursor = 0
    await websocket.send_json(
        {
            "channel": state.channel,
            "kind": "snapshot",
            "payload": state.snapshot.model_dump(mode="json"),
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
                        "kind": "events",
                        "payload": [event.model_dump(mode="json") for event in events],
                    }
                )
            await websocket.send_json(
                {
                    "channel": state.channel,
                    "kind": "snapshot",
                    "payload": state.snapshot.model_dump(mode="json"),
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

__all__ = ["router"]
