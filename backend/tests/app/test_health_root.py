from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.api_contract import build_versioned_path
from app.core.health import router as health_router


def test_root_route_returns_service_metadata_and_is_hidden_from_schema() -> None:
    app = FastAPI()
    app.state.settings = SimpleNamespace(app_name="GTEX API")
    app.include_router(health_router)

    with TestClient(app) as client:
        response = client.get("/")
        head_response = client.head("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "GTEX API",
        "docs_url": "/docs",
        "health_url": "/health",
        "ready_url": "/ready",
        "version_url": "/version",
    }
    assert head_response.status_code == 200
    assert "/" not in app.openapi()["paths"]


def test_build_versioned_path_skips_root() -> None:
    assert build_versioned_path("/") is None
