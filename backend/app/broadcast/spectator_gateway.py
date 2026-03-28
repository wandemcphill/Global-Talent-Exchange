from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import os
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from app.auth.security import TokenError, decode_access_token
from app.broadcast.broadcast_models import MatchSnapshot, SpectatorEvent, SpectatorPresenceView, TournamentEvent
from app.broadcast.match_room_manager import MatchRoomManager, RoomClient
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
        return MatchSnapshot(
            match_id=match_id,
            viewer_count=presence.active_viewers,
            peak_viewers=presence.peak_viewers,
            active_user_ids=presence.active_user_ids,
            metadata=dict(metadata or {}),
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
async def get_match_spectators(match_id: str, request: Request) -> SpectatorPresenceView:
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
            SpectatorEvent(type="viewer_count", match_id=match_id, snapshot=_snapshot_from_presence(match_id, presence)),
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
                    TournamentEvent(type="heartbeat", tournament_id=tournament_id, payload={"connection_id": client.connection_id}),
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


async def _handle_spectator_client_message(
    runtime: BroadcastRuntime,
    match_id: str,
    client: RoomClient,
    message: Any,
) -> None:
    if not isinstance(message, dict):
        return
    message_type = str(message.get("type") or "").strip().lower()
    if message_type == "reaction":
        reaction = str(message.get("reaction") or "").strip()
        if not reaction:
            return
        await runtime.match_room_manager.publish(
            match_id,
            SpectatorEvent(
                type="reaction",
                match_id=match_id,
                user_id=client.user_id,
                display_name=client.display_name,
                reaction=reaction[:8],
                payload={"connection_id": client.connection_id},
            ),
            delay_seconds=0,
        )
        return
    if message_type == "chat_message":
        chat_message = str(message.get("message") or "").strip()
        if not chat_message:
            return
        await runtime.match_room_manager.publish(
            match_id,
            SpectatorEvent(
                type="chat_message",
                match_id=match_id,
                user_id=client.user_id,
                display_name=client.display_name,
                message=chat_message[:500],
                payload={"connection_id": client.connection_id},
            ),
            delay_seconds=0,
        )
        return
    if message_type == "ping":
        await runtime.match_room_manager.broadcast(
            match_id,
            SpectatorEvent(type="heartbeat", match_id=match_id, payload={"connection_id": client.connection_id}),
            delay_seconds=0,
        )


def _resolve_optional_viewer(websocket: WebSocket) -> ResolvedViewer:
    token = websocket.query_params.get("token")
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", maxsplit=1)[1].strip()
    display_name = _fallback_display_name(websocket)
    if token is None or not token.strip():
        return ResolvedViewer(user_id=None, display_name=display_name)
    try:
        payload = decode_access_token(token.strip())
    except TokenError:
        return ResolvedViewer(user_id=None, display_name=display_name)
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return ResolvedViewer(user_id=None, display_name=display_name)
    session_factory = getattr(websocket.scope["app"].state, "session_factory", None)
    if session_factory is None:
        return ResolvedViewer(user_id=subject, display_name=display_name)
    with session_factory() as session:
        user = session.get(User, subject)
        if user is None or not user.is_active:
            return ResolvedViewer(user_id=None, display_name=display_name)
        resolved_name = (user.display_name or user.username or display_name or "").strip() or None
        return ResolvedViewer(user_id=user.id, display_name=resolved_name)


def _fallback_display_name(websocket: WebSocket) -> str | None:
    value = str(websocket.query_params.get("display_name") or websocket.query_params.get("name") or "").strip()
    if not value:
        return None
    return value[:80]


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
