from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth.dependencies import get_current_user
from app.routes.admin_referrals import router as admin_referrals_router
from app.routes.creators import router as creators_router
from app.routes.referrals import router as referrals_router
from app.services.referral_orchestrator import ReferralOrchestrator


@dataclass(frozen=True, slots=True)
class StubUser:
    id: str
    username: str
    display_name: str
    email: str
    role: str = "user"


@pytest.fixture()
def admin_referral_api():
    app = FastAPI()
    app.include_router(creators_router)
    app.include_router(referrals_router)
    app.include_router(admin_referrals_router)
    app.state.referral_orchestrator = ReferralOrchestrator()

    users = {
        "admin": StubUser("user-admin", "admin", "Admin User", "admin@example.com", role="admin"),
        "creator_alpha": StubUser("user-alpha", "alpha", "Alpha Creator", "alpha@example.com"),
        "creator_beta": StubUser("user-beta", "beta", "Beta Creator", "beta@example.com"),
        "referred_1": StubUser("user-r1", "referred1", "Referred 1", "r1@example.com"),
        "referred_2": StubUser("user-r2", "referred2", "Referred 2", "r2@example.com"),
        "referred_3": StubUser("user-r3", "referred3", "Referred 3", "r3@example.com"),
    }
    app.state.current_user = users["admin"]

    def override_current_user():
        return app.state.current_user

    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield app, client, users


def test_admin_can_inspect_analytics_review_rewards_and_block_share_codes(admin_referral_api) -> None:
    app, client, users = admin_referral_api

    alpha_code = _create_creator_profile(
        app,
        client,
        users["creator_alpha"],
        handle="alphaone",
        competition_id="comp-alpha",
    )
    beta_code = _create_creator_profile(
        app,
        client,
        users["creator_beta"],
        handle="betaone",
        competition_id="comp-beta",
    )

    _redeem_and_progress(
        app,
        client,
        users["referred_1"],
        alpha_code,
        campaign_name="alpha-growth",
        linked_competition_id="comp-alpha",
        milestones=["verification_completed", "first_creator_competition_joined", "retained_day_7"],
    )
    _redeem_and_progress(
        app,
        client,
        users["referred_2"],
        alpha_code,
        campaign_name="alpha-growth",
        linked_competition_id="comp-alpha",
        milestones=["first_creator_competition_joined"],
    )
    _redeem_and_progress(
        app,
        client,
        users["referred_3"],
        beta_code,
        campaign_name="beta-growth",
        linked_competition_id="comp-beta",
        milestones=["first_creator_competition_joined", "retained_day_7"],
    )

    app.state.current_user = users["admin"]

    analytics_response = client.get("/api/admin/referrals/analytics/summary")
    assert analytics_response.status_code == 200
    analytics_payload = analytics_response.json()
    assert analytics_payload["codes_created"] == 2
    assert analytics_payload["attributed_signups"] == 3
    assert analytics_payload["qualified_referrals"] >= 3
    assert analytics_payload["top_campaigns"][0]["creator_handle"] == "alphaone"

    share_codes_response = client.get("/api/admin/referrals/share-codes")
    assert share_codes_response.status_code == 200
    share_codes_payload = share_codes_response.json()
    alpha_summary = next(item for item in share_codes_payload if item["code"] == alpha_code)
    assert alpha_summary["attributed_signups"] == 2
    assert alpha_summary["creator_competition_joins"] == 2

    creators_before_review_response = client.get("/api/admin/referrals/creators")
    assert creators_before_review_response.status_code == 200
    creators_before_review = creators_before_review_response.json()
    alpha_creator_before_review = next(item for item in creators_before_review if item["handle"] == "alphaone")

    pending_response = client.get("/api/admin/referrals/rewards/pending")
    assert pending_response.status_code == 200
    pending_payload = pending_response.json()
    assert len(pending_payload) == 3
    alpha_pending_reward = next(
        item for item in pending_payload if item["beneficiary_creator_id"] == alpha_creator_before_review["creator_id"]
    )

    review_response = client.post(
        f"/api/admin/referrals/rewards/{alpha_pending_reward['reward_id']}/review",
        json={"action": "approve", "reason": "qualified participation confirmed", "reference": "case-001"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status_after"] == "approved"

    alpha_creator_response = client.get("/api/admin/referrals/creators")
    assert alpha_creator_response.status_code == 200
    creators_payload = alpha_creator_response.json()
    alpha_creator = next(item for item in creators_payload if item["handle"] == "alphaone")
    assert alpha_creator["attributed_signups"] == 2
    assert alpha_creator["pending_rewards"] == 1

    block_response = client.post(
        f"/api/admin/referrals/share-codes/{alpha_summary['code_id']}/block",
        json={"reason": "manual integrity review", "disable_code": True},
    )
    assert block_response.status_code == 200
    assert block_response.json()["active"] is False

    dashboard_response = client.get("/api/admin/referrals/dashboard")
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["blocked_share_codes"] == 1
    assert dashboard_payload["pending_rewards"] == 2


def _create_creator_profile(app: FastAPI, client: TestClient, user: StubUser, *, handle: str, competition_id: str) -> str:
    app.state.current_user = user
    response = client.post(
        "/api/creators/profile",
        json={
            "handle": handle,
            "display_name": handle.title(),
            "tier": "featured",
            "status": "active",
            "default_competition_id": competition_id,
            "revenue_share_percent": "12.5",
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
    campaign_name: str,
    linked_competition_id: str,
    milestones: list[str],
) -> None:
    app.state.current_user = user
    redeem_response = client.post(
        f"/api/referrals/share-codes/{share_code}/redeem",
        json={
            "source_channel": "community_post",
            "campaign_name": campaign_name,
            "linked_competition_id": linked_competition_id,
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
                "campaign_name": campaign_name,
                "linked_competition_id": linked_competition_id,
            },
        )
        assert capture_response.status_code == 200, capture_response.text
