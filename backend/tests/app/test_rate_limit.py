from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from redis.exceptions import RedisError

from app.core.config import reset_settings_cache
from app.core.rate_limit import RateLimitMiddleware, RedisRateLimitStore


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(
        user_id,
        claims={"sid": f"{user_id}-session"},
    )
    return {"Authorization": f"Bearer {token}"}


def _build_client() -> TestClient:
    reset_settings_cache()
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/feed")
    def read_feed() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/market/players")
    def read_market_players() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/wallets/summary")
    def read_wallet_summary() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_rate_limit_is_scoped_per_authenticated_user(monkeypatch) -> None:
    monkeypatch.setenv("GTE_API_RATE_LIMIT_PER_MINUTE", "2")
    client = _build_client()

    first_user = _auth_header("user-one")
    second_user = _auth_header("user-two")

    assert client.get("/feed", headers=first_user).status_code == 200
    assert client.get("/feed", headers=first_user).status_code == 200
    blocked = client.get("/feed", headers=first_user)
    assert blocked.status_code == 429
    assert blocked.headers["X-RateLimit-Scope"] == "default"

    assert client.get("/feed", headers=second_user).status_code == 200


def test_market_and_wallet_paths_use_stricter_limits(monkeypatch) -> None:
    monkeypatch.setenv("GTE_API_RATE_LIMIT_PER_MINUTE", "5")
    monkeypatch.setenv("GTE_MARKET_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("GTE_WALLET_RATE_LIMIT_PER_MINUTE", "3")
    client = _build_client()
    headers = _auth_header("market-wallet-user")

    assert client.get("/market/players", headers=headers).status_code == 200
    assert client.get("/market/players", headers=headers).status_code == 200
    market_blocked = client.get("/market/players", headers=headers)
    assert market_blocked.status_code == 429
    assert market_blocked.headers["X-RateLimit-Scope"] == "market"

    assert client.get("/wallets/summary", headers=headers).status_code == 200
    assert client.get("/wallets/summary", headers=headers).status_code == 200
    assert client.get("/wallets/summary", headers=headers).status_code == 200
    wallet_blocked = client.get("/wallets/summary", headers=headers)
    assert wallet_blocked.status_code == 429
    assert wallet_blocked.headers["X-RateLimit-Scope"] == "wallet"


def test_redis_rate_limit_store_uses_memory_fallback_on_increment_errors() -> None:
    store = RedisRateLimitStore("redis://127.0.0.1:1/0")

    def fail_increment(*, keys, args):
        del keys, args
        raise RedisError("redis unavailable")

    store._script = fail_increment

    first, _ = store.increment(key="test:bucket", window_seconds=60)
    second, _ = store.increment(key="test:bucket", window_seconds=60)

    assert first == 1
    assert second == 2
    assert store.snapshot()["redis_error_fallback"]["backend"] == "memory"


def test_resilient_store_falls_back_to_memory_and_recovers_after_backoff(
    monkeypatch, caplog
) -> None:
    import logging

    from app.core import rate_limit as rate_limit_module

    clock_state = {"now": 0.0}
    created: list[_FailingRedisStore] = []

    class _FailingRedisStore:
        def __init__(self, redis_url: str) -> None:
            self.redis_url = redis_url
            self.fail = True
            self.calls = 0
            created.append(self)

        def increment_strict(self, *, key: str, window_seconds: int) -> tuple[int, int]:
            self.calls += 1
            if self.fail:
                raise RedisError("redis unavailable")
            return 1, window_seconds

    monkeypatch.setattr(rate_limit_module, "RedisRateLimitStore", _FailingRedisStore)

    store = rate_limit_module.ResilientRateLimitStore(
        "redis://127.0.0.1:1/0",
        clock=lambda: clock_state["now"],
        retry_backoff_seconds=30.0,
    )

    with caplog.at_level(logging.ERROR, logger="app.core.rate_limit"):
        first, _ = store.increment(key="test:bucket", window_seconds=60)
        second, _ = store.increment(key="test:bucket", window_seconds=60)

    assert first == 1
    assert second == 2
    assert created[0].calls == 1  # backoff suppresses further Redis calls
    assert store.degraded is True
    assert caplog.text.count("rate_limit.redis_unavailable_falling_back_to_memory") == 1

    created[0].fail = False
    clock_state["now"] += 31.0

    with caplog.at_level(logging.INFO, logger="app.core.rate_limit"):
        third, _ = store.increment(key="test:bucket", window_seconds=60)

    assert third == 1  # fresh Redis-backed bucket
    assert created[0].calls == 2
    assert store.degraded is False
    assert "rate_limit.redis_recovered" in caplog.text


def test_resilient_store_retries_redis_after_backoff_and_stays_degraded_on_failure(
    monkeypatch, caplog
) -> None:
    import logging

    from app.core import rate_limit as rate_limit_module

    clock_state = {"now": 0.0}
    created: list[_AlwaysFailingRedisStore] = []

    class _AlwaysFailingRedisStore:
        def __init__(self, redis_url: str) -> None:
            self.calls = 0
            created.append(self)

        def increment_strict(self, *, key: str, window_seconds: int) -> tuple[int, int]:
            self.calls += 1
            raise RedisError("redis unavailable")

    monkeypatch.setattr(rate_limit_module, "RedisRateLimitStore", _AlwaysFailingRedisStore)

    store = rate_limit_module.ResilientRateLimitStore(
        "redis://127.0.0.1:1/0",
        clock=lambda: clock_state["now"],
        retry_backoff_seconds=30.0,
    )

    with caplog.at_level(logging.ERROR, logger="app.core.rate_limit"):
        store.increment(key="test:bucket", window_seconds=60)
        clock_state["now"] += 31.0
        store.increment(key="test:bucket", window_seconds=60)
        clock_state["now"] += 31.0
        store.increment(key="test:bucket", window_seconds=60)

    assert created[0].calls == 3  # probed again after each backoff window
    assert store.degraded is True
    assert caplog.text.count("rate_limit.redis_unavailable_falling_back_to_memory") == 1


def test_build_store_uses_memory_store_without_redis_url() -> None:
    from app.core import rate_limit as rate_limit_module
    from app.core.config import get_settings, reset_settings_cache

    reset_settings_cache()
    settings = get_settings()
    assert not settings.redis_url
    store = rate_limit_module._build_store(settings)
    assert isinstance(store, rate_limit_module.MemoryRateLimitStore)


def test_share_event_paths_use_sensitive_rate_limit_bucket() -> None:
    from types import SimpleNamespace

    from starlette.requests import Request

    from app.core.rate_limit import ApiRateLimiter

    settings = SimpleNamespace(
        auth_rate_limit_per_minute=5,
        sensitive_rate_limit_per_minute=7,
        market_rate_limit_per_minute=10,
        wallet_read_rate_limit_per_minute=20,
        wallet_rate_limit_per_minute=15,
        api_rate_limit_per_minute=60,
        distributed_rate_limit_enabled=True,
    )
    limiter = ApiRateLimiter(
        app=FastAPI(),
        settings=settings,
        store=rate_limit_module_placeholder(),
    )

    def _request(path: str) -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": path,
                "headers": [],
                "client": ("10.0.0.1", 1234),
            }
        )

    for path in (
        "/api/challenges/challenge-1/share-events",
        "/api/match-share-links/abc123/events",
    ):
        rule = limiter._rule_for_request(_request(path))
        assert rule.scope == "sensitive", path


def rate_limit_module_placeholder():
    from app.core.rate_limit import MemoryRateLimitStore

    return MemoryRateLimitStore()
