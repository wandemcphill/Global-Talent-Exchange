from __future__ import annotations

from types import SimpleNamespace
from typing import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_optional_current_user, get_session
from app.observability.router import router as observability_router


def _empty_session() -> Iterator[None]:
    yield None


def test_observability_config_snapshot_requires_admin_in_production() -> None:
    app = FastAPI()
    app.state.settings = SimpleNamespace(app_env="production")
    app.dependency_overrides[get_optional_current_user] = lambda: None
    app.dependency_overrides[get_session] = _empty_session
    app.include_router(observability_router)

    with TestClient(app) as client:
        response = client.get("/observability/config")

    assert response.status_code == 401
    assert response.json() == {"detail": "Admin authentication is required."}
