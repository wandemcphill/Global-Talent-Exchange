from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from threading import RLock
from typing import Any, Protocol

from fastapi import FastAPI, Request
from redis import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import error_response
from app.core.request_security import extract_access_token_subject, extract_client_ip

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    scope: str
    limit: int
    window_seconds: int
    remaining: int
    retry_after_seconds: int


class RateLimitStore(Protocol):
    def increment(self, *, key: str, window_seconds: int) -> tuple[int, int]: ...

    def snapshot(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class MemoryRateLimitStore:
    _lock: RLock = field(default_factory=RLock)
    _buckets: dict[str, tuple[int, datetime]] = field(default_factory=dict)

    def increment(self, *, key: str, window_seconds: int) -> tuple[int, int]:
        now = _utcnow()
        with self._lock:
            current, reset_at = self._buckets.get(key, (0, now + timedelta(seconds=window_seconds)))
            if reset_at <= now:
                current = 0
                reset_at = now + timedelta(seconds=window_seconds)
            current += 1
            self._buckets[key] = (current, reset_at)
            retry_after = max(1, int((reset_at - now).total_seconds()))
            return current, retry_after

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"backend": "memory", "bucket_count": len(self._buckets)}


class RedisRateLimitStore:
    _SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

    def __init__(self, redis_url: str):
        self.client = Redis.from_url(redis_url, decode_responses=True)
        self._script = self.client.register_script(self._SCRIPT)
        self._fallback = MemoryRateLimitStore()

    def increment(self, *, key: str, window_seconds: int) -> tuple[int, int]:
        try:
            current, ttl = self._script(keys=[key], args=[window_seconds])
            retry_after = max(1, int(ttl or window_seconds))
            return int(current), retry_after
        except RedisError:
            logger.warning("rate_limit.increment_failed_using_memory_fallback key=%s", key)
            return self._fallback.increment(key=key, window_seconds=window_seconds)

    def snapshot(self) -> dict[str, Any]:
        fallback_snapshot = self._fallback.snapshot()
        return {
            "backend": "redis",
            "redis_error_fallback": fallback_snapshot,
        }


