from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.models.base import Base
from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.routes.creators import router as creators_router
from backend.app.routes.referrals import router as referrals_router


@dataclass(frozen=True, slots=True)
class StubUser:
    id: str
    username: str
    display_name: str
    email: str


@pytest.fixture()
def referral_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    app = FastAPI()
    app.include_router(creators_router)
    app.include_router(referrals_router)

    users = {
        "owner": StubUser(
            id="user-owner",
            username="owner",
            display_name="Owner User",
            email="owner@example.com",
        ),
        "creator": StubUser(
            id="user-creator",
            username="creator",
            display_name="Creator User",
            email="creator@example.com",
        ),
        "referred": StubUser(
            id="user-referred",
            username="referred",
            display_name="Referred User",
            email="referred@example.com",
        ),
        "spectator": StubUser(
            id="user-spectator",
            username="spectator",
            display_name="Spectator User",
            email="spectator@example.com",
        ),
    }

    app.state.current_user = users["owner"]

    def override_current_user():
        return app.state.current_user

    def override_session():
        yield session

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        yield app, client, users, session

    session.close()
