from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import os
from typing import Any

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, decode_access_token
from app.broadcast.broadcast_models import MatchSnapshot, SpectatorEvent, SpectatorPresenceView, TournamentEvent
import re
import time
from app.broadcast.match_room_manager import (
    MatchRoomManager,
    RoomClient,
    sanitize_public_spectator_payload,
)
from app.broadcast.presence_service import PresenceService
from app.broadcast.tournament_hub import TournamentBroadcastHub
from app.models.user import User

router = APIRouter(tags=["broadcast"])

_DELAY_ENV = "GTE_BROADCAST_DELAY_SECONDS"
_PRESENCE_TTL_ENV = "GTE_BROADCAST_PRESENCE_TTL_SECONDS"
_HEARTBEAT_ENV = "GTE_BROADCAST_HEARTBEAT_INTERVAL_SECONDS"
_QUEUE_ENV = "GTE_BROADCAST_MAX_PENDING_MESSAGES"


@dataclass(frozen=True, slots=True)
class ResolvedViewer:
    user_id: str | None
    display_name: str | None


@dataclass(slots=True)
class BroadcastRuntime:
    redis_url: str | None
    delay_seconds: int = 3
    viewer_ttl_seconds: int = 45
    heartbeat_interval_seconds: int = 15
    max_queue_size: int = 256
    rate_limit_max_messages: int = 5
    rate_limit_window_seconds: float = 5.0
    presence_service: PresenceService = field(init=False)
    match_room_manager: MatchRoomManager = field(init=False)
    tournament_hub: TournamentBroadcastHub = field(init=False)

    def __post_init__(self) -> None:
        self.presence_service = PresenceService(
            redis_url=self.redis_url,
            viewer_ttl_seconds=self.viewer_ttl_seconds,
        )
        self.match_room_manager = MatchRoomManager(
            redis_url=self.redis_url,
            delay_seconds=self.delay_seconds,
            max_queue_size=self.max_queue_size,
        )
        self.tournament_hub = TournamentBroadcastHub(
            redis_url=self.redis_url,
            delay_seconds=self.delay_seconds,
            max_queue_size=self.max_queue_size,
        )

    async def match_snapshot(self, match_id: str, *, metadata: dict[str, Any] | None = None) -> MatchSnapshot:
        presence = await self.presence_service.get_match_presence(match_id)
        safe_metadata = sanitize_public_spectator_payload(dict(metadata or {}))
        return MatchSnapshot(
            match_id=match_id,
            viewer_count=presence.active_viewers,
            peak_viewers=presence.peak_viewers,
            active_user_ids=[],
            metadata=safe_metadata,
        )

    async def aclose(self) -> None:
        await asyncio.gather(
            self.presence_service.aclose(),
            self.match_room_manager.aclose(),
            self.tournament_hub.aclose(),
            return_exceptions=True,
        )


def install_broadcast_runtime(app, _context) -> None:
    ensure_broadcast_runtime(app)


def shutdown_broadcast_runtime(app, _context) -> None:
    runtime = getattr(app.state, "broadcast_runtime", None)
    if runtime is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(runtime.aclose())


def ensure_broadcast_runtime(app) -> BroadcastRuntime:
    runtime = getattr(app.state, "broadcast_runtime", None)
    if runtime is not None:
        return runtime

    settings = getattr(app.state, "settings", None)
    runtime = BroadcastRuntime(
        redis_url=getattr(settings, "redis_url", None),
        delay_seconds=_setting_or_env(settings, "broadcast_delay_seconds", _DELAY_ENV, 3),
        viewer_ttl_seconds=_setting_or_env(settings, "broadcast_presence_ttl_seconds", _PRESENCE_TTL_ENV, 45),
        heartbeat_interval_seconds=_setting_or_env(
            settings,
            "broadcast_presence_heartbeat_interval_seconds",
            _HEARTBEAT_ENV,
            15,
        ),
        max_queue_size=_setting_or_env(settings, "broadcast_max_pending_messages", _QUEUE_ENV, 256),
    )
    app.state.broadcast_runtime = runtime
    app.state.broadcast = runtime
    return runtime


