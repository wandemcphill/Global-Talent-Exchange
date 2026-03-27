from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

@pytest.fixture()
def mounted_app():
    temp_root = Path(__file__).resolve().parents[2] / ".tmp_testdbs"
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = temp_root / f"gte_module_registration_{uuid4().hex}.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    from app.main import create_app

    try:
        yield create_app(engine=engine, run_migration_check=True)
    finally:
        engine.dispose()
        try:
            database_path.unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            pass


def test_real_app_registers_competition_and_identity_modules(mounted_app) -> None:
    with TestClient(mounted_app):
        openapi_paths = mounted_app.openapi()["paths"]
        registered_modules = set(mounted_app.state.domain_modules)

    assert {
        "leagues",
        "champions_league",
        "academy",
        "ai_manager",
        "world_super_cup",
        "fast_cups",
        "match_engine",
        "matches",
        "simulation_matchmaking",
        "manager_marketplace",
        "predictions",
        "club_finance",
        "live_ops",
        "canonical_clubs",
        "competitive_integrity",
        "club_identity",
        "replay_archive",
        "notifications",
        "regen_universe",
    }.issubset(registered_modules)
    assert "/leagues/register" in openapi_paths
    assert "/champions-league/qualification-map" in openapi_paths
    assert "/academy/season-summary" in openapi_paths
    assert "/ai-manager/autopilot/run" in openapi_paths
    assert "/world-super-cup/countdown" in openapi_paths
    assert "/fast-cups/upcoming" in openapi_paths
    assert "/match-engine/replay" in openapi_paths
    assert "/matches/{match_id}/replay" in openapi_paths
    assert "/matches/{match_id}/analysis" in openapi_paths
    assert "/predictions" in openapi_paths
    assert "/predictions/leaderboard" in openapi_paths
    assert "/finance" in openapi_paths
    assert "/sponsors" in openapi_paths
    assert "/season-pass" in openapi_paths
    assert "/season-pass/claim" in openapi_paths
    assert "/live-events" in openapi_paths
    assert "/api/predictions" in openapi_paths
    assert "/api/finance" in openapi_paths
    assert "/api/season-pass" in openapi_paths
    assert "/managers" in openapi_paths
    assert "/managers/leaderboard" in openapi_paths
    assert "/simulation-matchmaking/quick-game" in openapi_paths
    assert "/api/competitive-integrity/managers" in openapi_paths
    assert "/api/competitive-integrity/matches" in openapi_paths
    assert "/api/competitive-integrity/fast-game/runs" in openapi_paths
    assert "/api/notifications" in openapi_paths
    assert "/api/clubs/{club_id}/reputation" in openapi_paths
    assert "/api/clubs/{club_id}/dynasty" in openapi_paths
    assert "/api/clubs/{club_id}/identity" in openapi_paths
    assert "/regen-universe/awards" in openapi_paths
    assert "/regen-universe/rising-stars" in openapi_paths
    assert "/regen-universe/bloodlines" in openapi_paths
    assert "/regen-universe/scouting-feed" in openapi_paths
    assert "/regen-universe/youth-tournaments" in openapi_paths
    assert "/regen-universe/youth-tournaments/{tournament_id}" in openapi_paths
    assert "/admin/regen-universe/youth-tournaments" in openapi_paths
    assert "/admin/regen-universe/jobs/story-regeneration" in openapi_paths
    assert "/admin/regen-universe/jobs/rivalry-detection" in openapi_paths
    assert "/admin/regen-universe/jobs/dna-evolution" in openapi_paths
    assert "/admin/regen-universe/jobs/tournament-scheduling" in openapi_paths
    assert "/players/{player_id}/story" in openapi_paths
    assert "/players/{player_id}/dna" in openapi_paths
    assert "/players/{player_id}/rivalries" in openapi_paths
    assert "/replays/public/featured" in openapi_paths
    assert "/notifications/me" in openapi_paths


def test_mounted_module_routes_resolve_on_the_real_app(mounted_app) -> None:
    with TestClient(mounted_app) as client:
        world_super_cup_response = client.get("/world-super-cup/countdown")
        fast_cups_response = client.get("/fast-cups/upcoming")
        replay_archive_response = client.get("/replays/public/featured")
        leagues_response = client.post("/leagues/register", json={})
        champions_league_response = client.post("/champions-league/qualification-map", json={})
        academy_response = client.post("/academy/season-summary", json={})
        ai_manager_response = client.post("/ai-manager/autopilot/run", json={})
        match_engine_response = client.post("/match-engine/summary", json={})
        replay_response = client.get("/matches/nonexistent/replay")
        analysis_response = client.get("/matches/nonexistent/analysis")
        predictions_response = client.get("/predictions")
        finance_response = client.get("/finance")
        sponsors_response = client.get("/sponsors")
        season_pass_response = client.get("/season-pass")
        live_events_response = client.get("/live-events")
        managers_response = client.get("/managers")
        simulation_matchmaking_response = client.post("/simulation-matchmaking/quick-game", json={})
        competitive_integrity_response = client.get("/api/competitive-integrity/managers")
        competitive_notifications_response = client.get("/api/notifications")
        regen_universe_response = client.get("/regen-universe/awards")
        regen_rising_stars_response = client.get("/regen-universe/rising-stars")
        regen_bloodlines_response = client.get("/regen-universe/bloodlines")
        regen_scouting_feed_response = client.get("/regen-universe/scouting-feed")
        youth_tournaments_response = client.get("/regen-universe/youth-tournaments")
        youth_tournament_detail_response = client.get("/regen-universe/youth-tournaments/nonexistent")
        player_story_response = client.get("/players/nonexistent/story")
        player_dna_response = client.get("/players/nonexistent/dna")
        player_rivalries_response = client.get("/players/nonexistent/rivalries")

    assert world_super_cup_response.status_code == 200
    assert fast_cups_response.status_code == 200
    assert replay_archive_response.status_code == 200
    assert leagues_response.status_code == 422
    assert champions_league_response.status_code == 422
    assert academy_response.status_code == 422
    assert ai_manager_response.status_code == 422
    assert match_engine_response.status_code == 422
    assert replay_response.status_code == 404
    assert analysis_response.status_code == 404
    assert predictions_response.status_code == 401
    assert finance_response.status_code == 401
    assert sponsors_response.status_code == 401
    assert season_pass_response.status_code == 401
    assert live_events_response.status_code == 401
    assert managers_response.status_code == 200
    assert simulation_matchmaking_response.status_code == 422
    assert competitive_integrity_response.status_code == 401
    assert competitive_notifications_response.status_code == 401
    assert regen_universe_response.status_code == 200
    assert regen_rising_stars_response.status_code == 200
    assert regen_bloodlines_response.status_code == 200
    assert regen_scouting_feed_response.status_code == 200
    assert youth_tournaments_response.status_code == 200
    assert youth_tournament_detail_response.status_code == 404
    assert player_story_response.status_code == 404
    assert player_dna_response.status_code == 404
    assert player_rivalries_response.status_code == 404
