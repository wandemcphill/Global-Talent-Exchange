from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import get_current_user, get_session
from app.models.regen_ecosystem import Scout
from app.models.regen import RegenScoutReport
from app.models.user import KycStatus, User, UserRole
from app.routes.player_lifecycle import router as player_lifecycle_router
from backend.tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def test_authenticated_player_scout_uses_owned_scout_and_rejects_other_user() -> None:
    session = build_regen_universe_session()
    bundle = seed_two_season_universe(session)
    session.add(
        Scout(
            id="scout-owned",
            club_user_id="user-owner",
            club_id=bundle["club_profile"].id,
            region="Lagos",
            skill_rating=86,
            specialty="youth",
            active=True,
            metadata_json={},
        )
    )
    session.commit()

    current_user = {
        "value": User(
            id="user-owner",
            email="owner@example.com",
            username="owner",
            password_hash="hashed",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
    }

    app = FastAPI()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: current_user["value"]
    app.include_router(player_lifecycle_router)

    with TestClient(app) as client:
        response = client.post("/scout/report/player-wonderkid")

        assert response.status_code == 200
        payload = response.json()
        assert payload["scout_id"] == "scout-owned"
        assert payload["player_id"] == "player-wonderkid"
        assert payload["accuracy"] == 86

        reports = session.scalars(
            select(RegenScoutReport).where(
                RegenScoutReport.regen_id == "profile-player-wonderkid",
                RegenScoutReport.club_id == bundle["club_profile"].id,
                RegenScoutReport.scout_identity == "scout-owned",
            )
        ).all()
        assert len(reports) == 1

        current_user["value"] = User(
            id="other-user",
            email="other@example.com",
            username="other",
            password_hash="hashed",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        denied = client.post("/scout/report/player-wonderkid")
        assert denied.status_code == 404
        assert denied.json()["detail"] == "No active scout is assigned to the authenticated club user"

    session.close()
