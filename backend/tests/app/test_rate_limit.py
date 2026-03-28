from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware, ensure_api_rate_limiter


def test_rate_limit_middleware_throttles_repeated_auth_requests(monkeypatch) -> None:
    monkeypatch.setenv("GTE_AUTH_RATE_LIMIT_PER_MINUTE", "2")

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/auth/login")
    def login() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        headers = {"x-forwarded-for": "203.0.113.10"}
        first = client.post("/auth/login", headers=headers)
        second = client.post("/auth/login", headers=headers)
        third = client.post("/auth/login", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["scope"] == "auth"
    assert third.headers["X-RateLimit-Scope"] == "auth"
    assert third.headers["X-RateLimit-Limit"] == "2"

    snapshot = ensure_api_rate_limiter(app).snapshot()
    assert snapshot["active_bucket_count"] == 1
    assert snapshot["active_buckets_by_scope"] == {"auth": 1}
    assert snapshot["throttled_events"] == 1
