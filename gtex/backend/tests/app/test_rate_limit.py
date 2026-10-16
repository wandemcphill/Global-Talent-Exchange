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