@dataclass(slots=True)
class ApiRateLimiter:
    app: FastAPI
    settings: Settings
    store: RateLimitStore
    _throttled_events: int = 0

    EXEMPT_PREFIXES = ("/health", "/ready", "/version", "/docs", "/redoc", "/openapi.json")
    _WALLET_PREFIXES = ("/api/wallets", "/wallets", "/wallet")
    # Credential-handling endpoints. Matched by suffix against every mounted auth
    # prefix (/auth, /api/auth, /api/v2/auth) so adding a version alias can never
    # silently drop an endpoint back to the permissive default bucket.
    _AUTH_PATH_PREFIXES = ("/auth", "/api/auth", "/api/v2/auth")
    _AUTH_PATH_SUFFIXES = (
        "/login",
        "/register",
        "/signup",
        "/signup/user",
        "/signup/trader",
        "/signup/creator",
        "/refresh",
        "/change-password",
        "/confirm-email",
        "/recovery/request",
        "/recovery/reset",
    )

    def check_request(self, request: Request) -> RateLimitDecision | None:
        if request.method.upper() == "OPTIONS":
            return None
        path = request.url.path or "/"
        if path.startswith(self.EXEMPT_PREFIXES):
            return None
        if not self.settings.distributed_rate_limit_enabled:
            return None

        rule = self._rule_for_request(request)
        actor_key = self._actor_key(request)
        bucket_key = self._bucket_key(rule=rule, actor_key=actor_key)
        current, retry_after = self.store.increment(key=bucket_key, window_seconds=rule.window_seconds)
        if current <= 0:
            return None
        remaining = max(0, rule.limit - current)
        allowed = current <= rule.limit
        if not allowed:
            self._throttled_events += 1
            self._audit_rate_limit_hit(
                request=request,
                scope=rule.scope,
                limit=rule.limit,
                retry_after_seconds=retry_after,
            )
        return RateLimitDecision(
            allowed=allowed,
            scope=rule.scope,
            limit=rule.limit,
            window_seconds=rule.window_seconds,
            remaining=remaining,
            retry_after_seconds=retry_after,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.settings.distributed_rate_limit_enabled),
            "rules": [
                {
                    "scope": rule.scope,
                    "limit": rule.limit,
                    "window_seconds": rule.window_seconds,
                }
                for rule in self._rules()
            ],
            "throttled_events": self._throttled_events,
            "store": self.store.snapshot(),
        }

    def _rule_for_request(self, request: Request) -> RateLimitRule:
        path = (request.url.path or "/").lower()
        method = request.method.upper()
        if self._is_auth_path(path):
            return self._rules()[0]
        if path in {
            "/market/buy",
            "/market/sell",
            "/api/market/buy",
            "/api/market/sell",
            "/gtex/market/buy",
            "/gtex/market/sell",
            "/api/gtex/market/buy",
            "/api/gtex/market/sell",
            "/wallet/top-up/initiate",
            "/wallet/top-up/verify",
            "/api/wallet/top-up/initiate",
            "/api/wallet/top-up/verify",
        }:
            return self._rules()[1]
        if self._matches_prefix(path, "/api/market", "/market", "/api/gtex/market", "/gtex/market"):
            return self._rules()[2]
        if self._matches_prefix(path, *self._WALLET_PREFIXES):
            if method in {"GET", "HEAD"}:
                return self._rules()[3]
            return self._rules()[4]
        return self._rules()[5]

    @classmethod
    def _is_auth_path(cls, path: str) -> bool:
        for prefix in cls._AUTH_PATH_PREFIXES:
            if not path.startswith(f"{prefix}/"):
                continue
            remainder = path[len(prefix) :]
            if remainder in cls._AUTH_PATH_SUFFIXES:
                return True
        return False

    def _rules(self) -> tuple[RateLimitRule, ...]:
        return (
            RateLimitRule("auth", limit=self.settings.auth_rate_limit_per_minute, window_seconds=60),
            RateLimitRule("sensitive", limit=self.settings.sensitive_rate_limit_per_minute, window_seconds=60),
            RateLimitRule("market", limit=self.settings.market_rate_limit_per_minute, window_seconds=60),
            RateLimitRule("wallet_read", limit=self.settings.wallet_read_rate_limit_per_minute, window_seconds=60),
            RateLimitRule("wallet", limit=self.settings.wallet_rate_limit_per_minute, window_seconds=60),
            RateLimitRule("default", limit=self.settings.api_rate_limit_per_minute, window_seconds=60),
        )

    def _bucket_key(self, *, rule: RateLimitRule, actor_key: str) -> str:
        bucket = int(_utcnow().timestamp()) // rule.window_seconds
        return f"gte:rate_limit:{rule.scope}:{actor_key}:{bucket}"

    def _audit_rate_limit_hit(
        self,
        *,
        request: Request,
        scope: str,
        limit: int,
        retry_after_seconds: int,
    ) -> None:
        from app.risk_ops_engine.service import RiskOpsService

        session_factory = getattr(self.app.state, "session_factory", None)
        if session_factory is None:
            return
        with session_factory() as session:
            RiskOpsService(session).log_audit(
                actor_user_id=extract_access_token_subject(request),
                action_key="api.rate_limited",
                resource_type="http_request",
                resource_id=None,
                detail=f"Rate limit exceeded for scope '{scope}'.",
                metadata_json={
                    "scope": scope,
                    "limit": limit,
                    "retry_after_seconds": retry_after_seconds,
                    "path": request.url.path,
                    "method": request.method.upper(),
                    "client_ip": extract_client_ip(request),
                },
                outcome="blocked",
            )
            session.commit()

    def _actor_key(self, request: Request) -> str:
        user_id = extract_access_token_subject(request)
        if user_id:
            return f"user:{user_id}"
        return f"ip:{extract_client_ip(request)}"

    @staticmethod
    def _matches_prefix(path: str, *prefixes: str) -> bool:
        return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limiter = ensure_api_rate_limiter(request.app)
        decision = limiter.check_request(request)
        if decision is None:
            return await call_next(request)
        if not decision.allowed:
            return error_response(
                429,
                message="Rate limit exceeded. Please retry later.",
                code="rate_limit_exceeded",
                headers={
                    "Retry-After": str(decision.retry_after_seconds),
                    "X-RateLimit-Limit": str(decision.limit),
                    "X-RateLimit-Remaining": str(decision.remaining),
                    "X-RateLimit-Scope": decision.scope,
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Scope"] = decision.scope
        return response


def ensure_api_rate_limiter(app: FastAPI) -> ApiRateLimiter:
    limiter = getattr(app.state, "api_rate_limiter", None)
    if limiter is None:
        settings = getattr(app.state, "settings", None) or get_settings()
        store = _build_store(settings)
        limiter = ApiRateLimiter(app=app, settings=settings, store=store)
        app.state.api_rate_limiter = limiter
    return limiter


def _build_store(settings: Settings) -> RateLimitStore:
    if settings.redis_url:
        try:
            store = RedisRateLimitStore(settings.redis_url)
            store.client.ping()
            return store
        except Exception:
            logger.warning("rate_limit.redis_unavailable_falling_back_to_memory")
    return MemoryRateLimitStore()


__all__ = [
    "ApiRateLimiter",
    "RateLimitDecision",
    "RateLimitMiddleware",
    "RateLimitRule",
    "ensure_api_rate_limiter",
]
