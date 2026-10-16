from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_admin, get_session
from app.jobs.ops_jobs import OpsJobRunner
from app.observability.router import admin_router


def test_admin_ops_router_exposes_football_universe_jobs(monkeypatch) -> None:
    monkeypatch.setattr(OpsJobRunner, "run_fan_update_cycle", lambda _self: {"fan_bases_updated": 2})
    monkeypatch.setattr(OpsJobRunner, "run_media_generation_cycle", lambda _self: {"media_events_generated": 3})
    monkeypatch.setattr(OpsJobRunner, "run_identity_evolution_cycle", lambda _self: {"club_identities_evolved": 2})

    app = FastAPI()
    app.include_router(admin_router)
    app.state.session_factory = lambda: None
    app.state.settings = SimpleNamespace()
    app.dependency_overrides[get_current_admin] = lambda: {"id": "admin-user"}
    app.dependency_overrides[get_session] = lambda: iter([None])

    with TestClient(app) as client:
        fan_response = client.post("/admin/ops/fan-updates")
        media_response = client.post("/admin/ops/media-generation")
        identity_response = client.post("/admin/ops/identity-evolution")

    assert fan_response.status_code == 200, fan_response.text
    assert media_response.status_code == 200, media_response.text
    assert identity_response.status_code == 200, identity_response.text
    assert fan_response.json() == {"result": {"fan_bases_updated": 2}}
    assert media_response.json() == {"result": {"media_events_generated": 3}}
    assert identity_response.json() == {"result": {"club_identities_evolved": 2}}
