from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.router import login_user, register_user
from backend.app.auth.schemas import LoginRequest, RegisterRequest
from backend.app.auth.service import AuthService
from backend.app.main import create_app
from backend.app.models import Base
from backend.app.models.user import User
from backend.app.users.router import read_current_user


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
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        yield app, client


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
        token, _ = service.issue_access_token(user)
        session.commit()
        session.refresh(user)
        return user.id, token


def test_register_login_and_me_flow(session) -> None:
    register_response = register_user(
        RegisterRequest(
            email="fan@example.com",
            username="fanuser",
            password="SuperSecret1",
            display_name="Fan User",
        ),
        session,
    )
    current_user = session.get(User, register_response.user.id)

    me_response = read_current_user(current_user=current_user)
    login_response = login_user(LoginRequest(email="fan@example.com", password="SuperSecret1"), session)

    assert register_response.user.email == "fan@example.com"
    assert me_response.id == register_response.user.id
    assert login_response.user.id == register_response.user.id


def test_duplicate_registration_returns_conflict(session) -> None:
    payload = RegisterRequest(email="fan@example.com", username="fanuser", password="SuperSecret1")
    register_user(payload, session)

    with pytest.raises(HTTPException) as exc_info:
        register_user(
            RegisterRequest(email="fan@example.com", username="fanuser2", password="SuperSecret1"),
            session,
        )

    assert exc_info.value.status_code == 409


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
        "display_name": "Fan User",
        "avatar_url": None,
        "favourite_club": None,
        "nationality": None,
        "preferred_position": None,
        "role": "user",
        "kyc_status": "unverified",
        "is_active": True,
        "created_at": response.json()["created_at"],
        "last_login_at": None,
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
        "display_name": "Updated Fan",
        "avatar_url": "https://cdn.example.com/avatar.png",
        "favourite_club": "Arsenal",
        "nationality": "Nigeria",
        "preferred_position": "Forward",
        "role": "user",
        "kyc_status": "unverified",
        "is_active": True,
        "created_at": response.json()["created_at"],
        "last_login_at": None,
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
