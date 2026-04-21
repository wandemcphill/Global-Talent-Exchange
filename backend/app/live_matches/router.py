from __future__ import annotations

import asyncio
from hashlib import md5
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder

from app.auth.security import TokenError
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
    UnityLiveAccessView,
    UnityLiveAccessRefreshRequest,
)
from app.live_matches.service import LiveMatchError, ensure_live_match_hub
from app.live_matches.unity_access import (
    issue_unity_live_token_bundle,
    validate_unity_live_access_token,
    validate_unity_live_refresh_token,
)
from app.infinite_league.service import ensure_infinite_league_runtime
from app.match_engine.schemas import MatchReplayPayloadView
from app.models.competition_match import CompetitionMatch
from app.models.manager_duel import ManagerDuel
from app.models.user import User
from app.realtime.service import commentary_topic, match_topic
from app.replay_archive.service import ensure_replay_archive
from app.schemas.match_viewer import MatchTimelineFrameView, MatchViewStateView
from app.services.device_fingerprint_service import DeviceFingerprintService
from app.services.match_timeline_service import MatchTimelineService
from app.ticketing.service import TicketingError, TicketingService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live-matches"])
legacy_router = APIRouter(prefix="/matches", tags=["live-matches"])
api_router = APIRouter(prefix="/api/matches", tags=["live-matches"])
match_router = APIRouter(prefix="/match", tags=["live-matches"])
api_match_router = APIRouter(prefix="/api/match", tags=["live-matches"])

_UNITY_ALLOWED_ACCESS_SOURCES = frozenset(
    {"infinite_league", "open", "non_exclusive", "rights_owner", "grant", "paid_view"}
)
_UNITY_ACCESS_POLICY_MESSAGE = "Unity live access requires session-backed rights validation for non-generated matches."
_INFINITE_LEAGUE_TARGET_RUNTIME_SECONDS = max(
    60.0,
    float(os.environ.get("GTE_INFINITE_LEAGUE_TARGET_RUNTIME_SECONDS", "900")),
)

_UNITY_PITCH_LENGTH_METERS = 105.0
_UNITY_PITCH_WIDTH_METERS = 68.0
_UNITY_PLAYER_HEIGHT_METERS = 0.9


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


def _bootstrap_infinite_league_stream(app, hub, match_id: str, *, restart_if_completed: bool = False) -> bool:
    existing_state = hub.get_state(match_id)
    if existing_state is not None and existing_state.is_live:
        return True
    if existing_state is not None and not restart_if_completed:
        return False

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
        target_runtime_seconds=_INFINITE_LEAGUE_TARGET_RUNTIME_SECONDS,
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


def _merge_session_access(
    base: dict[str, object] | None, overlay: dict[str, object] | None
) -> dict[str, object] | None:
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
    for key in (
        "access_source",
        "rights_owner_id",
        "viewing_fee_coin",
        "sync_strategy",
        "watch_party_enabled",
        "reactions_enabled",
    ):
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
                "cue": (
                    event.experience.commentary.model_dump(mode="json")
                    if event.experience is not None and event.experience.commentary is not None
                    else None
                ),
            }
        )
    return payload


def _enforce_unity_live_access_policy(
    *,
    match_id: str,
    access_payload: dict[str, object] | None,
    is_generated_match: bool,
) -> dict[str, object]:
    payload = dict(access_payload or {})
    encoded_payload = jsonable_encoder(payload)
    if is_generated_match and not payload:
        payload = _generated_match_access_payload()
        encoded_payload = jsonable_encoder(payload)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_UNITY_ACCESS_POLICY_MESSAGE,
        )

    if not bool(payload.get("has_access", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Broadcast rights access is restricted for this match.",
                "access": encoded_payload,
            },
        )

    access_source = str(payload.get("access_source") or "").strip()
    if access_source not in _UNITY_ALLOWED_ACCESS_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": _UNITY_ACCESS_POLICY_MESSAGE,
                "match_id": match_id,
                "access": encoded_payload,
            },
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


