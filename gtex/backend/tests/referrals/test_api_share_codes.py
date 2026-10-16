from __future__ import annotations


def test_share_code_api_creates_lists_updates_and_redeems_codes(referral_api) -> None:
    app, client, users, _session = referral_api
    app.state.current_user = users["owner"]

    create_response = client.post(
        "/api/referrals/share-codes",
        json={
            "share_code_type": "user_referral",
            "vanity_code": "ownerclub",
            "linked_competition_id": "comp-community-1",
            "max_uses": 25,
            "metadata": {"campaign": "spring-growth"},
            "use_as_default": False,
        },
    )
    assert create_response.status_code == 201
    code_payload = create_response.json()
    assert code_payload["code"] == "ownerclub"
    assert code_payload["current_uses"] == 0

    list_response = client.get("/api/referrals/share-codes/me")
    assert list_response.status_code == 200
    assert list_response.json()[0]["code"] == "ownerclub"

    update_response = client.patch(
        f"/api/referrals/share-codes/{code_payload['share_code_id']}",
        json={"active": True, "max_uses": 30, "metadata": {"campaign": "creator-growth"}},
    )
    assert update_response.status_code == 200
    assert update_response.json()["max_uses"] == 30
    assert update_response.json()["metadata"]["campaign"] == "creator-growth"

    app.state.current_user = users["referred"]
    redeem_response = client.post(
        "/api/referrals/share-codes/ownerclub/redeem",
        json={"source_channel": "community_post", "campaign_name": "spring-growth"},
    )
    assert redeem_response.status_code == 200
    redeem_payload = redeem_response.json()
    assert redeem_payload["attribution"]["referred_user_id"] == users["referred"].id
    assert redeem_payload["share_code"]["current_uses"] == 1


def test_share_code_api_blocks_self_referral_and_missing_codes(referral_api) -> None:
    app, client, users, _session = referral_api
    app.state.current_user = users["owner"]
    client.post(
        "/api/referrals/share-codes",
        json={
            "share_code_type": "user_referral",
            "vanity_code": "ownerloop",
            "max_uses": 10,
            "metadata": {},
            "use_as_default": False,
        },
    )

    missing_response = client.post(
        "/api/referrals/share-codes/nope/redeem",
        json={"source_channel": "direct_link"},
    )
    assert missing_response.status_code == 404

    self_redeem_response = client.post(
        "/api/referrals/share-codes/ownerloop/redeem",
        json={"source_channel": "direct_link"},
    )
    assert self_redeem_response.status_code == 409
    assert self_redeem_response.json()["detail"] == "self_referral_blocked"
