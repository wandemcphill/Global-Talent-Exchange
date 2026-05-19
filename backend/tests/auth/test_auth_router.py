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
from app.auth.router import login_user, register_user, signup_user
from app.auth.security import decode_access_token, decode_refresh_token
from app.auth.schemas import LoginRequest, RegisterRequest, UserClubSignupRequest
from app.auth.service import AuthService
from app.main import create_app
from app.models import Base, ClubProfile, CreatorProfile
from app.models.club_profile import ClubType
from app.models.user import User, UserRole
from app.trader.service import _totp
from app.users.router import read_current_user
from backend.tests.support.signup_payloads import creator_signup_payload, trader_signup_payload, user_signup_payload

TEST_PASSWORD = "SuperSecret1"  # pragma: allowlist secret
WRONG_PASSWORD = "WrongPassword1"  # pragma: allowlist secret


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
            user = session.scalar(select(User).where(User.email == os.environ["GTE_BOOTSTRAP_ADMIN_EMAIL"]))
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
            password=TEST_PASSWORD,
            display_name="Fan User",
        )
        service.create_explicit_club_profile(
            session,
            user,
            club_name="Fan User Sporting",
            short_name="FAN",
            club_type=ClubType.COMMUNITY,
            country_code="NG",
            region_name="Test State",
            city_name="Test City",
            crest_asset_ref=None,
            primary_color="#0F766E",
            secondary_color="#F8FAFC",
        )
        issued_session = service.issue_session_tokens(user, session=session)
        session.commit()
        session.refresh(user)
        return user.id, issued_session.access_token, issued_session.refresh_token


def _signup_user_direct(
    session,
    *,
    email: str,
    username: str,
    full_name: str = "Fan User",
):
    return signup_user(
        UserClubSignupRequest(
            **user_signup_payload(
                email=email,
                username=username,
                full_name=full_name,
                password=TEST_PASSWORD,
            )
        ),
        session,
    )


def _current_totp(secret: str) -> str:
    return _totp(secret, int(time.time()) // 30)


def test_register_login_and_me_flow(session) -> None:
    register_response = _signup_user_direct(
        session,
        email="fan@example.com",
        username="fanuser",
    )
    current_user = session.get(User, register_response.user.id)

    me_response = read_current_user(current_user=current_user)
    login_response = login_user(
        LoginRequest(email="fan@example.com", password=TEST_PASSWORD),
        session,
    )
    register_claims = decode_access_token(register_response.access_token)
    login_claims = decode_access_token(login_response.access_token)
    register_refresh_claims = decode_refresh_token(register_response.refresh_token)
    login_refresh_claims = decode_refresh_token(login_response.refresh_token)

    assert register_response.user.email == "fan@example.com"
    assert register_response.session_id
    assert register_claims["sid"] == register_response.session_id
    assert register_refresh_claims["sid"] == register_response.session_id
    assert register_response.refresh_token
    assert register_response.refresh_expires_in == 2592000
    assert me_response.id == register_response.user.id
    assert login_response.user.id == register_response.user.id
    assert login_response.session_id
    assert login_claims["sid"] == login_response.session_id
    assert login_refresh_claims["sid"] == login_response.session_id
    assert login_response.refresh_token
    assert login_response.refresh_expires_in == 2592000


def test_duplicate_registration_returns_conflict(session) -> None:
    _signup_user_direct(
        session,
        email="fan@example.com",
        username="fanuser",
    )

    with pytest.raises(HTTPException) as exc_info:
        _signup_user_direct(
            session,
            email="fan@example.com",
            username="fanuser2",
        )

    assert exc_info.value.status_code == 409


def test_login_with_invalid_credentials_returns_unauthorized(session) -> None:
    AuthService().register_user(
        session,
        email="fan@example.com",
        username="fanuser",
        password=TEST_PASSWORD,
        full_name="Fan User",
        region_code="NG",
    )

    with pytest.raises(HTTPException) as exc_info:
        login_user(
            LoginRequest(email="fan@example.com", password=WRONG_PASSWORD),
            session,
        )

    assert exc_info.value.status_code == 401


def test_public_register_route_is_gone(app_client) -> None:
    _app, client = app_client

    for path in ("/auth/register", "/api/auth/register", "/api/v2/auth/register"):
        register_response = client.post(
            path,
            json={
                "email": "noregion@example.com",
                "full_name": "No Region",
                "phone_number": "08000000000",
                "password": TEST_PASSWORD,
                "is_over_18": True,
            },
        )

        assert register_response.status_code == 410, register_response.text


def test_api_auth_me_returns_authenticated_user(app_client) -> None:
    app, client = app_client
    user_id, token, _refresh_token = _create_authenticated_user(app)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == user_id
    assert payload["email"] == "fan@example.com"
    assert payload["username"] == "fanuser"
    assert payload["display_name"] == "Fan User"
    assert payload["region_code"] == "GLOBAL"
    assert payload["role"] == "club"
    assert payload["active_organization_id"]
    assert payload["active_organization_type"] == "club"
    assert len(payload["memberships"]) == 1
    assert payload["permissions"] == [
        "players.view",
        "pipeline.manage",
        "contact.manage",
    ]


def test_api_auth_me_patch_updates_allowed_profile_fields(app_client) -> None:
    app, client = app_client
    user_id, token, _refresh_token = _create_authenticated_user(app)

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
    payload = response.json()
    assert payload["id"] == user_id
    assert payload["display_name"] == "Updated Fan"
    assert payload["avatar_url"] == "https://cdn.example.com/avatar.png"
    assert payload["favourite_club"] == "Arsenal"
    assert payload["nationality"] == "Nigeria"
    assert payload["preferred_position"] == "Forward"
    assert payload["role"] == "club"
    assert payload["active_organization_id"]
    assert payload["active_organization_type"] == "club"
    assert len(payload["memberships"]) == 1


def test_api_auth_me_patch_validation_rejects_invalid_avatar_url(app_client) -> None:
    app, client = app_client
    _user_id, token, _refresh_token = _create_authenticated_user(app)

    response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"avatar_url": "not-a-url"},
    )

    assert response.status_code == 422
    assert "avatar_url" in response.text