def _enum_value(value: object | None) -> str | None:
    if value is None:
        return None
    resolved = getattr(value, "value", None)
    if isinstance(resolved, str):
        return resolved
    text = str(value).strip()
    return text or None


def _float_or_default(value: object | None, *, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _world_x(normalized_x: object | None) -> float:
    return round(
        ((_float_or_default(normalized_x) / 100.0) * _UNITY_PITCH_LENGTH_METERS) - (_UNITY_PITCH_LENGTH_METERS / 2.0), 3
    )


def _world_z(normalized_y: object | None) -> float:
    return round(
        ((_float_or_default(normalized_y) / 100.0) * _UNITY_PITCH_WIDTH_METERS) - (_UNITY_PITCH_WIDTH_METERS / 2.0), 3
    )


def _world_velocity_x(normalized_delta_x: object | None) -> float:
    return round((_float_or_default(normalized_delta_x) / 100.0) * _UNITY_PITCH_LENGTH_METERS, 3)


def _world_velocity_z(normalized_delta_y: object | None) -> float:
    return round((_float_or_default(normalized_delta_y) / 100.0) * _UNITY_PITCH_WIDTH_METERS, 3)


def _ball_trajectory_type(active_event) -> str:
    event_type = (_enum_value(active_event.event_type) or "").lower() if active_event is not None else ""
    if event_type in {"goal", "save", "miss", "penalty"}:
        return "shot"
    if event_type in {"kickoff", "set_piece", "attack"}:
        return "pass"
    if event_type in {"foul", "offside", "halftime", "fulltime"}:
        return "stopped"
    return "controlled"


def _unity_player_payload(player) -> dict[str, object]:
    return {
        "entityId": f"player:{player.player_id}",
        "playerId": player.player_id,
        "teamId": player.team_id,
        "teamSide": _enum_value(player.side),
        "label": player.label,
        "role": _enum_value(player.role),
        "line": player.line,
        "shirtNumber": player.shirt_number,
        "active": bool(player.active),
        "highlighted": bool(player.highlighted),
        "hasPossession": bool(player.has_possession),
        "animationState": _enum_value(player.animation_state),
        "speedRatio": round(_float_or_default(player.speed_ratio), 3),
        "state": _enum_value(player.state),
        "x": _world_x(player.position.x),
        "y": _UNITY_PLAYER_HEIGHT_METERS,
        "z": _world_z(player.position.y),
        "velocityX": _world_velocity_x(player.velocity.x),
        "velocityY": 0.0,
        "velocityZ": _world_velocity_z(player.velocity.y),
        "facingX": round(_float_or_default(player.facing.x), 3),
        "facingZ": round(_float_or_default(player.facing.y, default=1.0), 3),
        "spin": 0.0,
        "trajectoryType": "",
        "isBall": False,
    }


def _unity_ball_payload(frame, active_event, players_by_id: dict[str, object]) -> dict[str, object]:
    owner_player_id = frame.ball.owner_player_id
    owner = players_by_id.get(owner_player_id) if owner_player_id is not None else None
    velocity = frame.ball.velocity
    spin = frame.ball.spin
    velocity_x = _float_or_default(velocity.x if velocity is not None else None)
    velocity_z = _float_or_default(velocity.z if velocity is not None else None, default=1.0)
    return {
        "entityId": "ball",
        "playerId": owner_player_id,
        "teamId": getattr(owner, "team_id", None),
        "teamSide": _enum_value(getattr(owner, "side", None)),
        "label": "Ball",
        "role": "ball",
        "line": None,
        "shirtNumber": None,
        "active": True,
        "highlighted": False,
        "hasPossession": bool(owner_player_id),
        "animationState": "ball",
        "speedRatio": 1.0 if velocity is not None else 0.0,
        "state": str(frame.ball.state or "rolling"),
        "x": _world_x(frame.ball.position.x),
        "y": round(_float_or_default(frame.ball.height), 3),
        "z": _world_z(frame.ball.position.y),
        "velocityX": round(velocity_x, 3),
        "velocityY": round(_float_or_default(velocity.y if velocity is not None else None), 3),
        "velocityZ": round(velocity_z, 3),
        "facingX": round(velocity_x, 3),
        "facingZ": round(velocity_z, 3),
        "spin": round(_float_or_default(getattr(spin, "z", None)), 3),
        "trajectoryType": _ball_trajectory_type(active_event),
        "isBall": True,
    }


def _unity_event_payload(event) -> dict[str, object]:
    return {
        "id": event.event_id,
        "type": _enum_value(event.event_type),
        "sequence": int(event.sequence),
        "minute": int(event.minute),
        "addedTime": int(event.added_time),
        "clockLabel": event.clock_label,
        "timeSeconds": round(_float_or_default(event.time_seconds), 3),
        "teamId": event.team_id,
        "teamName": event.team_name,
        "primaryPlayerId": event.primary_player_id,
        "primaryPlayerName": event.primary_player_name,
        "secondaryPlayerId": event.secondary_player_id,
        "secondaryPlayerName": event.secondary_player_name,
        "homeScore": int(event.home_score),
        "awayScore": int(event.away_score),
        "bannerText": event.banner_text,
        "commentary": event.commentary,
        "emphasisLevel": int(event.emphasis_level),
        "highlightedPlayerIds": list(event.highlighted_player_ids),
        "flags": list(event.flags),
        "playbackProfile": event.playback_profile,
        "missVariant": event.miss_variant,
        "reviewable": bool(event.reviewable),
        "reviewReason": event.review_reason,
        "reviewDecision": event.review_decision,
        "scoreCommit": event.score_commit,
    }


def _lerp(start: float, end: float, factor: float) -> float:
    return start + ((end - start) * factor)


def _player_state_threshold(player_id: str | None) -> float:
    token = str(player_id or "").strip()
    if not token:
        return 0.5

    digest = md5(token.encode("utf-8")).digest()
    return 0.35 + ((int.from_bytes(digest[:2], "big") / 65535.0) * 0.3)


def _interpolate_frame(
    start_frame: MatchTimelineFrameView,
    end_frame: MatchTimelineFrameView,
    *,
    sample_time_seconds: float,
    factor: float,
) -> MatchTimelineFrameView:
    sampled_suffix = int(round(sample_time_seconds * 100))
    if factor <= 0.0 or start_frame.frame_id == end_frame.frame_id:
        return start_frame.model_copy(
            update={
                "frame_id": f"{start_frame.frame_id}:sample:{sampled_suffix}",
                "time_seconds": round(sample_time_seconds, 2),
            }
        )
    if factor >= 1.0:
        return end_frame.model_copy(
            update={
                "frame_id": f"{end_frame.frame_id}:sample:{sampled_suffix}",
                "time_seconds": round(sample_time_seconds, 2),
            }
        )

    end_players_by_id = {player.player_id: player for player in end_frame.players}
    players = []
    span_seconds = max(end_frame.time_seconds - start_frame.time_seconds, 0.05)
    for start_player in start_frame.players:
        end_player = end_players_by_id.get(start_player.player_id, start_player)
        state_threshold = _player_state_threshold(start_player.player_id)
        sampled_position = start_player.position.model_copy(
            update={
                "x": round(_lerp(start_player.position.x, end_player.position.x, factor), 3),
                "y": round(_lerp(start_player.position.y, end_player.position.y, factor), 3),
            }
        )
        sampled_velocity = start_player.velocity.model_copy(
            update={
                "x": round((float(end_player.position.x) - float(start_player.position.x)) / span_seconds, 3),
                "y": round((float(end_player.position.y) - float(start_player.position.y)) / span_seconds, 3),
            }
        )
        sampled_velocity_x = float(sampled_velocity.x)
        sampled_velocity_y = float(sampled_velocity.y)
        sampled_velocity_magnitude = ((sampled_velocity_x**2) + (sampled_velocity_y**2)) ** 0.5
        sampled_facing = (
            start_player.facing.model_copy(
                update={
                    "x": round(sampled_velocity_x / sampled_velocity_magnitude, 3),
                    "y": round(sampled_velocity_y / sampled_velocity_magnitude, 3),
                }
            )
            if sampled_velocity_magnitude > 0.0001
            else start_player.facing.model_copy(
                update={
                    "x": round(_lerp(start_player.facing.x, end_player.facing.x, factor), 3),
                    "y": round(_lerp(start_player.facing.y, end_player.facing.y, factor), 3),
                }
            )
        )
        players.append(
            start_player.model_copy(
                update={
                    "highlighted": end_player.highlighted if factor >= state_threshold else start_player.highlighted,
                    "has_possession": end_player.has_possession if factor >= 0.5 else start_player.has_possession,
                    "state": end_player.state if factor >= state_threshold else start_player.state,
                    "animation_state": (
                        end_player.animation_state if factor >= state_threshold else start_player.animation_state
                    ),
                    "position": sampled_position,
                    "anchor_position": start_player.anchor_position.model_copy(
                        update={
                            "x": round(_lerp(start_player.anchor_position.x, end_player.anchor_position.x, factor), 3),
                            "y": round(_lerp(start_player.anchor_position.y, end_player.anchor_position.y, factor), 3),
                        }
                    ),
                    "speed_ratio": round(_lerp(start_player.speed_ratio, end_player.speed_ratio, factor), 3),
                    "blend_factor": round(_lerp(start_player.blend_factor, end_player.blend_factor, factor), 3),
                    "stamina_pct": round(_lerp(start_player.stamina_pct, end_player.stamina_pct, factor), 3),
                    "facing": sampled_facing,
                    "velocity": sampled_velocity,
                }
            )
        )

    start_ball = start_frame.ball
    end_ball = end_frame.ball
    sampled_ball = start_ball.model_copy(
        update={
            "position": start_ball.position.model_copy(
                update={
                    "x": round(_lerp(start_ball.position.x, end_ball.position.x, factor), 3),
                    "y": round(_lerp(start_ball.position.y, end_ball.position.y, factor), 3),
                }
            ),
            "height": round(_lerp(start_ball.height, end_ball.height, factor), 3),
            "owner_player_id": end_ball.owner_player_id if factor >= 0.5 else start_ball.owner_player_id,
            "state": end_ball.state if factor >= 0.5 else start_ball.state,
            "spin": (
                None
                if start_ball.spin is None or end_ball.spin is None
                else start_ball.spin.model_copy(
                    update={
                        "x": round(_lerp(start_ball.spin.x, end_ball.spin.x, factor), 3),
                        "y": round(_lerp(start_ball.spin.y, end_ball.spin.y, factor), 3),
                        "z": round(_lerp(start_ball.spin.z, end_ball.spin.z, factor), 3),
                    }
                )
            ),
            "velocity": (
                None
                if start_ball.velocity is None or end_ball.velocity is None
                else start_ball.velocity.model_copy(
                    update={
                        "x": round((float(end_ball.position.x) - float(start_ball.position.x)) / span_seconds, 3),
                        "y": round((float(end_ball.height) - float(start_ball.height)) / span_seconds, 3),
                        "z": round((float(end_ball.position.y) - float(start_ball.position.y)) / span_seconds, 3),
                    }
                )
            ),
        }
    )

    return start_frame.model_copy(
        update={
            "frame_id": f"{start_frame.frame_id}:sample:{sampled_suffix}",
            "time_seconds": round(sample_time_seconds, 2),
            "clock_minute": round(_lerp(start_frame.clock_minute, end_frame.clock_minute, factor), 2),
            "phase": end_frame.phase if factor >= 0.5 else start_frame.phase,
            "home_score": end_frame.home_score if factor >= 0.95 else start_frame.home_score,
            "away_score": end_frame.away_score if factor >= 0.95 else start_frame.away_score,
            "home_attacks_right": end_frame.home_attacks_right if factor >= 0.5 else start_frame.home_attacks_right,
            "possession_side": end_frame.possession_side if factor >= 0.5 else start_frame.possession_side,
            "active_event_id": end_frame.active_event_id if factor >= 0.5 else start_frame.active_event_id,
            "event_banner": end_frame.event_banner if factor >= 0.5 else start_frame.event_banner,
            "stage": end_frame.stage if factor >= 0.5 else start_frame.stage,
            "camera_preset": end_frame.camera_preset if factor >= 0.5 else start_frame.camera_preset,
            "overlay_text": end_frame.overlay_text if factor >= 0.5 else start_frame.overlay_text,
            "pause_playback": end_frame.pause_playback if factor >= 0.5 else start_frame.pause_playback,
            "playback_rate": round(_lerp(start_frame.playback_rate, end_frame.playback_rate, factor), 3),
            "flag_animation": end_frame.flag_animation if factor >= 0.5 else start_frame.flag_animation,
            "celebration_team_id": end_frame.celebration_team_id if factor >= 0.5 else start_frame.celebration_team_id,
            "possession_phase": end_frame.possession_phase if factor >= 0.5 else start_frame.possession_phase,
            "transition_state": end_frame.transition_state if factor >= 0.5 else start_frame.transition_state,
            "danger_zone": end_frame.danger_zone if factor >= 0.5 else start_frame.danger_zone,
            "pressure_index": round(_lerp(start_frame.pressure_index, end_frame.pressure_index, factor), 3),
            "compactness_home": round(_lerp(start_frame.compactness_home, end_frame.compactness_home, factor), 3),
            "compactness_away": round(_lerp(start_frame.compactness_away, end_frame.compactness_away, factor), 3),
            "frame_tags": list(end_frame.frame_tags if factor >= 0.5 else start_frame.frame_tags),
            "players": players,
            "ball": sampled_ball,
        }
    )


def _sample_viewer_frame(view_state: MatchViewStateView, sample_time_seconds: float) -> MatchTimelineFrameView:
    if not view_state.frames:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live match frame could not be resolved.",
        )

    sampled_suffix = int(round(sample_time_seconds * 100))
    if sample_time_seconds <= view_state.frames[0].time_seconds:
        return view_state.frames[0].model_copy(
            update={
                "frame_id": f"{view_state.frames[0].frame_id}:sample:{sampled_suffix}",
                "time_seconds": round(max(0.0, sample_time_seconds), 2),
            }
        )
    if sample_time_seconds >= view_state.frames[-1].time_seconds:
        return view_state.frames[-1].model_copy(
            update={
                "frame_id": f"{view_state.frames[-1].frame_id}:sample:{sampled_suffix}",
                "time_seconds": round(sample_time_seconds, 2),
            }
        )

    for index in range(1, len(view_state.frames)):
        previous_frame = view_state.frames[index - 1]
        next_frame = view_state.frames[index]
        if sample_time_seconds > next_frame.time_seconds:
            continue
        span = max(next_frame.time_seconds - previous_frame.time_seconds, 0.0001)
        factor = max(0.0, min(1.0, (sample_time_seconds - previous_frame.time_seconds) / span))
        return _interpolate_frame(
            previous_frame,
            next_frame,
            sample_time_seconds=sample_time_seconds,
            factor=factor,
        )

    return view_state.frames[-1]


