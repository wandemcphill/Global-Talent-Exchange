from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService
from app.core.config import load_settings
from app.main import _ensure_initial_admin
from app.models.user import User, UserRole


def _session_factory(gtex_db_session_factory: sessionmaker) -> sessionmaker:
    # Shared session-scoped schema (tests/conftest.py::gtex_db_engine) with
    # per-test rollback, instead of rebuilding all ~567 tables per test.
    return gtex_db_session_factory


def test_load_settings_defaults_bootstrap_admin_to_disabled(tmp_path: Path) -> None:
    settings = load_settings(
        environ={
            "GTE_DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'settings.db').as_posix()}",
        },
    )

    assert settings.bootstrap_admin_enabled is False
    assert settings.bootstrap_admin_email is None
    assert settings.bootstrap_admin_password is None
    assert settings.bootstrap_admin_username is None


def test_ensure_initial_admin_is_noop_when_disabled(gtex_db_session_factory) -> None:
    SessionLocal = _session_factory(gtex_db_session_factory)
    settings = SimpleNamespace(
        bootstrap_admin_enabled=False,
        bootstrap_admin_email=None,
        bootstrap_admin_password=None,
        bootstrap_admin_username=None,
        bootstrap_admin_display_name=None,
    )

    _ensure_initial_admin(settings, SessionLocal)

    with SessionLocal() as session:
        users = session.scalars(select(User)).all()
        assert users == []


def test_ensure_initial_admin_creates_super_admin_when_enabled(gtex_db_session_factory) -> None:
    SessionLocal = _session_factory(gtex_db_session_factory)
    settings = SimpleNamespace(
        bootstrap_admin_enabled=True,
        bootstrap_admin_email="bootstrap-admin@example.com",
        bootstrap_admin_password=TEST_PASSWORD,
        bootstrap_admin_username="bootstrap_admin",
        bootstrap_admin_display_name="Bootstrap Admin",
    )

    _ensure_initial_admin(settings, SessionLocal)

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "bootstrap-admin@example.com"))
        assert user is not None
        assert user.role == UserRole.SUPER_ADMIN
        assert user.username == "bootstrap_admin"
        authenticated = AuthService().authenticate_user(
            session,
            email="bootstrap-admin@example.com",
            password=TEST_PASSWORD,
        )
        assert authenticated.id == user.id
