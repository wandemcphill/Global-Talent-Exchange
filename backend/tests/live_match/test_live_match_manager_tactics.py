from __future__ import annotations

import importlib
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth.dependencies import get_current_user
from app.live_match.router import router
from app.live_match.service import LiveMatchEngine, LiveMatchStore

live_match_router_module = importlib.import_module("app.live_match.router")

HOME_OWNER = SimpleNamespace(id="owner-home")
AWAY_OWNER = SimpleNamespace(id="owner-away")
HOME_MANAGER = SimpleNamespace(id="manager-home")
AWAY_MANAGER = SimpleNamespace(id="manager-away")
SPECTATOR = SimpleNamespace(id="spectator-user")


@pytest.fixture()
def engine() -> LiveMatchEngine:
    return LiveMatchEngine(LiveMatchStore())


def _build_client(engine: LiveMatchEngine, user: object | None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[live_match_router_module._engine] = lambda: engine
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_manager_authority_over_tactics_in_live_match_router(engine: LiveMatchEngine) -> None:
    match_id = "duel-match-001"
    engine.create(
        match_id=match_id,
        home_id="club-home",
        away_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        home_overall=80,
        away_overall=75,
        home_user_id=HOME_OWNER.id,
        away_user_id=AWAY_OWNER.id,
        home_manager_user_id=HOME_MANAGER.id,
        away_manager_user_id=AWAY_MANAGER.id,
    )

    # 1. Anonymous -> 401
    anon_client = _build_client(engine, user=None)
    res = anon_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={"side": "home", "formation": "4-3-3", "tempo": 70},
    )
    assert res.status_code == 401

    # 2. Spectator -> 403
    spec_client = _build_client(engine, user=SPECTATOR)
    res = spec_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={"side": "home", "formation": "4-3-3", "tempo": 70},
    )
    assert res.status_code == 403
    assert "First-Team Manager" in res.json()["detail"]

    # 3. Plain Owner (home_user_id) -> 403 because home_manager_user_id is appointed!
    home_owner_client = _build_client(engine, user=HOME_OWNER)
    res = home_owner_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={"side": "home", "formation": "4-3-3", "tempo": 70},
    )
    assert res.status_code == 403
    assert "First-Team Manager" in res.json()["detail"]

    # 4. Away Manager targeting home -> 403
    away_mgr_client = _build_client(engine, user=AWAY_MANAGER)
    res = away_mgr_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={"side": "home", "formation": "4-3-3", "tempo": 70},
    )
    assert res.status_code == 403

    # 5. Home Manager targeting home -> 200
    home_mgr_client = _build_client(engine, user=HOME_MANAGER)
    res = home_mgr_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={
            "side": "home",
            "formation": "4-2-3-1",
            "pressing": 75,
            "tempo": 80,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["match_id"] == match_id
    assert data["home_tactics"]["formation"] == "4-2-3-1"
    assert data["home_tactics"]["pressing"] == 75

    # 6. Away Manager targeting away -> 200
    res = away_mgr_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={
            "side": "away",
            "formation": "3-5-2",
            "pressing": 65,
            "tempo": 60,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["away_tactics"]["formation"] == "3-5-2"
    assert data["away_tactics"]["pressing"] == 65

    # 7. Completed match lock -> 400
    session = engine.get(match_id)
    session.phase = "full_time"
    res = home_mgr_client.post(
        f"/live-match/sessions/{match_id}/tactics",
        json={"side": "home", "formation": "4-4-2"},
    )
    assert res.status_code == 400
    assert "full_time" in res.json()["detail"] or "completed" in res.json()["detail"].lower()
