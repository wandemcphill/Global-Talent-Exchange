from __future__ import annotations

import logging
import os
import shutil
import time

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import BACKEND_ROOT, load_settings
from app.core.database import load_model_modules
from app.auth.router import login_user, register_user
from app.auth.security import decode_access_token
from app.auth.schemas import LoginRequest, RegisterRequest
from app.auth.service import AuthService
from app.main import create_app
from app.models import Base
from app.models.user import User, UserRole
from app.users.router import read_current_user


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'auth_router.db').as_posix()}"
    media_root = tmp_path / "media"
    config_root = tmp_path / "config"
    shutil.copytree(BACKEND_ROOT / "config", config_root)
    settings = load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
            "GTE_DATABASE_READ_URL": database_url,
            "GTE_MEDIA_STORAGE_ROOT": str(media_root),
            "GTE_CONFIG_DIR": str(config_root),
        }
    )
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    load_model_modules()
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for ddl in (
            "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(2048)",
            "ALTER TABLE users ADD COLUMN favourite_club VARCHAR(160)",
            "ALTER TABLE users ADD COLUMN nationality VARCHAR(160)",
            "ALTER TABLE users ADD COLUMN preferred_position VARCHAR(120)",
        ):
            try:
                connection.exec_driver_sql(ddl)
            except Exception:
                pass
    app = create_app(settings=settings, engine=engine, run_migration_check=False)
    with TestClient(app) as client:
        yield app, client


def _bootstrap_admin_login(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/auth/login",
        json={
            "email": os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"],
            "password": os.environ["GTE_BOOTSTRAP_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _ensure_bootstrap_admin(app, *, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with app.state.session_factory() as session:
            user = session.scalar(
                select(User).where(User.email == os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"])
            )
            if user is not None and user.role == UserRole.SUPER_ADMIN:
                return
        time.sleep(0.25)
    raise AssertionError("Bootstrap admin was not created before timeout.")


def _create_authenticated_user(app):
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email="fan@example.com",
            username="fanuser",
            password="SuperSecret1",
            display_name="Fan User",
        )
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
        session.refresh(user)
        return user.id, token


def test_register_login_and_me_flow(session) -> None:
    register_response = register_user(
        RegisterRequest(
            email="fan@example.com",
            username="fanuser",
            password="SuperSecret1",
            full_name="Fan User",
            region_code="NG",
        ),
        session,
    )
    current_user = session.get(User, register_response.user.id)

    me_response = read_current_user(current_user=current_user)
    login_response = login_user(LoginRequest(email="fan@example.com", password="SuperSecret1"), session)
    register_claims = decode_access_token(register_response.access_token)
    login_claims = decode_access_token(login_response.access_token)

    assert register_response.user.email == "fan@example.com"
    assert register_response.session_id
    assert register_claims["sid"] == register_response.session_id
    assert me_response.id == register_response.user.id
    assert login_response.user.id == register_response.user.id
    assert login_response.session_id
    assert login_claims["sid"] == login_response.session_id


def test_duplicate_registration_returns_conflict(session) -> None:
    payload = RegisterRequest(email="fan@example.com", username="fanuser", password="SuperSecret1", region_code="NG")
    register_user(payload, session)

    with pytest.raises(HTTPException) as exc_info:
        register_user(
            RegisterRequest(email="fan@example.com", username="fanuser2", password="SuperSecret1", region_code="NG"),
            session,
        )

    assert exc_info.value.status_code == 409


def test_login_with_invalid_credentials_returns_unauthorized(session) -> None:
    register_user(
        RegisterRequest(
            email="fan@example.com",
            username="fanuser",
            password="SuperSecret1",
            full_name="Fan User",
            region_code="NG",
        ),
        session,
    )

    with pytest.raises(HTTPException) as exc_info:
        login_user(
            LoginRequest(email="fan@example.com", password="WrongPassword1"),
            session,
        )

    assert exc_info.value.status_code == 401


def test_register_without_region_code_defaults_to_global(app_client) -> None:
    _app, client = app_client

    register_response = client.post(
        "/auth/register",
        json={
            "email": "noregion@example.com",
            "full_name": "No Region",
            "phone_number": "08000000000",
            "password": "SuperSecret1",
            "is_over_18": True,
        },
    )

    assert register_response.status_code == 201, register_response.text

    access_token = register_response.json()["access_token"]
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["region_code"] == "GLOBAL"


def test_api_auth_me_returns_authenticated_user(app_client) -> None:
    app, client = app_client
    user_id, token = _create_authenticated_user(app)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user_id,
        "email": "fan@example.com",
        "username": "fanuser",
        "full_name": "Fan User",
        "phone_number": "0000000000",
        "age_confirmed_at": response.json()["age_confirmed_at"],
        "display_name": "Fan User",
        "avatar_url": None,
        "favourite_club": None,
        "nationality": None,
        "preferred_position": None,
        "region_code": "GLOBAL",
        "role": "user",
        "kyc_status": "unverified",
        "is_active": True,
        "created_at": response.json()["created_at"],
        "last_login_at": None,
        "active_organization_id": None,
        "active_organization_name": None,
        "active_organization_type": None,
        "memberships": [],
        "permissions": [],
    }


def test_api_auth_me_patch_updates_allowed_profile_fields(app_client) -> None:
    app, client = app_client
    user_id, token = _create_authenticated_user(app)

    response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "display_name": "Updated Fan",
            "avatar_url": "https://cdn.example.com/avatar.png",
            "favourite_club": "Arsenal",
            "nationality": "Nigeria",
            "preferred_position": "Forward",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": user_id,
        "email": "fan@example.com",
        "username": "fanuser",
        "full_name": "Fan User",
        "phone_number": "0000000000",
        "age_confirmed_at": response.json()["age_confirmed_at"],
        "display_name": "Updated Fan",
        "avatar_url": "https://cdn.example.com/avatar.png",
        "favourite_club": "Arsenal",
        "nationality": "Nigeria",
        "preferred_position": "Forward",
        "region_code": "GLOBAL",
        "role": "user",
        "kyc_status": "unverified",
        "is_active": True,
        "created_at": response.json()["created_at"],
        "last_login_at": None,
        "active_organization_id": None,
        "active_organization_name": None,
        "active_organization_type": None,
        "memberships": [],
        "permissions": [],
    }


def test_api_auth_me_patch_validation_rejects_invalid_avatar_url(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)

    response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"avatar_url": "not-a-url"},
    )

    assert response.status_code == 422
    assert "avatar_url" in response.text


