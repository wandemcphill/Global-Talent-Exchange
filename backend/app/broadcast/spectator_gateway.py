from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import hashlib
import logging
import os
import re
import secrets
import time
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, decode_access_token
from app.broadcast.broadcast_models import (
    MatchSnapshot,
    SpectatorEvent,
    SpectatorPresenceView,
    TournamentEvent,
)
from app.broadcast.match_room_manager import (
    MatchRoomManager,
    RoomClient,
    sanitize_public_spectator_payload,
)
from app.broadcast.presence_service import PresenceService
from app.broadcast.tournament_hub import TournamentBroadcastHub
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["broadcast"])

_DELAY_ENV = "GTE_BROADCAST_DELAY_SECONDS"
_PRESENCE_TTL_ENV = "GTE_BROADCAST_PRESENCE_TTL_SECONDS"
_HEARTBEAT_ENV = "GTE_BROADCAST_HEARTBEAT_INTERVAL_SECONDS"
_QUEUE_ENV = "GTE_BROADCAST_MAX_PENDING_MESSAGES"
_APP_ENV_VARS = ("GTE_APP_ENV", "APP_ENV", "ENVIRONMENT")

MAX_TICKET_TTL_SECONDS: float = 30.0

_TICKET_QUERY_LOG_RE = re.compile(r"""([?&]ticket=)[^&\s"']+""", re.IGNORECASE)
_TICKET_JSON_LOG_RE = re.compile(r'("ticket"\s*:\s*")[^"]+(")', re.IGNORECASE)


def redact_ticket_from_log_text(text: str) -> str:
    """Redacts spectator ticket values from URLs and JSON payloads in log messages."""
    redacted = _TICKET_QUERY_LOG_RE.sub(r"\1[REDACTED]", str(text))
    return _TICKET_JSON_LOG_RE.sub(r"\1[REDACTED]\2", redacted)


class SpectatorTicketLogRedactionFilter(logging.Filter):
    """Logging filter that prevents raw spectator tickets from appearing in app or access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_ticket_from_log_text(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact_ticket_from_log_text(arg) if isinstance(arg, str) else arg for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: redact_ticket_from_log_text(v) if isinstance(v, str) else v for k, v in record.args.items()
                }
        return True


for _log_name in (__name__, "uvicorn.access", "fastapi"):
    _target_logger = logging.getLogger(_log_name)
    if not any(isinstance(f, SpectatorTicketLogRedactionFilter) for f in _target_logger.filters):
        _target_logger.addFilter(SpectatorTicketLogRedactionFilter())


def ticket_sha256_digest(raw_ticket: str) -> str:
    """Computes the hex-encoded SHA-256 digest of a spectator ticket."""
    return hashlib.sha256(str(raw_ticket).strip().encode("utf-8")).hexdigest()


class SpectatorTicketStoreError(RuntimeError):
    """Raised when the authoritative Redis ticket store is unavailable in a protected runtime."""


class SpectatorTicketRateLimitError(RuntimeError):
    """Raised when a user exceeds the spectator ticket issuance rate limit."""


_STORE_TICKET_LUA = """
redis.call("HSET", KEYS[1],
    "user_id", ARGV[1],
    "display_name", ARGV[2],
    "scope_type", ARGV[3],
    "scope_id", ARGV[4],
    "expires_at_ms", ARGV[5]
)
redis.call("PEXPIRE", KEYS[1], tonumber(ARGV[6]))
return 1
"""

_REDEEM_TICKET_LUA = """
if redis.call("EXISTS", KEYS[1]) == 0 then
    return nil
end
local expires_at_ms = tonumber(redis.call("HGET", KEYS[1], "expires_at_ms") or "0")
local now_ms = tonumber(ARGV[1])
if now_ms >= expires_at_ms then
    redis.call("DEL", KEYS[1])
    return nil
end
local scope_type = redis.call("HGET", KEYS[1], "scope_type")
local scope_id = redis.call("HGET", KEYS[1], "scope_id")
if scope_type ~= ARGV[2] or scope_id ~= ARGV[3] then
    return nil