def _load_persisted_live_view_state(match_id: str, app) -> MatchViewStateView | None:
    timeline_service = MatchTimelineService()
    session_factory = getattr(app.state, "session_factory", None)
    if session_factory is not None:
        with session_factory() as session:
            match = session.get(CompetitionMatch, match_id)
            if match is not None:
                metadata = match.metadata_json if isinstance(match.metadata_json, dict) else {}
                viewer_payload = metadata.get("match_viewer")
                if isinstance(viewer_payload, dict):
                    try:
                        return MatchViewStateView.model_validate(viewer_payload)
                    except Exception:
                        logger.warning("Stored match_viewer payload for %s could not be validated.", match_id)
                replay_payload = metadata.get("replay_payload")
                if isinstance(replay_payload, dict):
                    try:
                        return timeline_service.build_from_replay_payload(
                            MatchReplayPayloadView.model_validate(replay_payload)
                        )
                    except Exception:
                        logger.warning("Stored replay_payload for %s could not be rebuilt into a live view.", match_id)

            duel = session.get(ManagerDuel, match_id)
            if duel is not None:
                replay_payload = (duel.metadata_json or {}).get("replay_payload")
                if isinstance(replay_payload, dict):
                    try:
                        return timeline_service.build_from_replay_payload(
                            MatchReplayPayloadView.model_validate(replay_payload)
                        )
                    except Exception:
                        logger.warning(
                            "Stored duel replay payload for %s could not be rebuilt into a live view.", match_id
                        )

    archive = ensure_replay_archive(app)
    record = archive.repository.get_latest_record(f"replay:{match_id}")
    if record is not None:
        try:
            return timeline_service.build_from_archive_record(record)
        except Exception:
            logger.warning("Replay archive record for %s could not be rebuilt into a live view.", match_id)
    return None


