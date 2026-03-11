from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.router import login_user, register_user
from backend.app.auth.schemas import LoginRequest, RegisterRequest
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