@router.get("/matches/{match_id}/spectators", response_model=SpectatorPresenceView)
async def get_match_spectators(
    match_id: str,
    request: Request,
    _: User = Depends(get_current_user),
) -> SpectatorPresenceView:
    # SpectatorPresenceView carries active_user_ids, i.e. the identity of every
    # account currently watching. That is not public data.
    runtime = ensure_broadcast_runtime(request.app)
    return await runtime.presence_service.get_match_presence(match_id)


@router.websocket("/ws/spectate/{match_id}")
async def spectate_match(websocket: WebSocket, match_id: str) -> None:
    runtime = ensure_broadcast_runtime(websocket.scope["app"])
    resolved_viewer = _resolve_optional_viewer(websocket)
    await websocket.accept()

    client = runtime.match_room_manager.build_client(
        websocket=websocket,
        user_id=resolved_viewer.user_id,
        display_name=resolved_viewer.display_name,
    )
    await runtime.match_room_manager.join_room(match_id, client)
    presence = await runtime.presence_service.register_viewer(match_id, client.connection_id, client.user_id)
    snapshot = await runtime.match_snapshot(match_id)
    await websocket.send_json(
        SpectatorEvent(
            type="snapshot",
            match_id=match_id,
            user_id=client.user_id,
            display_name=client.display_name,
            snapshot=snapshot,
            payload={"channel": runtime.match_room_manager.channel_for_match(match_id)},
        ).model_dump(mode="json")
    )
    await runtime.match_room_manager.publish(
        match_id,
        SpectatorEvent(type="viewer_count", match_id=match_id, snapshot=_snapshot_from_presence(match_id, presence)),
        delay_seconds=0,
    )

    sender_task = asyncio.create_task(_drain_client_queue(client), name=f"spectator-sender-{client.connection_id}")
    heartbeat_task = asyncio.create_task(
        _heartbeat_presence(runtime, match_id, client),
        name=f"spectator-heartbeat-{client.connection_id}",
    )
    try:
        while True:
            message = await websocket.receive_json()
            await _handle_spectator_client_message(runtime, match_id, client, message)
    except WebSocketDisconnect:
        return
    finally:
        heartbeat_task.cancel()
        sender_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        with suppress(asyncio.CancelledError):
            await sender_task
        presence = await runtime.presence_service.unregister_viewer(match_id, client.connection_id)
        await runtime.match_room_manager.leave_room(match_id, client)
        await runtime.match_room_manager.publish(
            match_id,
            SpectatorEvent(
                type="viewer_count", match_id=match_id, snapshot=_snapshot_from_presence(match_id, presence)
            ),
            delay_seconds=0,
        )
        with suppress(Exception):
            await websocket.close()


@router.websocket("/ws/tournament/{tournament_id}")
async def stream_tournament(websocket: WebSocket, tournament_id: str) -> None:
    runtime = ensure_broadcast_runtime(websocket.scope["app"])
    resolved_viewer = _resolve_optional_viewer(websocket)
    await websocket.accept()

    client = runtime.match_room_manager.build_client(
        websocket=websocket,
        user_id=resolved_viewer.user_id,
        display_name=resolved_viewer.display_name,
    )
    await runtime.tournament_hub.join_room(tournament_id, client)
    await websocket.send_json(
        TournamentEvent(
            type="tournament_snapshot",
            tournament_id=tournament_id,
            featured_match_id=await runtime.tournament_hub.featured_match_id(tournament_id),
            payload={"viewer_count": await runtime.tournament_hub.room_viewer_count(tournament_id)},
        ).model_dump(mode="json")
    )

    sender_task = asyncio.create_task(_drain_client_queue(client), name=f"tournament-sender-{client.connection_id}")
    try:
        while True:
            message = await websocket.receive_json()
            if str(message.get("type") or "").strip().lower() == "ping":
                await runtime.tournament_hub.broadcast(
                    tournament_id,
                    TournamentEvent(
                        type="heartbeat", tournament_id=tournament_id, payload={"connection_id": client.connection_id}
                    ),
                    delay_seconds=0,
                )
    except WebSocketDisconnect:
        return
    finally:
        sender_task.cancel()
        with suppress(asyncio.CancelledError):
            await sender_task
        await runtime.tournament_hub.leave_room(tournament_id, client)
        with suppress(Exception):
            await websocket.close()


