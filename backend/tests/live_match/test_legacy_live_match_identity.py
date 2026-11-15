from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.live_match.router import router as legacy_live_match_router
from app.live_match.service import LiveMatchEngine, LiveMatchStore
from app.live_matches.router import router as canonical_live_matches_router
from app.modules import DOMAIN_MODULES


def test_production_registry_uses_canonical_live_matches_not_legacy_live_match() -> None:
    registered = {module.name for module in DOMAIN_MODULES}
    assert "live_matches" in registered
    assert "live_match" not in registered


def test_legacy_create_payload_cannot_assign_its_own_manager_identity() -> None:
    app = FastAPI()
    app.include_router(legacy_live_match_router)
    engine = LiveMatchEngine(LiveMatchStore())
    engine_dependency = __import__("app.live_match.router", fromlist=["_engine"])._engine
    app.dependency_overrides[engine_dependency] = lambda: engine
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="attacker-user")

    with TestClient(app) as client:
        created = client.post(
            "/live-match/sessions",
            json={
                "match_id": "legacy-session-1",
                "home_id": "club-home",
                "away_id": "club-away",
                "home_manager_user_id": "attacker-user",
                "away_manager_user_id": "attacker-user",
                "home_user_id": "attacker-user",
                "away_user_id": "attacker-user",
            },
        )

        assert created.status_code == 201, created.text
        assert created.json()["your_side"] is None
        session = engine.get("legacy-session-1")
        assert session.home_manager_user_id is None
        assert session.away_manager_user_id is None
        assert session.home_user_id is None
        assert session.away_user_id is None

        tactics = client.post(
            "/live-match/sessions/legacy-session-1/tactics",
            json={"side": "home", "formation": "4-2-3-1"},
        )
        assert tactics.status_code == 403, tactics.text


def test_canonical_live_matches_router_is_the_registered_v2_surface() -> None:
    assert canonical_live_matches_router.prefix == "/api/matches"
