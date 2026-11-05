from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import os
import re
import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, decode_access_token
from app.broadcast.broadcast_models import MatchSnapshot, SpectatorEvent, SpectatorPresenceView, TournamentEvent
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
class SpectatorTicketRecord:
    ticket_id: str
    user_id: str
    display_name: str | None
    scope_type: str
    scope_id: str
    expires_at: float
    used: bool = False


@dataclass(slots=True)
class BroadcastRuntime:
    redis_url: str | None
    delay_seconds: int = 3
    viewer_ttl_seconds: int = 45
    heartbeat_interval_seconds: int = 15
    max_queue_size: int = 256
    rate_limit_max_messages: int = 5
    rate_limit_window_seconds: float = 5.0
    ticket_ttl_seconds: float = 30.0
    presence_service: PresenceService = field(init=False)
    match_room_manager: MatchRoomManager = field(init=False)
    tournament_hub: TournamentBroadcastHub = field(init=False)
    _tickets: dict[str, SpectatorTicketRecord] = field(init=False, default_factory=dict)

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

    def issue_spectator_ticket(
        self,
        *,
        user_id: str,
        display_name: str | None,
        scope_type: str,
        scope_id: str,
        ttl_seconds: float | None = None,
    ) -> dict[str, Any]:
        now = time.monotonic()
        # Prune expired or used tickets
        expired_keys = [
            k for k, rec in self._tickets.items() if rec.used or now >= rec.expires_at
        ]
        for k in expired_keys:
            self._tickets.pop(k, None)

        ttl = float(self.ticket_ttl_seconds if ttl_seconds is None else ttl_seconds)
        ticket_id = secrets.token_urlsafe(32)
        self._tickets[ticket_id] = SpectatorTicketRecord(
            ticket_id=ticket_id,
            user_id=str(user_id),
            display_name=display_name,
            scope_type=str(scope_type).strip().lower(),
            scope_id=str(scope_id).strip(),
            expires_at=now + max(ttl, 0.001),
            used=False,
        )
        return {
            "ticket": ticket_id,
            "scope_type": str(scope_type).strip().lower(),
            "scope_id": str(scope_id).strip(),
            "expires_in": max(int(ttl), 1),
        }

    def redeem_spectator_ticket(
        self,
        ticket: str,
        *,
        expected_scope_type: str,
        expected_scope_id: str,
    ) -> ResolvedViewer | None:
        cleaned = str(ticket or "").strip()
        if not cleaned:
            return None
        record = self._tickets.get(cleaned)
        if record is None:
            return None
        now = time.monotonic()
        if record.used or now >= record.expires_at:
            self._tickets.pop(cleaned, None)
            return None
        if (
            record.scope_type != str(expected_scope_type).strip().lower()
            or record.scope_id != str(expected_scope_id).strip()
        ):
            return None
        record.used = True
        self._tickets.pop(cleaned, None)
        return ResolvedViewer(user_id=record.user_id, display_name=record.display_name)

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


