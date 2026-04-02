from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import os
from threading import RLock
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_security import extract_access_token_subject, extract_client_ip


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    scope: str
    limit: int
    window_seconds: int


@dataclass(slots=True)
class RateLimitBucketState:
    count: int
    reset_at: datetime
    last_seen_at: datetime
    audited: bool = False


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    scope: str
    limit: int
    window_seconds: int
    remaining: int
    retry_after_seconds: int


@dataclass(slots=True)
class ApiRateLimiter:
    app: FastAPI
    _lock: RLock = field(default_factory=RLock)
    _buckets: dict[str, RateLimitBucketState] = field(default_factory=dict)
    _throttled_events: int = 0

    EXEMPT_PREFIXES = ("/health", "/ready", "/version", "/docs", "/redoc", "/openapi.json")

    def check_request(self, request: Request) -> RateLimitDecision | None:
        if request.method.upper() == "OPTIONS":
            return None
        path = request.url.path or "/"
        if path.startswith(self.EXEMPT_PREFIXES):
            return None
        rule = self._rule_for_request(request)
        actor_key = self._actor_key(request)
        bucket_key = f"{rule.scope}:{actor_key}"
        now = _utcnow()
        with self._lock:
            self._purge_expired_buckets_unlocked(now=now)
            bucket = self._buckets.get(bucket_key)
            if bucket is None or bucket.reset_at <= now:
                bucket = RateLimitBucketState(
                    count=0,
                    reset_at=now + timedelta(seconds=rule.window_seconds),
                    last_seen_at=now,
                )
                self._buckets[bucket_key] = bucket
            bucket.count += 1
            bucket.last_seen_at = now
            remaining = max(0, rule.limit - bucket.count)
            allowed = bucket.count <= rule.limit
            retry_after_seconds = max(1, int((bucket.reset_at - now).total_seconds()))
            if not allowed:
                self._throttled_events += 1
                if not bucket.audited:
                    self._audit_rate_limit_hit(
                        request=request,
                        scope=rule.scope,
                        limit=rule.limit,
                        retry_after_seconds=retry_after_seconds,
                    )
                    bucket.audited = True
            return RateLimitDecision(
                allowed=allowed,
                scope=rule.scope,
                limit=rule.limit,
                window_seconds=rule.window_seconds,
                remaining=remaining,
                retry_after_seconds=retry_after_seconds,
            )

    def snapshot(self) -> dict[str, Any]:
        now = _utcnow()
        with self._lock:
            self._purge_expired_buckets_unlocked(now=now)
            by_scope: dict[str, int] = {}
            for key in self._buckets:
                scope = key.split(":", 1)[0]
                by_scope[scope] = by_scope.get(scope, 0) + 1
            return {
                "enabled": True,
                "rules": [
                    {
                        "scope": rule.scope,
                        "limit": rule.limit,
                        "window_seconds": rule.window_seconds,
                    }
                    for rule in self._rules()
                ],
                "active_bucket_count": len(self._buckets),
                "active_buckets_by_scope": by_scope,
                "throttled_events": self._throttled_events,
            }

    def _rule_for_request(self, request: Request) -> RateLimitRule:
        path = (request.url.path or "/").lower()
        if path in {"/auth/login", "/api/auth/login"}:
            return self._rules()[0]
        if path.startswith("/integrations/payments/") and path.endswith("/webhook"):
            return self._rules()[5]
        if path in {
            "/market/buy",
            "/market/sell",
            "/api/market/buy",
            "/api/market/sell",
            "/gtex/market/buy",
            "/gtex/market/sell",
            "/api/gtex/market/buy",
            "/api/gtex/market/sell",
        }:
            return self._rules()[1]
        if self._matches_prefix(path, "/api/market", "/market", "/api/gtex/market", "/gtex/market"):
            return self._rules()[3]
        if self._matches_prefix(path, "/api/wallets", "/wallets", "/wallet"):
            return self._rules()[2]
        return self._rules()[4]

    def _rules(self) -> tuple[RateLimitRule, ...]:
        return (
            RateLimitRule("auth", limit=self._env_int("GTE_AUTH_RATE_LIMIT_PER_MINUTE", 10), window_seconds=60),
            RateLimitRule("market_trade", limit=self._env_int("GTE_MARKET_TRADE_RATE_LIMIT_PER_MINUTE", 10), window_seconds=60),
            RateLimitRule("wallet", limit=self._env_int("GTE_WALLET_RATE_LIMIT_PER_MINUTE", 50), window_seconds=60),
            RateLimitRule("market", limit=self._env_int("GTE_MARKET_RATE_LIMIT_PER_MINUTE", 40), window_seconds=60),
            RateLimitRule("default", limit=self._env_int("GTE_API_RATE_LIMIT_PER_MINUTE", 100), window_seconds=60),
            RateLimitRule("payment_webhook", limit=self._env_int("GTE_PAYMENT_WEBHOOK_RATE_LIMIT_PER_MINUTE", 120), window_seconds=60),
        )

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

    def _purge_expired_buckets_unlocked(self, *, now: datetime) -> None:
        expired_keys = [key for key, state in self._buckets.items() if state.reset_at <= now]
        for key in expired_keys:
            self._buckets.pop(key, None)

    def _actor_key(self, request: Request) -> str:
        user_id = extract_access_token_subject(request)
        if user_id:
            return f"user:{user_id}"
        return f"ip:{extract_client_ip(request)}"

    @staticmethod
    def _matches_prefix(path: str, *prefixes: str) -> bool:
        return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return max(1, int(os.getenv(name, str(default)).strip()))
        except (TypeError, ValueError, AttributeError):
            return default


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limiter = ensure_api_rate_limiter(request.app)
        decision = limiter.check_request(request)
        if decision is None:
            return await call_next(request)
        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please retry later.",
                    "scope": decision.scope,
                    "retry_after_seconds": decision.retry_after_seconds,
                },
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
        limiter = ApiRateLimiter(app=app)
        app.state.api_rate_limiter = limiter
    return limiter


__all__ = [
    "ApiRateLimiter",
    "RateLimitDecision",
    "RateLimitMiddleware",
    "RateLimitRule",
    "ensure_api_rate_limiter",
]
