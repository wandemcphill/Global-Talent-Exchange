from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api_v1.router import router as api_v1_router
from app.auth.dependencies import get_current_user, get_session
from app.manager_market.router import router as manager_router
from app.models.user import KycStatus, User, UserRole



def _user() -> User:
    return User(
        id="phase6-test-user",
        email="phase6@example.com",
        username="phase6-test-user",
        display_name="Phase 6 Test User",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )


def _session_override() -> Iterator[None]:
    yield None


def _current_user_override() -> User:
    return _user()


def test_legacy_manager_recruit_mutation_is_quarantined() -> None:
    app = FastAPI()
    app.include_router(manager_router)
    app.dependency_overrides[get_current_user] = _current_user_override
    app.dependency_overrides[get_session] = _session_override

    with TestClient(app) as client:
        response = client.post(
            "/api/managers/recruit",
            json={"manager_id": "legacy-manager", "slot": "bench"},
        )

    assert response.status_code == 410
    assert "canonical club staff offer and acceptance lifecycle" in response.json()["detail"]


def test_legacy_tournament_rental_mutation_is_quarantined() -> None:
    app = FastAPI()
    app.include_router(api_v1_router)
    app.dependency_overrides[get_current_user] = _current_user_override

    with TestClient(app) as client:
        response = client.post(
            "/api/v2/tournaments/legacy/rent",
            json={"player_id": "player-legacy"},
        )

    assert response.status_code == 503
    assert "Legacy tournament rentals are disabled" in response.json()["detail"]