@router.post("/matches/{match_id}/spectate-ticket")
async def create_match_spectate_ticket(
    match_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issues a short-lived, single-use, match-scoped WebSocket ticket so bearer tokens never appear in URLs."""
    user_id = str(getattr(current_user, "id", "") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    display_name = (
        str(getattr(current_user, "display_name", None) or getattr(current_user, "username", None) or "").strip()
        or None
    )
    runtime = ensure_broadcast_runtime(request.app)
    issued = runtime.issue_spectator_ticket(
        user_id=user_id,
        display_name=display_name,
        scope_type="match",
        scope_id=match_id,
    )
    return {
        "ticket": issued["ticket"],
        "match_id": match_id,
        "scope_type": "match",
        "expires_in": issued["expires_in"],
    }


@router.post("/tournaments/{tournament_id}/spectate-ticket")
async def create_tournament_spectate_ticket(
    tournament_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issues a short-lived, single-use, tournament-scoped WebSocket ticket."""
    user_id = str(getattr(current_user, "id", "") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    display_name = (
        str(getattr(current_user, "display_name", None) or getattr(current_user, "username", None) or "").strip()
        or None
    )
    runtime = ensure_broadcast_runtime(request.app)
    issued = runtime.issue_spectator_ticket(
        user_id=user_id,
        display_name=display_name,
        scope_type="tournament",
        scope_id=tournament_id,
    )
    return {
        "ticket": issued["ticket"],
        "tournament_id": tournament_id,
        "scope_type": "tournament",
        "expires_in": issued["expires_in"],
    }


@router.get("/matches/{match_id}/spectators", response_model=SpectatorPresenceView)
async def get_match_spectators(
    match_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SpectatorPresenceView:
    runtime = ensure_broadcast_runtime(request.app)
    presence = await runtime.presence_service.get_match_presence(match_id)
    if not (getattr(current_user, "is_admin", False) or getattr(current_user, "is_super_admin", False)):
        return presence.model_copy(update={"active_user_ids": []})
    return presence


@router.websocket("/ws/spectate/{match_id}")
async def spectate_match(websocket: WebSocket, match_id: str) -> None:
    runtime = ensure_broadcast_runtime(websocket.scope["app"])
    auth_ok, resolved_viewer, reject_reason = _authenticate_spectator_websocket(
        websocket,
        runtime=runtime,
        scope_type="match",
        scope_id=match_id,
    )
    if not auth_ok:
        await websocket.close(code=4401, reason=reject_reason or "Unauthorized spectator handshake.")
        return

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
        sanitize_public_spectator_payload(
            SpectatorEvent(
                type="snapshot",
                match_id=match_id,
                user_id=None,
                display_name=client.display_name,
                snapshot=snapshot,
                payload={
                    "channel": runtime.match_room_manager.channel_for_match(match_id),
                    "authenticated": bool(client.user_id),
                },
            ).model_dump(mode="json")
        )
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
    auth_ok, resolved_viewer, reject_reason = _authenticate_spectator_websocket(
        websocket,
        runtime=runtime,
        scope_type="tournament",
        scope_id=tournament_id,
    )
    if not auth_ok:
        await websocket.close(code=4401, reason=reject_reason or "Unauthorized tournament spectator handshake.")
        return

    await websocket.accept()

    client = runtime.match_room_manager.build_client(
        websocket=websocket,
        user_id=resolved_viewer.user_id,
        display_name=resolved_viewer.display_name,
    )
    await runtime.tournament_hub.join_room(tournament_id, client)
    await websocket.send_json(
        sanitize_public_spectator_payload(
            TournamentEvent(
                type="tournament_snapshot",
                tournament_id=tournament_id,
                featured_match_id=await runtime.tournament_hub.featured_match_id(tournament_id),
                payload={
                    "viewer_count": await runtime.tournament_hub.room_viewer_count(tournament_id),
                    "authenticated": bool(client.user_id),
                },
            ).model_dump(mode="json")
        )
    )

    sender_task = asyncio.create_task(_drain_client_queue(client), name=f"tournament-sender-{client.connection_id}")
    try:
        while True:
            message = await websocket.receive_json()
            await _handle_tournament_client_message(runtime, tournament_id, client, message)
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


def _enqueue_private_event(client: RoomClient, payload: dict[str, Any]) -> None:
    safe_payload = sanitize_public_spectator_payload(payload)
    if client.queue.full():
        with suppress(asyncio.QueueEmpty):
            client.queue.get_nowait()
    with suppress(asyncio.QueueFull):
        client.queue.put_nowait(safe_payload)


async def _handle_tournament_client_message(
    runtime: BroadcastRuntime,
    tournament_id: str,
    client: RoomClient,
    message: Any,
) -> None:
    if not isinstance(message, dict):
        return
    message_type = str(message.get("type") or "").strip().lower()
    if message_type not in {"ping", "heartbeat"}:
        return

    if not _check_client_rate_limit(runtime, client):
        _enqueue_private_event(
            client,
            TournamentEvent(
                type="rate_limit",
                tournament_id=tournament_id,
                payload={
                    "code": "rate_limit_exceeded",
                    "detail": "Message rate limit exceeded.",
                },
            ).model_dump(mode="json"),
        )
        return

    _enqueue_private_event(
        client,
        TournamentEvent(
            type="heartbeat",
            tournament_id=tournament_id,
            payload={"status": "ok"},
        ).model_dump(mode="json"),
    )


async def _handle_spectator_client_message(
    runtime: BroadcastRuntime,
    match_id: str,
    client: RoomClient,
    message: Any,
) -> None:
    if not isinstance(message, dict):
        return
    message_type = str(message.get("type") or "").strip().lower()
    if message_type not in {"ping", "heartbeat", "reaction", "chat_message"}:
        return

    if not _check_client_rate_limit(runtime, client):
        _enqueue_private_event(
            client,
            SpectatorEvent(
                type="rate_limit",
                match_id=match_id,
                user_id=None,
                display_name=client.display_name,
                payload={
                    "code": "rate_limit_exceeded",
                    "detail": "Message rate limit exceeded.",
                },
            ).model_dump(mode="json"),
        )
        return

    if message_type in {"ping", "heartbeat"}:
        await runtime.presence_service.heartbeat_viewer(match_id, client.connection_id, client.user_id)
        _enqueue_private_event(
            client,
            SpectatorEvent(
                type="heartbeat",
                match_id=match_id,
                user_id=None,
                payload={"status": "ok"},
            ).model_dump(mode="json"),
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
                user_id=None,
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
                user_id=None,
                display_name=client.display_name,
                message=chat_message,
                payload={
                    "authenticated": bool(client.user_id),
                },
            ),
            delay_seconds=0,
        )
        return


def _authenticate_spectator_websocket(
    websocket: WebSocket,
    *,
    runtime: BroadcastRuntime,
    scope_type: str,
    scope_id: str,
) -> tuple[bool, ResolvedViewer, str | None]:
    # 1. Explicitly reject raw bearer tokens in WebSocket URL query parameters
    for forbidden_param in ("token", "access_token", "bearer"):
        if websocket.query_params.get(forbidden_param) is not None:
            return (
                False,
                ResolvedViewer(user_id=None, display_name=None),
                "Bearer tokens are not permitted in WebSocket URLs; use a short-lived spectator ticket.",
            )

    guest_display_name = _fallback_display_name(websocket, is_authenticated=False)

    # 2. Validate short-lived, single-use, scope-bound spectator ticket if provided
    raw_ticket = websocket.query_params.get("ticket")
    if raw_ticket is not None:
        redeemed = runtime.redeem_spectator_ticket(
            raw_ticket,
            expected_scope_type=scope_type,
            expected_scope_id=scope_id,
        )
        if redeemed is None:
            return (
                False,
                ResolvedViewer(user_id=None, display_name=None),
                "Invalid, expired, wrong-scope, or replayed spectator ticket.",
            )
        resolved_name = redeemed.display_name or _fallback_display_name(websocket, is_authenticated=True)
        return (True, ResolvedViewer(user_id=redeemed.user_id, display_name=resolved_name), None)

    # 3. Optional non-URL authentication via HttpOnly cookie or Authorization header
    non_url_token: str | None = None
    cookie_token = websocket.cookies.get("gtex_access_token") or websocket.cookies.get("access_token")
    if cookie_token and cookie_token.strip():
        non_url_token = cookie_token.strip()
    else:
        authorization = websocket.headers.get("authorization")
        if authorization and authorization.lower().startswith("bearer "):
            non_url_token = authorization.split(" ", maxsplit=1)[1].strip()

    if not non_url_token:
        return (True, ResolvedViewer(user_id=None, display_name=guest_display_name), None)

    try:
        payload = decode_access_token(non_url_token)
    except TokenError:
        return (True, ResolvedViewer(user_id=None, display_name=guest_display_name), None)
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return (True, ResolvedViewer(user_id=None, display_name=guest_display_name), None)
    session_factory = getattr(websocket.scope["app"].state, "session_factory", None)
    if session_factory is None:
        token_name = str(payload.get("display_name") or payload.get("username") or "").strip()
        resolved_name = token_name or _fallback_display_name(websocket, is_authenticated=True)
        return (True, ResolvedViewer(user_id=subject, display_name=resolved_name), None)
    with session_factory() as session:
        user = session.get(User, subject)
        if user is None or not user.is_active:
            return (True, ResolvedViewer(user_id=None, display_name=guest_display_name), None)
        resolved_name = (user.display_name or user.username or "").strip() or None
        return (True, ResolvedViewer(user_id=user.id, display_name=resolved_name), None)


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
        active_user_ids=[],
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
