from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.tests.support.secrets import TEST_PASSWORD
import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
from app.admin_access.router import router as admin_access_router
from app.admin_godmode.service import (
    ADMIN_GODMODE_FILE,
    ADMIN_GODMODE_STATE_KEY,
    AdminGodModeService,
    DEFAULT_ROLE_PERMISSIONS,
    GOD_MODE_ROLE_NAME,
    SCOPED_ADMIN_ROLE_NAME,
    SUPER_ADMIN_EXTRA_PERMISSIONS,
)
from app.models.admin_runtime_state import AdminRuntimeState
from app.auth.dependencies import get_current_super_admin, get_session
from app.auth.service import AuthService
from app.models.base import Base
from app.models.user import UserRole
from app.wallets.service import WalletService


@pytest.fixture()
def admin_access_context(tmp_path: Path):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    auth = AuthService()
    super_admin = auth.ensure_admin_user(
        session,
        email="root-admin@example.com",
        password=TEST_PASSWORD,
        username="root_admin",
        display_name="Root Admin",
        role=UserRole.SUPER_ADMIN,
    )
    session.commit()

    app = FastAPI()
    app.include_router(admin_access_router)
    app.state.settings = SimpleNamespace(config_root=tmp_path)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_super_admin] = lambda: super_admin

    with TestClient(app) as client:
        yield client, session, tmp_path

    session.close()


def _read_state(config_root: Path) -> dict[str, object]:
    path = config_root / ADMIN_GODMODE_FILE
    return json.loads(path.read_text(encoding="utf-8"))


def test_create_admin_assigns_scoped_role_without_god_mode_baseline(
    admin_access_context,
) -> None:
    client, session, config_root = admin_access_context

    response = client.post(
        "/api/admin/access",
        json={
            "email": "scoped-admin@example.com",
            "username": "scoped_admin",
            "password": TEST_PASSWORD,
            "display_name": "Scoped Admin",
            "permissions": ["manage_commissions"],
        },
    )

    assert response.status_code == 201, response.text
    state = _read_state(config_root)
    assignments = state["roles"]["assignments"]
    assert state["roles"]["default_admin_role"] == SCOPED_ADMIN_ROLE_NAME
    assert assignments[0]["role_name"] == SCOPED_ADMIN_ROLE_NAME
    assert assignments[0]["permissions"] == ["manage_commissions"]

    admin = AuthService().authenticate_user(
        session,
        email="scoped-admin@example.com",
        password=TEST_PASSWORD,
    )
    profile = AdminGodModeService(wallet_service=WalletService()).resolve_profile(
        admin,
        state,
    )
    assert profile.role_name == SCOPED_ADMIN_ROLE_NAME
    assert profile.permissions == ["manage_commissions"]
    assert "manage_payment_rails" not in profile.permissions
    assert "view_audit_log" not in profile.permissions


def test_god_mode_state_prefers_database_when_session_factory_exists(tmp_path: Path) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

    service = AdminGodModeService(wallet_service=WalletService())
    state = service._load_state(app)

    with SessionLocal() as session:
        row = session.scalar(
            select(AdminRuntimeState).where(
                AdminRuntimeState.state_key == ADMIN_GODMODE_STATE_KEY
            )
        )

    assert state["roles"]["default_admin_role"] == SCOPED_ADMIN_ROLE_NAME
    assert row is not None
    assert not (tmp_path / ADMIN_GODMODE_FILE).exists()


def test_resolve_profile_keeps_super_admin_full_and_plain_admin_scoped(
    admin_access_context,
) -> None:
    _client, session, _config_root = admin_access_context
    auth = AuthService()
    plain_admin = auth.ensure_admin_user(
        session,
        email="plain-admin@example.com",
        password=TEST_PASSWORD,
        username="plain_admin",
        display_name="Plain Admin",
        role=UserRole.ADMIN,
    )
    super_admin = auth.ensure_admin_user(
        session,
        email="another-root@example.com",
        password=TEST_PASSWORD,
        username="another_root",
        display_name="Another Root",
        role=UserRole.SUPER_ADMIN,
    )
    session.commit()

    state = {
        "roles": {
            "default_admin_role": GOD_MODE_ROLE_NAME,
            "available_roles": DEFAULT_ROLE_PERMISSIONS,
            "assignments": [],
        }
    }
    service = AdminGodModeService(wallet_service=WalletService())

    plain_profile = service.resolve_profile(plain_admin, state)
    super_profile = service.resolve_profile(super_admin, state)

    assert plain_profile.role_name == SCOPED_ADMIN_ROLE_NAME
    assert plain_profile.permissions == []
    assert super_profile.role_name == GOD_MODE_ROLE_NAME
    assert sorted(super_profile.permissions) == sorted(
        [
            *DEFAULT_ROLE_PERMISSIONS[GOD_MODE_ROLE_NAME],
            *SUPER_ADMIN_EXTRA_PERMISSIONS,
        ]
    )


def test_disabled_assignment_resolves_to_no_delegated_permissions(
    admin_access_context,
) -> None:
    _client, session, _config_root = admin_access_context
    auth = AuthService()
    scoped_admin = auth.ensure_admin_user(
        session,
        email="disabled-admin@example.com",
        password=TEST_PASSWORD,
        username="disabled_admin",
        display_name="Disabled Admin",
        role=UserRole.ADMIN,
    )
    session.commit()

    state = {
        "roles": {
            "default_admin_role": SCOPED_ADMIN_ROLE_NAME,
            "available_roles": DEFAULT_ROLE_PERMISSIONS,
            "assignments": [
                {
                    "subject_key": scoped_admin.email.lower(),
                    "role_name": "support_admin",
                    "permissions": ["manage_commissions"],
                    "is_enabled": False,
                }
            ],
        }
    }
    profile = AdminGodModeService(wallet_service=WalletService()).resolve_profile(
        scoped_admin,
        state,
    )

    assert profile.role_name == "support_admin"
    assert profile.permissions == []
