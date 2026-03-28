from __future__ import annotations


def test_ingest_signal_evaluate_and_release_action(client) -> None:
    signal_response = client.post(
        "/risk-ops/me/signals",
        headers={"x-device-id": "client-device-1"},
        json={"signal_type": "transaction_pattern", "signal_key": "fake_deposit", "metadata_json": {"fake_deposit": True}},
    )
    assert signal_response.status_code == 200
    assert signal_response.json()["user_id"] == "user-alpha"

    evaluate_response = client.post("/admin/risk-ops/evaluate", json={"user_id": "user-alpha"})
    assert evaluate_response.status_code == 200
    assert evaluate_response.json()["users_flagged"] == 1

    restrictions_response = client.get("/risk-ops/me/restrictions")
    assert restrictions_response.status_code == 200
    restrictions_payload = restrictions_response.json()
    assert restrictions_payload["wallet_frozen"] is True
    assert restrictions_payload["withdrawals_blocked"] is True

    actions_response = client.get("/admin/risk-ops/actions", params={"user_id": "user-alpha", "status": "active"})
    assert actions_response.status_code == 200
    action_id = actions_response.json()[0]["id"]

    release_response = client.post(
        f"/admin/risk-ops/actions/{action_id}/release",
        json={"release_note": "False positive after review."},
    )
    assert release_response.status_code == 200
    assert release_response.json()["status"] == "released"
