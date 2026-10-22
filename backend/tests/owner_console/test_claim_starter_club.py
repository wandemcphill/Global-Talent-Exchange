"""A new account can claim a club and receive local inbox decisions."""

from __future__ import annotations


def test_claim_starter_club_opens_decisions_without_external_writer(client, bootstrap_admin_headers):
    claimed = client.post("/api/owner/clubs/claim", headers=bootstrap_admin_headers)
    assert claimed.status_code == 200, claimed.text
    claim = claimed.json()
    assert claim["club_name"].endswith("FC")
    assert claim["stage"] == "active"

    center = client.get("/api/owner/control-center", headers=bootstrap_admin_headers)
    assert center.status_code == 200, center.text
    payload = center.json()
    assert len(payload["clubs"]) == 1
    assert payload["decisions"], payload
    assert all(item.get("body") for item in payload["decisions"])
    assert all(item.get("ai_generated") is False for item in payload["decisions"])

    again = client.post("/api/owner/clubs/claim", headers=bootstrap_admin_headers)
    assert again.status_code == 200, again.text
    assert again.json()["club_id"] == claim["club_id"]

    review = client.get("/api/owner/admin/review-queue", headers=bootstrap_admin_headers)
    assert review.status_code == 200, review.text
    queue = review.json()
    assert set(queue) >= {"withdrawals", "flags", "held_payouts"}


def test_dedicated_creator_and_coin_trader_accounts_cannot_enter_club_owner_lane(
    client,
    auth_user_factory,
) -> None:
    from backend.tests.support.signup_payloads import creator_signup_payload

    creator_response = client.post(
        "/auth/signup/creator",
        json=creator_signup_payload(
            email="dedicated-creator-owner-guard@example.com",
            username="dedicated_creator_guard",
            creator_name="Dedicated Creator",
            password="SuperSecret1",
        ),
    )
    assert creator_response.status_code == 201, creator_response.text
    creator_headers = {"Authorization": f"Bearer {creator_response.json()['access_token']}"}

    trader = auth_user_factory(
        suffix="dedicated-trader-owner-guard",
        account_type="coin_trader",
    )

    for headers in (creator_headers, trader["headers"]):
        claim = client.post("/api/owner/clubs/claim", headers=headers)
        assert claim.status_code == 403, claim.text
        assert claim.json()["detail"]["code"] == "club_owner_account_type_required"

        control_center = client.get("/api/owner/control-center", headers=headers)
        assert control_center.status_code == 403, control_center.text
        assert control_center.json()["detail"]["code"] == "club_owner_account_type_required"

