from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.app.auth.dependencies import get_current_user
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

    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield app, client, users
