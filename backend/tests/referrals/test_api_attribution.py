from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_user, get_session
from app.routes.creators import router as creators_router
from app.routes.referrals import router as referrals_router


def _build_referral_app(engine, users, *, current_user):
    app = FastAPI()
    app.include_router(creators_router)
    app.include_router(referrals_router)
    app.state.current_user = current_user
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_current_user():
        return app.state.current_user

    def override_session():
        local_session = SessionLocal()
        try:
            yield local_session
        finally:
            local_session.close()

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_session] = override_session
    return app


def test_attribution_api_captures_creator_flow_and_invite_audit(referral_api) -> None:
    app, client, users, _session = referral_api

    app.state.current_user = users["creator"]
    profile_response = client.post(
        "/api/creators/profile",
        json={
            "handle": "invitecaptain",
            "display_name": "Invite Captain",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "creator-cup-1",
        },
    )
    assert profile_response.status_code == 201

    create_code_response = client.post(
        "/api/referrals/share-codes",
        json={
            "share_code_type": "creator_share",
            "vanity_code": "captaincode",
            "linked_competition_id": "creator-cup-1",
            "max_uses": 100,
            "metadata": {"campaign": "creator-cup-launch"},
            "use_as_default": True,
        },
    )
    assert create_code_response.status_code == 201

    app.state.current_user = users["referred"]
    redeem_response = client.post(
        "/api/referrals/share-codes/captaincode/redeem",
        json={
            "source_channel": "creator_profile",
            "campaign_name": "creator-cup-launch",
            "linked_competition_id": "creator-cup-1",
        },
    )
    assert redeem_response.status_code == 200
    assert redeem_response.json()["attribution"]["creator_profile_id"] is not None

    capture_response = client.post(
        "/api/referrals/attribution",
        json={
            "milestone": "first_creator_competition_joined",
            "source_channel": "competition_lobby",
            "linked_competition_id": "creator-cup-1",
        },
    )
    assert capture_response.status_code == 200
    capture_payload = capture_response.json()
    assert "first_creator_competition_joined" in capture_payload["milestones"]
    assert capture_payload["attribution_status"] == "qualified"

    app.state.current_user = users["creator"]
    invites_response = client.get("/api/referrals/me/invites")
    assert invites_response.status_code == 200
    invites_payload = invites_response.json()
    assert invites_payload[0]["share_code"] == "captaincode"
    assert invites_payload[0]["linked_competition_id"] == "creator-cup-1"

    summary_response = client.get("/api/creators/me/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["total_signups"] == 1
    assert summary_payload["qualified_joins"] == 1
    assert summary_payload["active_participants"] == 1


def test_attribution_survives_restart_and_progresses_on_fresh_instance(referral_api) -> None:
    app, client, users, session = referral_api

    app.state.current_user = users["creator"]
    profile_response = client.post(
        "/api/creators/profile",
        json={
            "handle": "restartcaptain",
            "display_name": "Restart Captain",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "creator-cup-restart",
        },
    )
    assert profile_response.status_code == 201, profile_response.text
    share_code = profile_response.json()["default_share_code"]

    app.state.current_user = users["referred"]
    redeem_response = client.post(
        f"/api/referrals/share-codes/{share_code}/redeem",
        json={
            "source_channel": "creator_profile",
            "campaign_name": "restart-launch",
            "linked_competition_id": "creator-cup-restart",
        },
    )
    assert redeem_response.status_code == 200, redeem_response.text

    engine = session.get_bind()
    restarted_app = _build_referral_app(engine, users, current_user=users["referred"])

    with TestClient(restarted_app) as restarted_client:
        capture_response = restarted_client.post(
            "/api/referrals/attribution",
            json={
                "milestone": "first_creator_competition_joined",
                "source_channel": "competition_lobby",
                "linked_competition_id": "creator-cup-restart",
            },
        )
        assert capture_response.status_code == 200, capture_response.text

        restarted_app.state.current_user = users["creator"]

        invites_response = restarted_client.get("/api/referrals/me/invites")
        assert invites_response.status_code == 200, invites_response.text
        invites_payload = invites_response.json()
        assert invites_payload[0]["share_code"] == share_code
        assert "first_creator_competition_joined" in invites_payload[0]["milestones"]

        summary_response = restarted_client.get("/api/creators/me/summary")
        assert summary_response.status_code == 200, summary_response.text
        summary_payload = summary_response.json()
        assert summary_payload["total_signups"] == 1
        assert summary_payload["qualified_joins"] == 1
        assert summary_payload["active_participants"] == 1


def test_attribution_and_competition_views_stay_consistent_across_app_instances(referral_api) -> None:
    app_a, client_a, users, session = referral_api
    engine = session.get_bind()
    app_b = _build_referral_app(engine, users, current_user=users["referred"])

    app_a.state.current_user = users["creator"]
    profile_response = client_a.post(
        "/api/creators/profile",
        json={
            "handle": "scalecaptain",
            "display_name": "Scale Captain",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "creator-cup-scale",
        },
    )
    assert profile_response.status_code == 201, profile_response.text
    share_code = profile_response.json()["default_share_code"]

    with TestClient(app_b) as client_b:
        redeem_response = client_b.post(
            f"/api/referrals/share-codes/{share_code}/redeem",
            json={
                "source_channel": "creator_profile",
                "campaign_name": "scale-launch",
                "linked_competition_id": "creator-cup-scale",
            },
        )
        assert redeem_response.status_code == 200, redeem_response.text

        app_a.state.current_user = users["creator"]
        invites_after_redeem = client_a.get("/api/referrals/me/invites")
        assert invites_after_redeem.status_code == 200, invites_after_redeem.text
        invites_payload = invites_after_redeem.json()
        assert len(invites_payload) == 1
        assert invites_payload[0]["share_code"] == share_code
        assert invites_payload[0]["attribution_status"] == "attributed"

        capture_response = client_b.post(
            "/api/referrals/attribution",
            json={
                "milestone": "first_creator_competition_joined",
                "source_channel": "competition_lobby",
                "linked_competition_id": "creator-cup-scale",
            },
        )
        assert capture_response.status_code == 200, capture_response.text
        assert "first_creator_competition_joined" in capture_response.json()["milestones"]

        summary_response = client_a.get("/api/creators/me/summary")
        assert summary_response.status_code == 200, summary_response.text
        summary_payload = summary_response.json()
        assert summary_payload["total_signups"] == 1
        assert summary_payload["qualified_joins"] == 1
        assert summary_payload["active_participants"] == 1

        competitions_response = client_a.get("/api/creators/me/competitions")
        assert competitions_response.status_code == 200, competitions_response.text
        competitions_payload = competitions_response.json()
        assert competitions_payload[0]["competition_id"] == "creator-cup-scale"
        assert competitions_payload[0]["linked_share_code"] == share_code
        assert competitions_payload[0]["qualified_joins"] == 1

        app_b.state.current_user = users["creator"]
        creator_invites_response = client_b.get("/api/referrals/me/invites")
        assert creator_invites_response.status_code == 200, creator_invites_response.text
        creator_invites = creator_invites_response.json()
        assert creator_invites[0]["share_code"] == share_code
        assert "first_creator_competition_joined" in creator_invites[0]["milestones"]
