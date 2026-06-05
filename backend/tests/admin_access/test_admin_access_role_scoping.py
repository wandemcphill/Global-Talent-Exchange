from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import pytest

from backend.tests.support.secrets import TEST_PASSWORD
from app.admin_access.router import router as admin_access_router
from app.admin_godmode.service import (
    ADMIN_GODMODE_FILE,
    ADMIN_GODMODE_STATE_KEY,
    ALL_ADMIN_PERMISSIONS,
    AdminGodModeService,
    COMPETITION_OPS_ADMIN_ROLE_NAME,
    DEFAULT_ROLE_PERMISSIONS,
    GOD_MODE_ROLE_NAME,
    REGEN_OPS_ADMIN_ROLE_NAME,
    SCOPED_ADMIN_ROLE_NAME,
)
from app.models.admin_runtime_state import AdminRuntimeState
from app.auth.dependencies import get_current_super_admin, get_session
from app.auth.service import AuthService
from app.models.user import UserRole
from app.wallets.service import WalletService


@pytest.fixture()
def admin_access_context(tmp_path: Path, gtex_db_session_factory):
    SessionLocal = gtex_db_session_factory
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
    app.state.session_factory = SessionLocal

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_super_admin] = lambda: super_admin

    with TestClient(app) as client:
        yield client, session, tmp_path, app, SessionLocal

    session.close()


def _read_db_state(SessionLocal: sessionmaker) -> dict[str, object]:
    with SessionLocal() as session:
        row = session.scalar(select(AdminRuntimeState).where(AdminRuntimeState.state_key == ADMIN_GODMODE_STATE_KEY))
        assert row is not None
        return dict(row.payload_json or {})


def test_create_admin_assigns_scoped_role_without_god_mode_baseline(
    admin_access_context,
) -> None:
    client, session, config_root, _app, SessionLocal = admin_access_context

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
    payload = response.json()
    state = _read_db_state(SessionLocal)
    assignments = state["roles"]["assignments"]
    assert state["roles"]["default_admin_role"] == SCOPED_ADMIN_ROLE_NAME
    assert assignments[0]["role_name"] == SCOPED_ADMIN_ROLE_NAME
    assert assignments[0]["permissions"] == ["manage_commissions"]
    assert payload["admin_role_name"] == SCOPED_ADMIN_ROLE_NAME
    assert payload["assigned_permissions"] == ["manage_commissions"]
    assert payload["permissions"] == ["manage_commissions"]
    assert not (config_root / ADMIN_GODMODE_FILE).exists()

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


def test_permission_catalog_exposes_finance_and_god_mode_controls(admin_access_context) -> None:
    client, *_ = admin_access_context

    response = client.get("/api/admin/access/permissions")

    assert response.status_code == 200, response.text
    permissions = set(response.json()["permissions"])
    assert "manage_payment_rails" in permissions
    assert "manage_treasury_withdrawals" in permissions
    assert "manage_liquidity_desk" in permissions
    assert "manage_regen_universe" in permissions


def test_god_mode_state_prefers_database_when_session_factory_exists(
    tmp_path: Path,
    gtex_db_session_factory,
) -> None:
    SessionLocal = gtex_db_session_factory
    app = FastAPI()
    app.state.settings = SimpleNamespace(config_root=tmp_path)
    app.state.session_factory = SessionLocal

    service = AdminGodModeService(wallet_service=WalletService())
    state = service._load_state(app)

    with SessionLocal() as session:
        row = session.scalar(select(AdminRuntimeState).where(AdminRuntimeState.state_key == ADMIN_GODMODE_STATE_KEY))

    assert state["roles"]["default_admin_role"] == SCOPED_ADMIN_ROLE_NAME
    assert row is not None
    assert not (tmp_path / ADMIN_GODMODE_FILE).exists()


def test_resolve_profile_keeps_super_admin_full_and_plain_admin_scoped(
    admin_access_context,
) -> None:
    _client, session, _config_root, _app, _SessionLocal = admin_access_context
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
    assert sorted(super_profile.permissions) == sorted(ALL_ADMIN_PERMISSIONS)


def test_resolve_profile_short_circuits_runtime_state_for_super_admin(
    admin_access_context,
) -> None:
    _client, session, _config_root, _app, _SessionLocal = admin_access_context
    auth = AuthService()
    super_admin = auth.ensure_admin_user(
        session,
        email="short-circuit-root@example.com",
        password=TEST_PASSWORD,
        username="short_circuit_root",
        display_name="Short Circuit Root",
        role=UserRole.SUPER_ADMIN,
    )
    session.commit()

    class ExplodingState(dict):
        def get(self, *args, **kwargs):  # type: ignore[override]
            raise AssertionError("SUPER_ADMIN resolution should not consult runtime state.")

    profile = AdminGodModeService(wallet_service=WalletService()).resolve_profile(
        super_admin,
        ExplodingState(),
    )

    assert profile.role_name == GOD_MODE_ROLE_NAME
    assert sorted(profile.permissions) == sorted(ALL_ADMIN_PERMISSIONS)


