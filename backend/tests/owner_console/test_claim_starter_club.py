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