def build_unity_live_payload_for_app(app, match_id: str) -> dict[str, object]:
    hub = ensure_live_match_hub(app)
    source = "live_match_hub"
    state = hub.get_state(match_id)
    if (state is None or not state.is_live) and _bootstrap_infinite_league_stream(
        app,
        hub,
        match_id,
        restart_if_completed=True,
    ):
        state = hub.get_state(match_id)
        source = "infinite_league_runtime"
    view_state: MatchViewStateView | None = None
    live_status = "completed"
    playback_context = hub.get_playback_context(match_id)
    if playback_context is not None and playback_context.viewer_state is not None:
        view_state = playback_context.viewer_state
        source = view_state.source or source
        live_status = "live" if playback_context.is_live else "completed"
    elif state is not None:
        events, _ = hub.get_events_since(match_id, 0)
        live_status = state.snapshot.status
        try:
            view_state = MatchTimelineService().build_from_live_stream(
                match_id=match_id,
                source=source,
                home_team_id=None,
                home_team_name=None,
                away_team_id=None,
                away_team_name=None,
                events=events,
                live_state=state,
            )
        except Exception:
            logger.exception("Failed to build live-stream view state for match %s", match_id)
            view_state = None
    if view_state is None:
        view_state = _load_persisted_live_view_state(match_id, app)
        if view_state is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match stream was not found.")
        logger.warning("Live match cache miss for %s; returning persisted match frames instead.", match_id)
    if not view_state.frames:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Live match frame could not be resolved."
        )

    if state is not None:
        live_status = state.snapshot.status

    if playback_context is not None and playback_context.viewer_state is not None:
        playback_span_seconds = max(
            float(view_state.duration_seconds),
            float(view_state.frames[-1].time_seconds),
            1.0,
        )
        playback_ratio = min(
            1.0,
            max(0.0, playback_context.elapsed_runtime_seconds / max(playback_context.target_runtime_seconds, 1.0)),
        )
        frame = _sample_viewer_frame(
            view_state,
            round(playback_span_seconds * playback_ratio, 2),
        )
    else:
        frame = view_state.frames[-1]
    players_by_id = {player.player_id: player for player in frame.players}
    active_event = next((event for event in view_state.events if event.event_id == frame.active_event_id), None)
    view_state_payload = view_state.model_dump(mode="json")

    return {
        "matchId": match_id,
        "source": view_state.source,
        "status": live_status if state is not None else "completed",
        "isLive": bool(state.is_live) if state is not None else False,
        "frameId": frame.frame_id,
        "clockMinute": round(_float_or_default(frame.clock_minute), 2),
        "phase": _enum_value(frame.phase) or "open_play",
        "homeScore": int(frame.home_score),
        "awayScore": int(frame.away_score),
        "possessionSide": _enum_value(frame.possession_side) or "home",
        "activeEventId": frame.active_event_id,
        "cameraPreset": _enum_value(frame.camera_preset) or "broadcast",
        "pitchLengthMeters": _UNITY_PITCH_LENGTH_METERS,
        "pitchWidthMeters": _UNITY_PITCH_WIDTH_METERS,
        "score": {"home": int(frame.home_score), "away": int(frame.away_score)},
        "players": [_unity_player_payload(player) for player in frame.players],
        "ballPosition": _unity_ball_payload(frame, active_event, players_by_id),
        "events": [_unity_event_payload(event) for event in view_state.events],
        "frames": view_state_payload["frames"],
        "timelineEvents": view_state_payload["events"],
        "viewer": view_state_payload,
    }