end
local user_id = redis.call("HGET", KEYS[1], "user_id")
local display_name = redis.call("HGET", KEYS[1], "display_name") or ""
redis.call("DEL", KEYS[1])
return {user_id, display_name}
"""

_RATE_LIMIT_TICKET_LUA = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local max_allowed = tonumber(ARGV[3])
local member_id = ARGV[4]

local cutoff_ms = now_ms - window_ms
redis.call("ZREMRANGEBYSCORE", key, "-inf", cutoff_ms)
local current = tonumber(redis.call("ZCARD", key))
if current >= max_allowed then
    return 0
end
redis.call("ZADD", key, now_ms, member_id)
redis.call("PEXPIRE", key, window_ms)
return 1
"""


class AsyncEvalRedisEmulator:
    """
    Thread/coroutine-safe in-memory evaluator for unit tests without a live Redis daemon.
    Can be shared across multiple BroadcastRuntime instances to test multi-worker ticket redemption
    and sorted-set rate limiting. Never used in production/staging environments.
    """

    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, str]] = {}
        self._counters: dict[str, int] = {}
        self._sorted_sets: dict[str, list[tuple[int, str]]] = {}
        self._expires_at_ms: dict[str, int] = {}
        self._lock = asyncio.Lock()

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _evict_if_expired(self, key: str, now_ms: int) -> None:
        exp = self._expires_at_ms.get(key)
        if exp is not None and now_ms >= exp:
            self._hashes.pop(key, None)
            self._counters.pop(key, None)
            self._sorted_sets.pop(key, None)
            self._expires_at_ms.pop(key, None)

    async def eval(self, script: str, numkeys: int, *keys_and_args: Any) -> Any:
        async with self._lock:
            now_ms = self._now_ms()
            keys = [str(k) for k in keys_and_args[:numkeys]]
            argv = [str(a) for a in keys_and_args[numkeys:]]
            key = keys[0]
            self._evict_if_expired(key, now_ms)

            if script == _STORE_TICKET_LUA:
                self._hashes[key] = {
                    "user_id": argv[0],
                    "display_name": argv[1],
                    "scope_type": argv[2],
                    "scope_id": argv[3],
                    "expires_at_ms": argv[4],
                }
                ttl_ms = max(1, int(argv[5]))
                self._expires_at_ms[key] = now_ms + ttl_ms
                return 1

            if script == _REDEEM_TICKET_LUA:
                record = self._hashes.get(key)
                if record is None:
                    return None
                req_now_ms = int(argv[0])
                exp_ms = int(record.get("expires_at_ms") or "0")
                if req_now_ms >= exp_ms:
                    self._hashes.pop(key, None)
                    self._expires_at_ms.pop(key, None)
                    return None
                if record.get("scope_type") != argv[1] or record.get("scope_id") != argv[2]:
                    return None
                user_id = record.get("user_id") or ""
                display_name = record.get("display_name") or ""
                self._hashes.pop(key, None)
                self._expires_at_ms.pop(key, None)
                return [user_id, display_name]

            if script == _RATE_LIMIT_TICKET_LUA:
                req_now_ms = int(argv[0])
                window_ms = max(1, int(argv[1]))
                max_allowed = max(1, int(argv[2]))
                member_id = argv[3]
                cutoff_ms = req_now_ms - window_ms
                entries = self._sorted_sets.setdefault(key, [])
                entries = [item for item in entries if item[0] > cutoff_ms]
                if len(entries) >= max_allowed:
                    self._sorted_sets[key] = entries
                    return 0
                entries.append((req_now_ms, member_id))
                self._sorted_sets[key] = entries
                self._expires_at_ms[key] = req_now_ms + window_ms
                return 1

            raise RedisError("Unsupported script in AsyncEvalRedisEmulator")

    async def hgetall(self, key: str) -> dict[str, str]:
        async with self._lock:
            self._evict_if_expired(key, self._now_ms())
            return dict(self._hashes.get(key, {}))

    async def keys(self, pattern: str = "*") -> list[str]:
        async with self._lock:
            now_ms = self._now_ms()
            for k in list(self._expires_at_ms.keys()):
                self._evict_if_expired(k, now_ms)
            return list(self._hashes.keys()) + list(self._counters.keys()) + list(self._sorted_sets.keys())

    async def aclose(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class ResolvedViewer:
    user_id: str | None
    display_name: str | None


@dataclass(slots=True)
class RedisSpectatorTicketStore:
    redis_url: str | None = None
    prefix: str = "gtex:broadcast:spectator"
    default_ttl_seconds: float = MAX_TICKET_TTL_SECONDS
    require_redis: bool = False
    redis_client: Any = None
    _owned_redis: redis_asyncio.Redis | None = field(init=False, default=None)
    _test_emulator: AsyncEvalRedisEmulator | None = field(init=False, default=None)

    def _is_redis_mandatory(self) -> bool:
        if self.require_redis or bool(self.redis_url):
            return True
        for env_key in _APP_ENV_VARS:
            env_val = str(os.getenv(env_key, "") or "").strip().lower()
            if env_val in {"production", "prod", "staging"}:
                return True
        return False

    async def _get_backend(self) -> Any:
        if self.redis_client is not None:
            return self.redis_client
        if self.redis_url:
            if self._owned_redis is None:
                self._owned_redis = redis_asyncio.Redis.from_url(self.redis_url, decode_responses=True)
            return self._owned_redis
        if self._is_redis_mandatory():
            raise SpectatorTicketStoreError(
                "Authoritative Redis ticket store is required in production/staging but redis_url is not configured."
            )
        if self._test_emulator is None:
            self._test_emulator = AsyncEvalRedisEmulator()
        return self._test_emulator

    def ticket_key_from_digest(self, digest: str) -> str:
        return f"{self.prefix}:ticket:{digest}"

    def rate_limit_key(self, user_id: str) -> str:
        return f"{self.prefix}:ticket_rl:{user_id}"

    async def check_issuance_rate_limit(
        self,
        user_id: str,
        *,
        max_tickets: int,
        window_seconds: float,
        now_ms: int | None = None,
    ) -> bool:
        """Atomically checks a sliding window; now_ms is injectable for deterministic tests."""
        backend = await self._get_backend()
        request_time_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        window_ms = max(100, int(round(max(float(window_seconds), 0.1) * 1000)))
        limit = max(1, int(max_tickets))
        member_id = f"{request_time_ms}:{secrets.token_hex(8)}"
        try:
            allowed = await backend.eval(
                _RATE_LIMIT_TICKET_LUA,
                1,
                self.rate_limit_key(user_id),
                str(request_time_ms),
                str(window_ms),
                str(limit),
                member_id,
            )
            return bool(int(allowed or 0) == 1)
        except (RedisError, OSError, RuntimeError) as exc:
            logger.error("broadcast.ticket.rate_limit_store_error error=%s", type(exc).__name__)
            raise SpectatorTicketStoreError("Ticket rate-limit backend unavailable.") from exc

    async def issue_ticket(
        self,
        *,
        user_id: str,
        display_name: str | None,
        scope_type: str,
        scope_id: str,
        ttl_seconds: float | None = None,
    ) -> dict[str, Any]:
        backend = await self._get_backend()
        requested_ttl = float(self.default_ttl_seconds if ttl_seconds is None else ttl_seconds)
        effective_ttl = min(max(requested_ttl, 0.001), MAX_TICKET_TTL_SECONDS)
        ttl_ms = max(1, min(int(round(effective_ttl * 1000)), int(MAX_TICKET_TTL_SECONDS * 1000)))
        now_ms = int(time.time() * 1000)
        expires_at_ms = now_ms + ttl_ms

        raw_ticket = secrets.token_urlsafe(32)
        digest = ticket_sha256_digest(raw_ticket)
        redis_key = self.ticket_key_from_digest(digest)
        normalized_scope_type = str(scope_type).strip().lower()
        normalized_scope_id = str(scope_id).strip()

        try:
            await backend.eval(
                _STORE_TICKET_LUA,
                1,
                redis_key,
                str(user_id).strip(),
                str(display_name or "").strip(),
                normalized_scope_type,
                normalized_scope_id,
                str(expires_at_ms),
                str(ttl_ms),
            )
        except (RedisError, OSError, RuntimeError) as exc:
            logger.error(
                "broadcast.ticket.issue_failed scope=%s:%s error=%s",
                normalized_scope_type,
                normalized_scope_id,
                type(exc).__name__,
            )
            raise SpectatorTicketStoreError("Failed to persist spectator ticket in Redis.") from exc

        return {
            "ticket": raw_ticket,
            "ticket_digest": digest,
            "scope_type": normalized_scope_type,
            "scope_id": normalized_scope_id,
            "expires_in": max(1, min(int(round(effective_ttl)), int(MAX_TICKET_TTL_SECONDS))),
        }

    async def redeem_ticket(
        self,
        raw_ticket: str,
        *,
        expected_scope_type: str,
        expected_scope_id: str,
    ) -> ResolvedViewer | None:
        cleaned = str(raw_ticket or "").strip()
        if not cleaned:
            return None
        try:
            backend = await self._get_backend()
        except SpectatorTicketStoreError:
            # Fail closed when Redis is mandatory/unavailable
            return None

        digest = ticket_sha256_digest(cleaned)
        redis_key = self.ticket_key_from_digest(digest)
        now_ms = int(time.time() * 1000)
        normalized_scope_type = str(expected_scope_type).strip().lower()
        normalized_scope_id = str(expected_scope_id).strip()

        try:
            result = await backend.eval(
                _REDEEM_TICKET_LUA,
                1,
                redis_key,
                str(now_ms),
                normalized_scope_type,
                normalized_scope_id,
            )
        except (RedisError, OSError, RuntimeError) as exc:
            logger.error(
                "broadcast.ticket.redeem_failed scope=%s:%s error=%s",
                normalized_scope_type,
                normalized_scope_id,
                type(exc).__name__,
            )
            # Fail closed on Redis errors
            return None

        if not result or not isinstance(result, (list, tuple)) or len(result) < 1:
            return None
        user_id = str(result[0] or "").strip()
        if not user_id:
            return None
        display_name = str(result[1] or "").strip() if len(result) > 1 else ""
        return ResolvedViewer(user_id=user_id, display_name=display_name or None)

    async def aclose(self) -> None:
        if self._owned_redis is not None:
            try:
                await self._owned_redis.aclose()
            except RedisError:
                pass
            finally:
                self._owned_redis = None


@dataclass(slots=True)
class BroadcastRuntime:
    redis_url: str | None
    delay_seconds: int = 3
    viewer_ttl_seconds: int = 45
    heartbeat_interval_seconds: int = 15
    max_queue_size: int = 256
    rate_limit_max_messages: int = 5
    rate_limit_window_seconds: float = 5.0
    ticket_ttl_seconds: float = MAX_TICKET_TTL_SECONDS
    ticket_rate_limit_max: int = 10
    ticket_rate_limit_window_seconds: float = 60.0
    require_redis_tickets: bool = False
    ticket_redis_client: Any = None
    presence_service: PresenceService = field(init=False)
    match_room_manager: MatchRoomManager = field(init=False)
    tournament_hub: TournamentBroadcastHub = field(init=False)
    ticket_store: RedisSpectatorTicketStore = field(init=False)

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
        self.ticket_store = RedisSpectatorTicketStore(
            redis_url=self.redis_url,
            default_ttl_seconds=min(float(self.ticket_ttl_seconds), MAX_TICKET_TTL_SECONDS),
            require_redis=self.require_redis_tickets,
            redis_client=self.ticket_redis_client,
        )

    async def issue_spectator_ticket(
        self,
        *,
        user_id: str,
        display_name: str | None,
        scope_type: str,
        scope_id: str,
        ttl_seconds: float | None = None,
        enforce_rate_limit: bool = True,
    ) -> dict[str, Any]:
        self.ticket_store.require_redis = self.require_redis_tickets
        if self.ticket_redis_client is not None:
            self.ticket_store.redis_client = self.ticket_redis_client

        if enforce_rate_limit:
            allowed = await self.ticket_store.check_issuance_rate_limit(
                user_id,
                max_tickets=self.ticket_rate_limit_max,
                window_seconds=self.ticket_rate_limit_window_seconds,
            )
            if not allowed:
                raise SpectatorTicketRateLimitError("Ticket issuance rate limit exceeded.")

        effective_ttl = self.ticket_ttl_seconds if ttl_seconds is None else ttl_seconds
        return await self.ticket_store.issue_ticket(
            user_id=user_id,
            display_name=display_name,
            scope_type=scope_type,
            scope_id=scope_id,
            ttl_seconds=effective_ttl,
        )

    async def redeem_spectator_ticket(
        self,
        ticket: str,
        *,
        expected_scope_type: str,
        expected_scope_id: str,
    ) -> ResolvedViewer | None:
        self.ticket_store.require_redis = self.require_redis_tickets
        if self.ticket_redis_client is not None:
            self.ticket_store.redis_client = self.ticket_redis_client
        return await self.ticket_store.redeem_ticket(
            ticket,
            expected_scope_type=expected_scope_type,
            expected_scope_id=expected_scope_id,
        )

    async def match_snapshot(self, match_id: str, *, metadata: dict[str, Any] | None = None) -> MatchSnapshot:
        presence = await self.presence_service.get_match_presence(match_id)
        safe_metadata = sanitize_public_spectator_payload(dict(metadata or {}), _is_root=False)
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
            self.ticket_store.aclose(),
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


def _is_protected_app_env(app: Any) -> bool:
    settings = getattr(getattr(app, "state", None), "settings", None)
    app_env = str(getattr(settings, "app_env", "") or "").strip().lower()
    if app_env in {"production", "prod", "staging"}:
        return True
    for env_key in _APP_ENV_VARS:
        if str(os.getenv(env_key, "") or "").strip().lower() in {"production", "prod", "staging"}:
            return True
    return False


def ensure_broadcast_runtime(app) -> BroadcastRuntime:
    runtime = getattr(app.state, "broadcast_runtime", None)
    if runtime is not None:
        if _is_protected_app_env(app):
            runtime.require_redis_tickets = True
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
        require_redis_tickets=_is_protected_app_env(app),
    )
    app.state.broadcast_runtime = runtime
    app.state.broadcast = runtime
    return runtime