def test_disabled_assignment_resolves_to_no_delegated_permissions(
    admin_access_context,
) -> None:
    _client, session, _config_root, _app, _SessionLocal = admin_access_context
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


def test_create_admin_can_assign_competition_ops_role_and_publish_immediately(
    admin_access_context,
) -> None:
    client, _session, config_root, app, SessionLocal = admin_access_context

    response = client.post(
        "/api/admin/access",
        json={
            "email": "competition-ops@example.com",
            "username": "competition_ops_admin",
            "password": TEST_PASSWORD,
            "display_name": "Competition Ops Admin",
            "role_name": COMPETITION_OPS_ADMIN_ROLE_NAME,
            "permissions": [],
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["admin_role_name"] == COMPETITION_OPS_ADMIN_ROLE_NAME
    assert payload["assigned_permissions"] == []
    assert sorted(payload["permissions"]) == ["manage_competitions", "view_audit_log"]
    assert not (config_root / ADMIN_GODMODE_FILE).exists()

    state = _read_db_state(SessionLocal)
    assignments = state["roles"]["assignments"]
    assert assignments[0]["role_name"] == COMPETITION_OPS_ADMIN_ROLE_NAME

    with SessionLocal() as session:
        admin = AuthService().authenticate_user(
            session,
            email="competition-ops@example.com",
            password=TEST_PASSWORD,
        )
        profile = AdminGodModeService(wallet_service=WalletService()).resolve_profile(admin, state)

    assert sorted(profile.permissions) == ["manage_competitions", "view_audit_log"]


def test_competition_ops_assignment_persists_across_runtime_reload(
    admin_access_context,
) -> None:
    client, _session, config_root, _app, SessionLocal = admin_access_context

    create_response = client.post(
        "/api/admin/access",
        json={
            "email": "competition-restart@example.com",
            "username": "competition_restart",
            "password": TEST_PASSWORD,
            "display_name": "Competition Restart Admin",
            "role_name": COMPETITION_OPS_ADMIN_ROLE_NAME,
            "permissions": [],
        },
    )
    assert create_response.status_code == 201, create_response.text
    assert not (config_root / ADMIN_GODMODE_FILE).exists()

    reloaded_app = FastAPI()
    reloaded_app.state.settings = SimpleNamespace(config_root=config_root)
    reloaded_app.state.session_factory = SessionLocal
    service = AdminGodModeService(wallet_service=WalletService())
    state = service._load_state(reloaded_app)

    with SessionLocal() as session:
        admin = AuthService().authenticate_user(
            session,
            email="competition-restart@example.com",
            password=TEST_PASSWORD,
        )
        profile = service.resolve_profile(admin, state)

    assert sorted(profile.permissions) == ["manage_competitions", "view_audit_log"]


def test_create_admin_can_assign_regen_ops_role_and_seed_regen_permissions(
    admin_access_context,
) -> None:
    client, _session, config_root, _app, SessionLocal = admin_access_context

    response = client.post(
        "/api/admin/access",
        json={
            "email": "regen-ops@example.com",
            "username": "regen_ops_admin",
            "password": TEST_PASSWORD,
            "display_name": "Regen Ops Admin",
            "role_name": REGEN_OPS_ADMIN_ROLE_NAME,
            "permissions": [],
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["admin_role_name"] == REGEN_OPS_ADMIN_ROLE_NAME
    assert payload["assigned_permissions"] == []
    assert sorted(payload["permissions"]) == [
        "manage_national_regens",
        "manage_regen_awards",
        "manage_regen_generation",
        "manage_regen_universe",
        "view_audit_log",
    ]
    assert not (config_root / ADMIN_GODMODE_FILE).exists()

    state = _read_db_state(SessionLocal)
    assignments = state["roles"]["assignments"]
    assert assignments[0]["role_name"] == REGEN_OPS_ADMIN_ROLE_NAME

    with SessionLocal() as session:
        admin = AuthService().authenticate_user(
            session,
            email="regen-ops@example.com",
            password=TEST_PASSWORD,
        )
        profile = AdminGodModeService(wallet_service=WalletService()).resolve_profile(admin, state)

    assert sorted(profile.permissions) == [
        "manage_national_regens",
        "manage_regen_awards",
        "manage_regen_generation",
        "manage_regen_universe",
        "view_audit_log",
    ]