def test_api_auth_me_patch_rejects_protected_fields(app_client) -> None:
    app, client = app_client
    _user_id, token = _create_authenticated_user(app)

    response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "owner@example.com"},
    )

    assert response.status_code == 422
    assert "Protected fields cannot be updated" in response.text


def test_register_user_logs_completion(session, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        response = register_user(
            RegisterRequest(
                email="telemetry-register@example.com",
                username="telemetryregister",
                password="SuperSecret1",
                full_name="Telemetry Register",
                region_code="NG",
            ),
            session,
        )

    assert response.user.email == "telemetry-register@example.com"
    assert any("auth.request.route_entry flow=register" in message for message in caplog.messages)
    assert any("auth.request.completed flow=register status_code=201" in message for message in caplog.messages)
    assert any("auth.create_access_token_ms" in message for message in caplog.messages)
    assert any("db.commit_ms" in message for message in caplog.messages)


def test_login_user_logs_completion(session, caplog: pytest.LogCaptureFixture) -> None:
    register_user(
        RegisterRequest(
            email="telemetry-login@example.com",
            username="telemetrylogin",
            password="SuperSecret1",
            full_name="Telemetry Login",
            region_code="NG",
        ),
        session,
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = login_user(
            LoginRequest(email="telemetry-login@example.com", password="SuperSecret1"),
            session,
        )

    assert response.user.email == "telemetry-login@example.com"
    assert any("auth.request.route_entry flow=login" in message for message in caplog.messages)
    assert any("auth.request.completed flow=login status_code=200" in message for message in caplog.messages)
    assert any("auth.create_access_token_ms" in message for message in caplog.messages)
    assert any("service.authenticate_user_ms" in message for message in caplog.messages)


def test_login_user_logs_failure_with_rollback(session, caplog: pytest.LogCaptureFixture) -> None:
    register_user(
        RegisterRequest(
            email="telemetry-login-failure@example.com",
            username="telemetryloginfailure",
            password="SuperSecret1",
            full_name="Telemetry Login Failure",
            region_code="NG",
        ),
        session,
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        with pytest.raises(HTTPException) as exc_info:
            login_user(
                LoginRequest(email="telemetry-login-failure@example.com", password="WrongPassword1"),
                session,
            )

    assert exc_info.value.status_code == 401
    assert any("auth.request.route_entry flow=login" in message for message in caplog.messages)
    assert any("auth.request.failed flow=login status_code=401" in message for message in caplog.messages)
    assert any("db.rollback_ms" in message for message in caplog.messages)


def test_super_admin_login_includes_catalog_permissions_and_god_mode_route(app_client) -> None:
    app, client = app_client
    _ensure_bootstrap_admin(app)

    payload = _bootstrap_admin_login(client)

    assert "manage_manager_catalog" in payload["permissions"]
    assert payload["landing_route"] == "/profile/admin/god-mode"


def test_scoped_admin_login_reflects_delegated_permissions_and_admin_route(app_client) -> None:
    app, client = app_client
    _ensure_bootstrap_admin(app)

    super_payload = _bootstrap_admin_login(client)
    super_headers = {"Authorization": f"Bearer {super_payload['access_token']}"}
    scoped_email = "scoped-auth-router@example.com"
    scoped_password = "SuperSecret1"
    create_response = client.post(
        "/api/admin/access",
        headers=super_headers,
        json={
            "email": scoped_email,
            "username": "scoped_auth_router",
            "password": scoped_password,
            "display_name": "Scoped Auth Router",
            "permissions": ["manage_manager_catalog"],
        },
    )
    assert create_response.status_code == 201, create_response.text

    login_response = client.post(
        "/auth/login",
        json={"email": scoped_email, "password": scoped_password},
    )

    assert login_response.status_code == 200, login_response.text
    payload = login_response.json()
    assert payload["permissions"] == ["manage_manager_catalog"]
    assert payload["landing_route"] == "/profile/admin"

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["permissions"] == ["manage_manager_catalog"]