@router.post("/matches/{match_id}/spectate-ticket")
async def create_match_spectate_ticket(
    match_id: str,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issues a short-lived (<=30s), single-use, match-scoped WebSocket ticket stored as SHA-256 in Redis."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user_id = str(getattr(current_user, "id", "") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    display_name = (
        str(getattr(current_user, "display_name", None) or getattr(current_user, "username", None) or "").strip()
        or None
    )
    runtime = ensure_broadcast_runtime(request.app)
    try:
        issued = await runtime.issue_spectator_ticket(
            user_id=user_id,
            display_name=display_name,
            scope_type="match",
            scope_id=match_id,
        )
    except SpectatorTicketRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ticket issuance rate limit exceeded.",
        ) from exc
    except SpectatorTicketStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spectator ticket service temporarily unavailable.",
        ) from exc

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
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issues a short-lived (<=30s), single-use, tournament-scoped WebSocket ticket stored as SHA-256 in Redis."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    user_id = str(getattr(current_user, "id", "") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    display_name = (
        str(getattr(current_user, "display_name", None) or getattr(current_user, "username", None) or "").strip()
        or None
    )
    runtime = ensure_broadcast_runtime(request.app)
    try:
        issued = await runtime.issue_spectator_ticket(
            user_id=user_id,
            display_name=display_name,
            scope_type="tournament",
            scope_id=tournament_id,
        )
    except SpectatorTicketRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ticket issuance rate limit exceeded.",
        ) from exc
    except SpectatorTicketStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spectator ticket service temporarily unavailable.",
        ) from exc

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
    auth_ok, resolved_viewer, reject_reason = await _authenticate_spectator_websocket(
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
    auth_ok, resolved_viewer, reject_reason = await _authenticate_spectator_websocket(
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


_FORBIDDEN_WS_QUERY_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "access_token",
        "accesstoken",
        "bearer",
        "auth_token",
        "authtoken",
        "authorization",
        "jwt",
    }
)


async def _authenticate_spectator_websocket(
    websocket: WebSocket,
    *,
    runtime: BroadcastRuntime,
    scope_type: str,
    scope_id: str,
) -> tuple[bool, ResolvedViewer, str | None]:
    # 1. Case-insensitively reject any raw bearer token in WebSocket URL query parameters
    for query_key in websocket.query_params.keys():
        if str(query_key).strip().lower() in _FORBIDDEN_WS_QUERY_KEYS:
            return (
                False,
                ResolvedViewer(user_id=None, display_name=None),
                "Bearer tokens are not permitted in WebSocket URLs; use a short-lived spectator ticket.",
            )

    guest_display_name = _fallback_display_name(websocket, is_authenticated=False)

    # 2. Validate short-lived, single-use, scope-bound spectator ticket via Redis if provided
    raw_ticket = None
    for k, v in websocket.query_params.items():
        if str(k).strip().lower() == "ticket":
            raw_ticket = v
            break

    if raw_ticket is not None:
        redeemed = await runtime.redeem_spectator_ticket(
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
            normalized.startswith(f"{tok} ") or normalized.endswith(f" {tok}") for tok in _IMPERSONATION_TOKENS
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
