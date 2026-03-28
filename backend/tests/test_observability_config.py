from __future__ import annotations

from app.auth.service import AuthService
from app.jobs.ops_jobs import OpsJobRunner
from app.main import (
    INITIAL_ADMIN_DISPLAY_NAME,
    INITIAL_ADMIN_EMAIL,
    INITIAL_ADMIN_PASSWORD,
)
from app.risk_ops_engine.service import RiskOpsService


def _ensure_admin_ready(client) -> None:
    startup_thread = getattr(client.app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    with client.app.state.session_factory() as session:
        AuthService().ensure_admin_user(
            session,
            email=INITIAL_ADMIN_EMAIL,
            password=INITIAL_ADMIN_PASSWORD,
            username="observability-test-admin",
            display_name=INITIAL_ADMIN_DISPLAY_NAME,
        )
        session.commit()


def _admin_headers(client) -> dict[str, str]:
    _ensure_admin_ready(client)
    response = client.post("/auth/login", json={"email": INITIAL_ADMIN_EMAIL, "password": INITIAL_ADMIN_PASSWORD})
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


def test_admin_football_universe_job_endpoints_run(client, monkeypatch) -> None:
    headers = _admin_headers(client)
    monkeypatch.setattr(OpsJobRunner, "run_fan_update_cycle", lambda _self: {"fan_bases_updated": 2})
    monkeypatch.setattr(OpsJobRunner, "run_media_generation_cycle", lambda _self: {"media_events_generated": 3})
    monkeypatch.setattr(OpsJobRunner, "run_identity_evolution_cycle", lambda _self: {"club_identities_evolved": 2})

    fan_response = client.post("/admin/ops/fan-updates", headers=headers)
    media_response = client.post("/admin/ops/media-generation", headers=headers)
    identity_response = client.post("/admin/ops/identity-evolution", headers=headers)

    assert fan_response.status_code == 200, fan_response.text
    assert media_response.status_code == 200, media_response.text
    assert identity_response.status_code == 200, identity_response.text
    assert fan_response.json() == {"result": {"fan_bases_updated": 2}}
    assert media_response.json() == {"result": {"media_events_generated": 3}}
    assert identity_response.json() == {"result": {"club_identities_evolved": 2}}
