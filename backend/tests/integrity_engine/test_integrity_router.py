from __future__ import annotations


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_scan_creates_incidents_from_repeated_gifts_and_rewards(client, demo_seed) -> None:
    admin_headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    sender = demo_seed.demo_users[0]
    recipient = demo_seed.demo_users[1]
    sender_headers = _login(client, email=sender.email, password=sender.password)

    for _ in range(3):
        reward_response = client.post(
            "/admin/reward-engine/settlements",
            headers=admin_headers,
            json={
                "user_id": sender.id,
                "competition_key": "integrity-cup",
                "title": "Integrity Reward",
                "gross_amount": "50",
            },
        )
        assert reward_response.status_code == 200, reward_response.text

    for _ in range(3):
        gift_response = client.post(
            "/gift-engine/send",
            headers=sender_headers,
            json={
                "recipient_user_id": recipient.id,
                "gift_key": "cheer-burst",
                "quantity": "1",
            },
        )
        assert gift_response.status_code == 200, gift_response.text

    scan_response = client.post(
        "/admin/integrity-engine/scan",
        headers=admin_headers,
        json={"repeated_gift_threshold": 3, "reward_cluster_threshold": 3, "lookback_limit": 100},
    )
    assert scan_response.status_code == 200, scan_response.text
    payload = scan_response.json()
    assert len(payload["created_incidents"]) >= 2

    my_score_response = client.get("/integrity-engine/me/score", headers=sender_headers)
    assert my_score_response.status_code == 200, my_score_response.text
    score = my_score_response.json()
    assert float(score["score"]) < 100
    assert score["incident_count"] >= 1

    incidents_response = client.get("/integrity-engine/me/incidents", headers=sender_headers)
    assert incidents_response.status_code == 200, incidents_response.text
    incidents = incidents_response.json()
    assert len(incidents) >= 1

    resolve_response = client.post(
        f"/admin/integrity-engine/incidents/{incidents[0]['id']}/resolve",
        headers=admin_headers,
        json={"resolution_note": "Reviewed and noted."},
    )
    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json()["status"] == "resolved"