async def _drain_client_queue(client: RoomClient) -> None:
    while True:
        payload = await client.queue.get()
        await client.websocket.send_json(payload)


async def _heartbeat_presence(runtime: BroadcastRuntime, match_id: str, client: RoomClient) -> None:
    interval = max(runtime.heartbeat_interval_seconds, 1)
    while True:
        await asyncio.sleep(interval)
        await runtime.presence_service.heartbeat_viewer(match_id, client.connection_id, client.user_id)


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_DISALLOWED_MARKUP_RE = re.compile(r"(<\s*/?\s*script|javascript:|<[^>]+>)", re.IGNORECASE)
_IMPERSONATION_TOKENS: frozenset[str] = frozenset(
    {
        "admin",
        "administrator",
        "system",
        "official",
        "moderator",
        "club owner",
        "owner",
        "gtex official",
        "gtex admin",
    }
)


def _sanitize_text_content(raw: str, *, max_length: int) -> str:
    cleaned = _CONTROL_CHARS_RE.sub("", raw).strip()
    cleaned = _DISALLOWED_MARKUP_RE.sub("", cleaned).strip()
    return cleaned[:max_length]


def _check_client_rate_limit(runtime: BroadcastRuntime, client: RoomClient) -> bool:
    now = time.monotonic()
    window = max(float(runtime.rate_limit_window_seconds), 0.1)
    max_msgs = max(int(runtime.rate_limit_max_messages), 1)
    cutoff = now - window
    client.message_timestamps = [ts for ts in client.message_timestamps if ts > cutoff]
    if len(client.message_timestamps) >= max_msgs:
        return False
    client.message_timestamps.append(now)
    return True


async def _handle_spectator_client_message(
    runtime: BroadcastRuntime,
    match_id: str,
    client: RoomClient,
    message: Any,
) -> None:
    if not isinstance(message, dict):
        return
    message_type = str(message.get("type") or "").strip().lower()
    if message_type == "ping":
        await runtime.match_room_manager.broadcast(
            match_id,
            SpectatorEvent(type="heartbeat", match_id=match_id, payload={"connection_id": client.connection_id}),
            delay_seconds=0,
        )
        return

    if message_type not in {"reaction", "chat_message"}:
        return

    if not _check_client_rate_limit(runtime, client):
        with suppress(asyncio.QueueFull):
            client.queue.put_nowait(
                SpectatorEvent(
                    type="rate_limit",
                    match_id=match_id,
                    user_id=client.user_id,
                    display_name=client.display_name,
                    payload={
                        "code": "rate_limit_exceeded",
                        "detail": "Message rate limit exceeded.",
                        "connection_id": client.connection_id,
                    },
                ).model_dump(mode="json")
            )
        return

    if message_type == "reaction":
        raw_reaction = str(message.get("reaction") or "")
        if _DISALLOWED_MARKUP_RE.search(raw_reaction):
            return
        reaction = _sanitize_text_content(raw_reaction, max_length=8)
        if not reaction:
            return
        payload: dict[str, Any] = {
            "connection_id": client.connection_id,
            "authenticated": bool(client.user_id),
        }
        app = client.websocket.scope.get("app")
        ticketing_runtime = getattr(getattr(app, "state", None), "ticketing_runtime", None) if app is not None else None
        if ticketing_runtime is not None and client.user_id:
            ticket_reaction = ticketing_runtime.record_reaction(
                match_id=match_id,
                user_id=client.user_id,
                reaction_type=reaction,
                source="websocket",
            )
            if ticket_reaction is not None:
                payload.update(
                    {
                        "seat_tier": ticket_reaction["attendee_access"]["seat_tier"],
                        "crowd_delta": ticket_reaction["crowd_delta"],
                        "influence_multiplier": ticket_reaction["influence_multiplier"],
                        "stadium_badge": ticket_reaction["attendee_access"]["badge"],
                    }
                )
        await runtime.match_room_manager.publish(
            match_id,
            SpectatorEvent(
                type="reaction",
                match_id=match_id,
                user_id=client.user_id,
                display_name=client.display_name,
                reaction=reaction,
                payload=payload,
            ),
            delay_seconds=0,
        )
        return

    if message_type == "chat_message":
        raw_chat = str(message.get("message") or "")
        if _DISALLOWED_MARKUP_RE.search(raw_chat):
            return
        chat_message = _sanitize_text_content(raw_chat, max_length=280)
        if not chat_message:
            return
        await runtime.match_room_manager.publish(
            match_id,
            SpectatorEvent(
                type="chat_message",
                match_id=match_id,
                user_id=client.user_id,
                display_name=client.display_name,
                message=chat_message,
                payload={
                    "connection_id": client.connection_id,
                    "authenticated": bool(client.user_id),
                },
            ),
            delay_seconds=0,
        )
        return


