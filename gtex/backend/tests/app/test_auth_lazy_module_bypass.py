from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules import LazyModuleMiddleware, _should_bypass_lazy_hydration


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.state.modules_hydrated = False
    app.add_middleware(LazyModuleMiddleware)

    @app.post("/auth/login")
    def login():
        return {"ok": True}

    @app.get("/api/auth/me")
    def read_me():
        return {"ok": True}

    @app.get("/api/v2/session/bootstrap")
    def session_bootstrap():
        return {"ok": True}

    @app.get("/competitions")
    def list_competitions():
        return {"ok": True}

    return app


def test_auth_paths_are_marked_for_lazy_hydration_bypass() -> None:
    assert _should_bypass_lazy_hydration("/auth/login") is True
    assert _should_bypass_lazy_hydration("/api/auth/me") is True
    assert _should_bypass_lazy_hydration("/api/v2/auth/me") is True
    assert _should_bypass_lazy_hydration("/api/v2/session/bootstrap") is True
    assert _should_bypass_lazy_hydration("/api/competitions") is True
    assert _should_bypass_lazy_hydration("/api/v2/competitions") is True
    assert _should_bypass_lazy_hydration("/api/v2/match-viewer/live") is True


def test_lazy_module_middleware_skips_hydration_for_auth_paths(monkeypatch) -> None:
    app = _build_test_app()
    hydration_calls: list[FastAPI] = []

    def fake_ensure_modules_loaded(target_app: FastAPI) -> None:
        hydration_calls.append(target_app)

    monkeypatch.setattr("app.modules.ensure_modules_loaded", fake_ensure_modules_loaded)

    with TestClient(app) as client:
        login_response = client.post("/auth/login")
        me_response = client.get("/api/auth/me")
        bootstrap_response = client.get("/api/v2/session/bootstrap")

    assert login_response.status_code == 200
    assert me_response.status_code == 200
    assert bootstrap_response.status_code == 200
    assert hydration_calls == []


def test_lazy_module_middleware_hydrates_for_non_auth_paths(monkeypatch) -> None:
    app = _build_test_app()
    hydration_calls: list[FastAPI] = []

    def fake_ensure_modules_loaded(target_app: FastAPI) -> None:
        hydration_calls.append(target_app)
        target_app.state.modules_hydrated = True

    monkeypatch.setattr("app.modules.ensure_modules_loaded", fake_ensure_modules_loaded)

    with TestClient(app) as client:
        response = client.get("/competitions")

    assert response.status_code == 200
    assert hydration_calls == [app]
