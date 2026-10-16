from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.observability.metrics import GTexMetrics
from app.observability.middleware import ObservabilityMiddleware


def test_observability_middleware_preserves_correlation_id() -> None:
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware, metrics=GTexMetrics(runtime_name="test"))

    @app.get("/probe/{item_id}")
    def probe(item_id: str, request: Request) -> dict[str, str]:
        return {
            "item_id": item_id,
            "correlation_id": request.state.correlation_id,
        }

    with TestClient(app) as client:
        response = client.get("/probe/alpha", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "request-123"
    assert response.json()["correlation_id"] == "request-123"


def test_observability_middleware_generates_correlation_id() -> None:
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware, metrics=GTexMetrics(runtime_name="test"))

    @app.get("/probe")
    def probe(request: Request) -> dict[str, str]:
        return {"correlation_id": request.state.correlation_id}

    with TestClient(app) as client:
        response = client.get("/probe")

    assert response.status_code == 200
    correlation_id = response.headers["X-Correlation-ID"]
    assert correlation_id.startswith("gtex-")
    assert response.json()["correlation_id"] == correlation_id
