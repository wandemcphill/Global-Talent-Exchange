from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.admin_godmode.router import router as admin_router
from app.auth.dependencies import get_current_admin, get_session
from app.auth.service import AuthService
from app.models.base import Base
from app.models.user import UserRole


def test_scoped_admin_bootstrap_returns_clean_403(tmp_path: Path) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
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
    engine.dispose()
