from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.world_super_cup.api.router import router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_world_super_cup_api_surfaces_demo_tournament_state(monkeypatch) -> None:
    monkeypatch.setenv("GTE_ENABLE_WORLD_SUPER_CUP_DEMO", "true")
    client = _build_client()
    reference_at = datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc).isoformat()

    qualification = client.get("/world-super-cup/qualification/explanation", params={"reference_at": reference_at})
    playoff = client.get("/world-super-cup/playoff/draw", params={"reference_at": reference_at})
    groups = client.get("/world-super-cup/groups/table", params={"reference_at": reference_at})
    bracket = client.get("/world-super-cup/knockout/bracket", params={"reference_at": reference_at})
    countdown = client.get("/world-super-cup/countdown", params={"reference_at": reference_at})

    assert qualification.status_code == 200
    assert qualification.json()["direct_slots"] == 24
    assert len(qualification.json()["direct_qualifiers"]) == 24

    assert playoff.status_code == 200
    assert len(playoff.json()["matches"]) == 8
    assert len(playoff.json()["winners"]) == 8

    assert groups.status_code == 200
    assert len(groups.json()["groups"]) == 8
    assert len(groups.json()["tables"]) == 8
    assert len(groups.json()["advancing_clubs"]) == 16

    assert bracket.status_code == 200
    assert [round_view["round_name"] for round_view in bracket.json()["rounds"]] == [
        "round_of_16",
        "quarterfinal",
        "semifinal",
        "final",
    ]

    assert countdown.status_code == 200
    assert countdown.json()["pause_policy"]["active_competitions"] == [
        "gtex_fast_cup",
        "academy_competitions",
    ]
    assert countdown.json()["source_of_truth"] == "local_projection"
    assert countdown.json()["no_demo_data"] is False
    assert "demo" not in countdown.json()


def test_world_super_cup_demo_routes_fail_closed_in_production(monkeypatch) -> None:
    monkeypatch.delenv("GTE_ENABLE_WORLD_SUPER_CUP_DEMO", raising=False)
    app = FastAPI()
    app.state.settings = SimpleNamespace(app_env="production")
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/world-super-cup/countdown")

    assert response.status_code == 503
    assert "demo projections are disabled" in response.json()["detail"]


def test_world_super_cup_demo_routes_ignore_explicit_enablement_in_production(monkeypatch) -> None:
    monkeypatch.setenv("GTE_ENABLE_WORLD_SUPER_CUP_DEMO", "true")
    app = FastAPI()
    app.state.settings = SimpleNamespace(app_env="production")
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/world-super-cup/countdown")

    assert response.status_code == 503
    assert "protected environments" in response.json()["detail"]
