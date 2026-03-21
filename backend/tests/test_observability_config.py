from __future__ import annotations

from app.risk_ops_engine.service import RiskOpsService


def _admin_headers(client) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": "vidvimedialtd@gmail.com", "password": "NewPass1234!"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_observability_config_snapshot(client):
    response = client.get("/observability/config")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "media_storage" in body
    assert "sponsorship" in body
    assert "payments" in body


def test_admin_audit_feed_lists_events(client, app_session_factory):
    with app_session_factory() as session:
        RiskOpsService(session).log_audit(
            actor_user_id=None,
            action_key="policy.audit.test",
            resource_type="policy_document",
            resource_id="test-doc",
            detail="Audit feed test event.",
            metadata_json={"scope": "test"},
        )
        session.commit()

    headers = _admin_headers(client)
    response = client.get("/admin/ops/audit", headers=headers, params={"action": "policy.audit.test"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(item["action"] == "policy.audit.test" for item in payload)