def test_api_auth_me_patch_rejects_protected_fields(app_client) -> None:
    app, client = app_client
    _user_id, token, _refresh_token = _create_authenticated_user(app)

    response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "owner@example.com"},
    )

    assert response.status_code == 422
    assert "Protected fields cannot be updated" in response.text


def test_refresh_logout_and_session_bootstrap_flow(app_client) -> None:
    _app, client = app_client
    login_response = client.post(
        "/auth/signup/user",
        json=user_signup_payload(
            email="bootstrap@example.com",
            username="bootstrapuser",
            full_name="Bootstrap User",
            password=TEST_PASSWORD,
        ),
    )

    assert login_response.status_code == 201, login_response.text
    issued = login_response.json()
    refresh_response = client.post(
        "/api/v2/auth/refresh",
        json={"refresh_token": issued["refresh_token"]},
        headers={"X-API-Version": "2", "X-Device-Id": "pytest-device"},
    )

    assert refresh_response.status_code == 200, refresh_response.text
    refreshed = refresh_response.json()["data"]
    assert refreshed["session_id"] == issued["session_id"]
    assert refreshed["access_token"] != issued["access_token"]
    assert refreshed["refresh_token"] != issued["refresh_token"]

    bootstrap_response = client.get(
        "/api/v2/session/bootstrap",
        headers={
            "X-API-Version": "2",
            "Authorization": f"Bearer {refreshed['access_token']}",
            "X-User-Id": refreshed["user"]["id"],
            "X-Session-Id": refreshed["session_id"],
            "X-Device-Id": "pytest-device",
        },
    )

    assert bootstrap_response.status_code == 200, bootstrap_response.text
    bootstrap = bootstrap_response.json()["data"]
    assert bootstrap["user"]["id"] == refreshed["user"]["id"]
    assert bootstrap["club"]["owner_user_id"] == refreshed["user"]["id"]
    assert bootstrap["wallet"]["currency"] in {"credit", "coin"}
    assert bootstrap["compliance"]["country_code"] == "NG"
    assert "players.view" in bootstrap["permissions"]

    logout_response = client.post(
        "/api/v2/auth/logout",
        headers={
            "X-API-Version": "2",
            "Authorization": f"Bearer {refreshed['access_token']}",
            "X-User-Id": refreshed["user"]["id"],
            "X-Session-Id": refreshed["session_id"],
            "X-Device-Id": "pytest-device",
        },
    )
    assert logout_response.status_code == 200, logout_response.text

    revoked_bootstrap = client.get(
        "/api/v2/session/bootstrap",
        headers={
            "X-API-Version": "2",
            "Authorization": f"Bearer {refreshed['access_token']}",
            "X-User-Id": refreshed["user"]["id"],
            "X-Session-Id": refreshed["session_id"],
            "X-Device-Id": "pytest-device",
        },
    )
    assert revoked_bootstrap.status_code == 401


