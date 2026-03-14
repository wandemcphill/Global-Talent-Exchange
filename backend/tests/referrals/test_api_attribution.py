from __future__ import annotations


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