def _resolve_optional_viewer(websocket: WebSocket) -> ResolvedViewer:
    token = websocket.query_params.get("token")
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", maxsplit=1)[1].strip()
    guest_display_name = _fallback_display_name(websocket, is_authenticated=False)
    if token is None or not token.strip():
        return ResolvedViewer(user_id=None, display_name=guest_display_name)
    try:
        payload = decode_access_token(token.strip())
    except TokenError:
        return ResolvedViewer(user_id=None, display_name=guest_display_name)
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return ResolvedViewer(user_id=None, display_name=guest_display_name)
    session_factory = getattr(websocket.scope["app"].state, "session_factory", None)
    if session_factory is None:
        token_name = str(payload.get("display_name") or payload.get("username") or "").strip()
        resolved_name = token_name or _fallback_display_name(websocket, is_authenticated=True)
        return ResolvedViewer(user_id=subject, display_name=resolved_name)
    with session_factory() as session:
        user = session.get(User, subject)
        if user is None or not user.is_active:
            return ResolvedViewer(user_id=None, display_name=guest_display_name)
        resolved_name = (user.display_name or user.username or "").strip() or None
        return ResolvedViewer(user_id=user.id, display_name=resolved_name)


def _fallback_display_name(websocket: WebSocket, *, is_authenticated: bool = False) -> str | None:
    raw = str(websocket.query_params.get("display_name") or websocket.query_params.get("name") or "").strip()
    cleaned = _sanitize_text_content(raw, max_length=40)
    if not cleaned:
        return None
    if not is_authenticated:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", cleaned.lower()).strip()
        if normalized in _IMPERSONATION_TOKENS or any(
            normalized.startswith(f"{tok} ") or normalized.endswith(f" {tok}")
            for tok in _IMPERSONATION_TOKENS
        ):
            return "Spectator"
    return cleaned


def _snapshot_from_presence(match_id: str, presence: SpectatorPresenceView) -> MatchSnapshot:
    return MatchSnapshot(
        match_id=match_id,
        viewer_count=presence.active_viewers,
        peak_viewers=presence.peak_viewers,
        active_user_ids=presence.active_user_ids,
    )


def _setting_or_env(settings: Any, attr_name: str, env_name: str, default: int) -> int:
    value = getattr(settings, attr_name, None)
    if value is not None:
        return int(value)
    raw = os.getenv(env_name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
