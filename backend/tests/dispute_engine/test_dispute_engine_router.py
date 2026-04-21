from __future__ import annotations


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_user_can_create_dispute_and_admin_can_action_it(client, demo_seed, demo_auth_headers) -> None:
    reporter = demo_seed.demo_users[0]
    subject = demo_seed.demo_users[1]

    create_response = client.post(
        "/disputes",
        headers=demo_auth_headers,
        json={
            "resource_type": "competition",
            "resource_id": f"comp-{subject.user_id[:6]}",
            "reference": "COMP-001",
            "subject": "Score dispute",
            "message": "The points awarded do not match the fixture.",
            "metadata_json": {},
        },
    )
    assert create_response.status_code == 200, create_response.text
    detail = create_response.json()
    dispute = detail["dispute"]
    assert dispute["user_id"] == reporter.user_id
    assert dispute["status"] == "open"
    assert detail["messages"][0]["sender_role"] == "user"

    my_disputes = client.get("/disputes/me", headers=demo_auth_headers)
    assert my_disputes.status_code == 200
    assert any(item["id"] == dispute["id"] for item in my_disputes.json()["disputes"])

    message_response = client.post(
        f"/disputes/{dispute['id']}/messages",
        headers=demo_auth_headers,
        json={"message": "Adding more context for the dispute."},
    )
    assert message_response.status_code == 200, message_response.text
    assert len(message_response.json()["messages"]) >= 2

    admin_headers = _login(client, "vidvimedialtd@gmail.com", "NewPass1234!")
    queue = client.get("/admin/disputes", headers=admin_headers)
    assert queue.status_code == 200
    assert any(item["id"] == dispute["id"] for item in queue.json()["disputes"])

    assign_response = client.post(
        f"/admin/disputes/{dispute['id']}/assign",
        headers=admin_headers,
        json={},
    )
    assert assign_response.status_code == 200, assign_response.text
    assigned = assign_response.json()
    assert assigned["admin_user_id"] is not None

    status_response = client.post(
        f"/admin/disputes/{dispute['id']}/status",
        headers=admin_headers,
        json={"status": "resolved", "note": "Reviewed and resolved."},
    )
    assert status_response.status_code == 200, status_response.text
    resolved = status_response.json()
    assert resolved["status"] == "resolved"