def _build_unity_live_payload(match_id: str, request: Request) -> dict[str, object]:
    return build_unity_live_payload_for_app(request.app, match_id)


def _extract_bearer_token(authorization: str | None) -> str:
    candidate = str(authorization or "").strip()
    if not candidate:
        return ""
    if candidate.lower().startswith("bearer "):
        return candidate.split(" ", maxsplit=1)[1].strip()
    return ""


def _resolve_unity_live_access_token(
    *,
    authorization: str | None,
    query_token: str | None,
) -> str:
    bearer_token = _extract_bearer_token(authorization)
    if bearer_token:
        return bearer_token
    candidate = str(query_token or "").strip()
    return candidate


def _require_unity_live_access_for_request(request: Request, *, match_id: str):
    token = _resolve_unity_live_access_token(
        authorization=request.headers.get("authorization"),
        query_token=request.query_params.get("access_token"),
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unity live access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = validate_unity_live_access_token(token, match_id=match_id)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    hub = ensure_live_match_hub(request.app)
    try:
        spectator_session = hub.validate_session(match_id, claims["spectator_session_id"])
    except LiveMatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if spectator_session.user_id != claims["viewer_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unity live access token does not match the spectator session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return spectator_session


def _require_unity_live_access_for_websocket(websocket: WebSocket, *, match_id: str):
    token = _resolve_unity_live_access_token(
        authorization=websocket.headers.get("authorization"),
        query_token=websocket.query_params.get("access_token"),
    )
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unity live access token is required.")

    try:
        claims = validate_unity_live_access_token(token, match_id=match_id)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    hub = ensure_live_match_hub(websocket.scope["app"])
    try:
        spectator_session = hub.validate_session(match_id, claims["spectator_session_id"])
    except LiveMatchError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if spectator_session.user_id != claims["viewer_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unity live access token does not match the spectator session.",
        )

    return spectator_session


def _join_spectate_session(
    *,
    match_id: str,
    request: Request,
    current_user: User,
    pay_to_view: bool,
    require_resolved_access: bool = False,
):
    access_payload: dict[str, object] | None = None
    hub = ensure_live_match_hub(request.app)
    is_generated_match = _bootstrap_infinite_league_stream(request.app, hub, match_id)
    if is_generated_match:
        access_payload = _generated_match_access_payload()

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None and require_resolved_access and not is_generated_match:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_UNITY_ACCESS_POLICY_MESSAGE,
        )

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
                                "access": jsonable_encoder(access_payload),
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
            if require_resolved_access:
                access_payload = _enforce_unity_live_access_policy(
                    match_id=match_id,
                    access_payload=access_payload,
                    is_generated_match=is_generated_match,
                )
            session.commit()
            return spectator_session, access_payload

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
    if require_resolved_access:
        access_payload = _enforce_unity_live_access_policy(
            match_id=match_id,
            access_payload=access_payload,
            is_generated_match=is_generated_match,
        )
    return spectator_session, access_payload


def _revalidate_unity_refresh_access(
    *,
    match_id: str,
    request: Request,
    viewer_user_id: str,
) -> dict[str, object]:
    hub = ensure_live_match_hub(request.app)
    is_generated_match = _bootstrap_infinite_league_stream(request.app, hub, match_id)
    access_payload: dict[str, object] | None = _generated_match_access_payload() if is_generated_match else None

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return _enforce_unity_live_access_policy(
            match_id=match_id,
            access_payload=access_payload,
            is_generated_match=is_generated_match,
        )

    with session_factory() as session:
        actor = session.get(User, viewer_user_id)
        if actor is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unity live refresh user was not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not is_generated_match:
            try:
                access_payload = BroadcastRightsService(session).resolve_match_access(
                    actor=actor,
                    match_id=match_id,
                    pay_to_view=False,
                )
            except BroadcastRightsError as exc:
                session.rollback()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc

        return _enforce_unity_live_access_policy(
            match_id=match_id,
            access_payload=access_payload,
            is_generated_match=is_generated_match,
        )


def _issue_unity_live_access_view(
    *, match_id: str, spectator_session_id: str, viewer_user_id: str
) -> UnityLiveAccessView:
    token_bundle = issue_unity_live_token_bundle(
        match_id=match_id,
        spectator_session_id=spectator_session_id,
        viewer_user_id=viewer_user_id,
    )
    return UnityLiveAccessView(
        match_id=match_id,
        spectator_session_id=spectator_session_id,
        access_token=str(token_bundle["access_token"]),
        refresh_token=str(token_bundle["refresh_token"]),
        token_type="bearer",
        expires_in=int(token_bundle["access_expires_in"]),
        refresh_expires_in=int(token_bundle["refresh_expires_in"]),
        live_path=f"/match/{match_id}/live",
        websocket_path=f"/api/v1/ws/match/{match_id}?format=unity",
        refresh_path=f"/match/{match_id}/unity-access/refresh",
    )


@legacy_router.post("/{match_id}/spectate", response_model=SpectatorSessionView)
@api_router.post("/{match_id}/spectate", response_model=SpectatorSessionView)
def join_spectate(
    match_id: str,
    request: Request,
    pay_to_view: bool = Query(default=False),
    current_user: User = Depends(get_current_match_user),
) -> SpectatorSessionView:
    spectator_session, access_payload = _join_spectate_session(
        match_id=match_id,
        request=request,
        current_user=current_user,
        pay_to_view=pay_to_view,
    )
    return _build_session_view(match_id, spectator_session, access_payload)


@legacy_router.post("/{match_id}/unity-access", response_model=UnityLiveAccessView)
@api_router.post("/{match_id}/unity-access", response_model=UnityLiveAccessView)
@match_router.post("/{match_id}/unity-access", response_model=UnityLiveAccessView)
@api_match_router.post("/{match_id}/unity-access", response_model=UnityLiveAccessView)
def issue_unity_live_access(
    match_id: str,
    request: Request,
    pay_to_view: bool = Query(default=False),
    current_user: User = Depends(get_current_match_user),
) -> UnityLiveAccessView:
    spectator_session, _access_payload = _join_spectate_session(
        match_id=match_id,
        request=request,
        current_user=current_user,
        pay_to_view=pay_to_view,
        require_resolved_access=True,
    )
    return _issue_unity_live_access_view(
        match_id=match_id,
        spectator_session_id=spectator_session.id,
        viewer_user_id=current_user.id,
    )


@legacy_router.post("/{match_id}/unity-access/refresh", response_model=UnityLiveAccessView)
@api_router.post("/{match_id}/unity-access/refresh", response_model=UnityLiveAccessView)
@match_router.post("/{match_id}/unity-access/refresh", response_model=UnityLiveAccessView)
@api_match_router.post("/{match_id}/unity-access/refresh", response_model=UnityLiveAccessView)
def refresh_unity_live_access(
    match_id: str,
    payload: UnityLiveAccessRefreshRequest,
    request: Request,
) -> UnityLiveAccessView:
    try:
        claims = validate_unity_live_refresh_token(payload.refresh_token, match_id=match_id)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    hub = ensure_live_match_hub(request.app)
    try:
        spectator_session = hub.validate_session(match_id, claims["spectator_session_id"])
    except LiveMatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if spectator_session.user_id != claims["viewer_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unity live refresh token does not match the spectator session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _revalidate_unity_refresh_access(
        match_id=match_id,
        request=request,
        viewer_user_id=spectator_session.user_id,
    )

    return _issue_unity_live_access_view(
        match_id=match_id,
        spectator_session_id=spectator_session.id,
        viewer_user_id=spectator_session.user_id,
    )


@legacy_router.get("/{match_id}/live")
@api_router.get("/{match_id}/live")
@match_router.get("/{match_id}/live")
@api_match_router.get("/{match_id}/live")
def read_match_live_bridge(match_id: str, request: Request) -> dict[str, object]:
    _require_unity_live_access_for_request(request, match_id=match_id)
    try:
        return _build_unity_live_payload(match_id, request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to build live match bridge payload for %s", match_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live match payload is temporarily unavailable.",
        ) from exc


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
