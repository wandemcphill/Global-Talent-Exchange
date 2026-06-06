from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin_godmode.router import router as admin_router
from app.auth.dependencies import get_current_admin, get_session
from app.auth.service import AuthService
from app.models.user import UserRole


def test_scoped_admin_bootstrap_returns_clean_403(tmp_path: Path, gtex_db_session_factory) -> None:
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    SessionLocal = gtex_db_session_factory
    session = SessionLocal()
    scoped_admin = AuthService().ensure_admin_user(
        session,
        email="scoped-admin@example.com",
        password="SuperSecret1",
        username="scoped_admin",
        display_name="Scoped Admin",
        role=UserRole.ADMIN,
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: scoped_admin

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/admin/god-mode/bootstrap")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission view_audit_log is required for this action."

    session.close()
