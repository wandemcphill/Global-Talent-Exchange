from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_optional_current_user
from app.core.api_contract import build_versioned_path
from app.core.health import ReadinessResponse, ServiceCheck, get_system_status_service, router as health_router


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
        "openapi_url": "/openapi.json",
        "health_url": "/health",
        "ready_url": "/ready",
        "version_url": "/version",
    }
    assert head_response.status_code == 200
    assert "/" not in app.openapi()["paths"]


def test_build_versioned_path_skips_root() -> None:
    assert build_versioned_path("/") is None


def test_diagnostics_and_metrics_require_admin_in_production() -> None:
    app = FastAPI()
    app.state.settings = SimpleNamespace(app_name="GTEX API", app_env="production")
    app.dependency_overrides[get_optional_current_user] = lambda: None
    app.include_router(health_router)

    with TestClient(app) as client:
        diagnostics = client.get("/diagnostics")
        metrics = client.get("/metrics")

    assert diagnostics.status_code == 401
    assert metrics.status_code == 401


def test_root_route_hides_docs_links_when_docs_are_disabled() -> None:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = SimpleNamespace(app_name="GTEX API", app_env="production")
    app.include_router(health_router)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs_url"] is None
    assert response.json()["openapi_url"] is None


def test_ready_route_is_mounted_at_root_path() -> None:
    class _ReadyService:
        def build_readiness(self, request, *, check_schema: bool = True) -> ReadinessResponse:
            assert check_schema is True
            return ReadinessResponse(
                status="ready",
                checks={"database": ServiceCheck(status="ok")},
                runtime_mode="normal",
            )

    app = FastAPI()
    app.state.settings = SimpleNamespace(app_name="GTEX API")
    app.dependency_overrides[get_system_status_service] = lambda: _ReadyService()
    app.include_router(health_router)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
