from __future__ import annotations


def test_reward_api_surfaces_pending_and_approved_rewards_for_referrers_and_creators(referral_api) -> None:
    app, client, users, _session = referral_api

    app.state.current_user = users["creator"]
    client.post(
        "/api/creators/profile",
        json={
            "handle": "rewardpilot",
            "display_name": "Reward Pilot",
            "tier": "pro",
            "status": "active",
            "default_competition_id": "creator-cup-9",
        },
    )
    client.post(
        "/api/referrals/share-codes",
        json={
            "share_code_type": "creator_share",
            "vanity_code": "rewardpilot9",
            "linked_competition_id": "creator-cup-9",
            "max_uses": 500,
            "metadata": {"campaign": "reward-pilot"},
            "use_as_default": True,
        },
    )

    app.state.current_user = users["referred"]
    redeem_response = client.post(
        "/api/referrals/share-codes/rewardpilot9/redeem",
        json={"source_channel": "creator_profile", "linked_competition_id": "creator-cup-9"},
    )
    assert redeem_response.status_code == 200

    for milestone in (
        "verification_completed",
        "first_paid_competition_joined",
        "first_creator_competition_joined",
        "retained_day_30",
    ):
        response = client.post(
            "/api/referrals/attribution",
            json={
                "milestone": milestone,
                "source_channel": "competition_lobby",
                "linked_competition_id": "creator-cup-9",
            },
        )
        assert response.status_code == 200

    app.state.current_user = users["creator"]
    rewards_response = client.get("/api/referrals/me/rewards")
    assert rewards_response.status_code == 200
    rewards_payload = rewards_response.json()
    reward_types = {item["reward_type"] for item in rewards_payload}
    assert reward_types == {"points", "wallet_credit", "badge", "creator_revshare"}
    assert any(item["reward_type"] == "creator_revshare" and item["status"] == "pending" for item in rewards_payload)
    assert any(item["reward_type"] == "wallet_credit" and item["review_reason"] == "ledger_hook_pending" for item in rewards_payload)

    summary_response = client.get("/api/referrals/me/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["approved_rewards"] >= 2
    assert summary_payload["pending_rewards"] >= 1