def test_user_creator_and_trader_signup_sessions_include_public_account_type(app_client) -> None:
    app, client = app_client
    trader_secret = "JBSWY3DPEHPK3PXP"
    signups = [
        (
            "/auth/signup/user",
            user_signup_payload(
                email="account-type-user@example.com",
                username="account_type_user",
                full_name="Account Type User",
                password=TEST_PASSWORD,
            ),
            "user",
        ),
        (
            "/auth/signup/creator",
            creator_signup_payload(
                email="account-type-creator@example.com",
                username="account_type_creator",
                creator_name="Account Type Creator",
                password=TEST_PASSWORD,
            ),
            "creator",
        ),
        (
            "/auth/signup/trader",
            trader_signup_payload(
                email="account-type-trader@example.com",
                trading_alias="account_type_trader",
                full_name="Account Type Trader",
                password=TEST_PASSWORD,
                totp_secret=trader_secret,
                totp_code=_current_totp(trader_secret),
            ),
            "coin_trader",
        ),
    ]

    for path, payload, expected_account_type in signups:
        response = client.post(path, json=payload)
        assert response.status_code == 201, response.text
        issued = response.json()
        assert issued["user"]["account_type"] == expected_account_type
        assert decode_access_token(issued["access_token"])["account_type"] == expected_account_type

    with app.state.session_factory() as session:
        creator = session.scalar(select(User).where(User.email == "account-type-creator@example.com"))
        assert creator is not None
        assert session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == creator.id)) is not None
        assert session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == creator.id)) is None


def test_public_signup_rejects_external_admin_account_type(app_client) -> None:
    _app, client = app_client
    payload = user_signup_payload(
        email="external-admin@example.com",
        username="external_admin",
        full_name="External Admin",
        password=TEST_PASSWORD,
    )
    payload["account_type"] = "admin"

    response = client.post("/auth/signup/user", json=payload)

    assert response.status_code == 422, response.text
    assert "account_type" in response.text


def test_trader_signup_requires_proof_of_address(app_client) -> None:
    _app, client = app_client
    secret = "JBSWY3DPEHPK3PXP"
    payload = trader_signup_payload(
        email="missing-address-trader@example.com",
        trading_alias="missing_address_trader",
        full_name="Missing Address Trader",
        password=TEST_PASSWORD,
        totp_secret=secret,
        totp_code=_current_totp(secret),
    )
    payload["compliance"].pop("proof_of_address_attachment_id")

    response = client.post("/auth/signup/trader", json=payload)

    assert response.status_code == 422, response.text
    assert "proof_of_address_attachment_id" in response.text


def test_legacy_register_function_returns_gone(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        register_user(
            RegisterRequest(
                email="telemetry-register@example.com",
                username="telemetryregister",
                password=TEST_PASSWORD,
                full_name="Telemetry Register",
                region_code="NG",
            ),
            session,
        )

    assert exc_info.value.status_code == 410


def test_login_user_logs_completion(session, caplog: pytest.LogCaptureFixture) -> None:
    AuthService().register_user(
        session,
        email="telemetry-login@example.com",
        username="telemetrylogin",
        password=TEST_PASSWORD,
        full_name="Telemetry Login",
        region_code="NG",
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = login_user(
            LoginRequest(email="telemetry-login@example.com", password=TEST_PASSWORD),
            session,
        )

    assert response.user.email == "telemetry-login@example.com"
    assert any("auth.request.route_entry flow=login" in message for message in caplog.messages)
    assert any("auth.request.completed flow=login status_code=200" in message for message in caplog.messages)
    assert any("auth.create_access_token_ms" in message for message in caplog.messages)
    assert any("service.authenticate_user_ms" in message for message in caplog.messages)


def test_login_user_logs_failure_with_rollback(session, caplog: pytest.LogCaptureFixture) -> None:
    AuthService().register_user(
        session,
        email="telemetry-login-failure@example.com",
        username="telemetryloginfailure",
        password=TEST_PASSWORD,
        full_name="Telemetry Login Failure",
        region_code="NG",
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        with pytest.raises(HTTPException) as exc_info:
            login_user(
                LoginRequest(
                    email="telemetry-login-failure@example.com",
                    password=WRONG_PASSWORD,
                ),
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
    scoped_password = TEST_PASSWORD
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
    assert "manage_manager_catalog" in payload["permissions"]
    assert payload["landing_route"] == "/profile/admin"

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert "manage_manager_catalog" in me_response.json()["permissions"]
