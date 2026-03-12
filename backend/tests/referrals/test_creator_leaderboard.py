from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.app.auth.dependencies import get_current_user
from backend.app.routes.admin_referrals import router as admin_referrals_router
from backend.app.routes.creators import router as creators_router
from backend.app.routes.referrals import router as referrals_router
from backend.app.services.referral_orchestrator import ReferralOrchestrator


@dataclass(frozen=True, slots=True)
class StubUser:
    id: str
    username: str
    display_name: str
    email: str
    role: str = "user"


@pytest.fixture()
def leaderboard_api():
    app = FastAPI()
    app.include_router(creators_router)
    app.include_router(referrals_router)
    app.include_router(admin_referrals_router)
    app.state.referral_orchestrator = ReferralOrchestrator()

    users = {
        "admin": StubUser("user-admin", "admin", "Admin User", "admin@example.com", role="admin"),
        "creator_alpha": StubUser("user-alpha", "alpha", "Alpha Creator", "alpha@example.com"),
        "creator_beta": StubUser("user-beta", "beta", "Beta Creator", "beta@example.com"),
        "referred_a1": StubUser("user-a1", "a1", "A1", "a1@example.com"),
        "referred_a2": StubUser("user-a2", "a2", "A2", "a2@example.com"),
        "referred_b1": StubUser("user-b1", "b1", "B1", "b1@example.com"),
        "referred_b2": StubUser("user-b2", "b2", "B2", "b2@example.com"),
    }
    app.state.current_user = users["admin"]

    def override_current_user():
        return app.state.current_user

    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield app, client, users


def test_creator_leaderboard_orders_by_fraud_adjusted_growth(leaderboard_api) -> None:
    app, client, users = leaderboard_api

    alpha_code = _create_creator_profile(app, client, users["creator_alpha"], "alphaone", "comp-alpha")
    beta_code = _create_creator_profile(app, client, users["creator_beta"], "betaone", "comp-beta")

    _redeem_and_progress(
        app,
        client,
        users["referred_a1"],
        alpha_code,
        milestones=[],
        competition_id="comp-alpha",
    )
    _redeem_and_progress(
        app,
        client,
        users["referred_a2"],
        alpha_code,
        milestones=[],
        competition_id="comp-alpha",
    )

    _redeem_and_progress(
        app,
        client,
        users["referred_b1"],
        beta_code,
        milestones=["first_creator_competition_joined", "retained_day_7"],
        competition_id="comp-beta",
    )
    _redeem_and_progress(
        app,
        client,
        users["referred_b2"],
        beta_code,
        milestones=["first_creator_competition_joined", "retained_day_7"],
        competition_id="comp-beta",
    )

    app.state.current_user = users["admin"]
    leaderboard_response = client.get("/api/admin/referrals/leaderboard")
    assert leaderboard_response.status_code == 200
    payload = leaderboard_response.json()

    assert payload["items"][0]["creator_handle"] == "betaone"
    assert payload["items"][0]["headline"] == "Strongest retained community growth"
    assert Decimal(payload["items"][0]["fraud_adjusted_score"]) > Decimal(payload["items"][1]["fraud_adjusted_score"])
    assert payload["items"][1]["creator_handle"] == "alphaone"


def _create_creator_profile(app: FastAPI, client: TestClient, user: StubUser, handle: str, competition_id: str) -> str:
    app.state.current_user = user
    response = client.post(
        "/api/creators/profile",
        json={
            "handle": handle,
            "display_name": handle.title(),
            "tier": "featured",
            "status": "active",
            "default_competition_id": competition_id,
            "revenue_share_percent": "10",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["default_share_code"]


def _redeem_and_progress(
    app: FastAPI,
    client: TestClient,
    user: StubUser,
    share_code: str,
    *,
    milestones: list[str],
    competition_id: str,
) -> None:
    app.state.current_user = user
    redeem_response = client.post(
        f"/api/referrals/share-codes/{share_code}/redeem",
        json={
            "source_channel": "community_post",
            "campaign_name": "creator-growth",
            "linked_competition_id": competition_id,
        },
    )
    assert redeem_response.status_code == 200, redeem_response.text

    for milestone in milestones:
        capture_response = client.post(
            "/api/referrals/attribution",
            json={
                "share_code": share_code,
                "source_channel": "community_post",
                "milestone": milestone,
                "campaign_name": "creator-growth",
                "linked_competition_id": competition_id,
            },
        )
        assert capture_response.status_code == 200, capture_response.text
