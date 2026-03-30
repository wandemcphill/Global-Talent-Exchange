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
        "ultimate_league",
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
        "football_universe",
        "broadcast_rights",
        "ownership_groups",
        "real_world_hub",
        "real_world_hub_admin",
        "gtex_universe",
        "federations",
        "federations_admin",
    }.issubset(registered_modules)
    assert "/leagues/register" in openapi_paths
    assert "/champions-league/qualification-map" in openapi_paths
    assert "/academy/season-summary" in openapi_paths
    assert "/ai-manager/autopilot/run" in openapi_paths
    assert "/world-super-cup/countdown" in openapi_paths
    assert "/fast-cups/upcoming" in openapi_paths
    assert "/match-engine/replay" in openapi_paths
    assert "/matches/start" in openapi_paths
    assert "/matches/complete" in openapi_paths
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
    assert "/ultimate-league/tiers" in openapi_paths
    assert "/ultimate-league/tournaments" in openapi_paths
    assert "/api/competitive-integrity/managers" in openapi_paths
    assert "/api/competitive-integrity/matches" in openapi_paths
    assert "/api/competitive-integrity/fast-game/runs" in openapi_paths
    assert "/api/notifications" in openapi_paths
    assert "/broadcast/{match_id}" in openapi_paths
    assert "/broadcast-rights/competitions/{competition_id}" in openapi_paths
    assert "/broadcast-rights/matches/{match_id}/access" in openapi_paths
    assert "/admin/broadcast-rights/jobs/run" in openapi_paths
    assert "/fans/{club_id}" in openapi_paths
    assert "/club/identity" in openapi_paths
    assert "/media" in openapi_paths
    assert "/ownership-groups" in openapi_paths
    assert "/ownership-groups/transfers/validate" in openapi_paths
    assert "/admin/ownership-groups/reputation-cycle" in openapi_paths
    assert "/real-world/providers" in openapi_paths
    assert "/real-world/hybrid-players" in openapi_paths
    assert "/real-world/events" in openapi_paths
    assert "/admin/real-world/providers" in openapi_paths
    assert "/career/create" in openapi_paths
    assert "/career/retire" in openapi_paths
    assert "/career/{user_id}" in openapi_paths
    assert "/sync/update" in openapi_paths
    assert "/federations" in openapi_paths
    assert "/federations/rankings" in openapi_paths
    assert "/federations/{federation_id}/governance" in openapi_paths
    assert "/admin/federations/run-jobs" in openapi_paths
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
    assert "/admin/ops/fan-updates" in openapi_paths
    assert "/admin/ops/media-generation" in openapi_paths
    assert "/admin/ops/identity-evolution" in openapi_paths
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
        match_start_response = client.post("/matches/start", json={})
        match_complete_response = client.post("/matches/complete", json={})
        replay_response = client.get("/matches/nonexistent/replay")
        analysis_response = client.get("/matches/nonexistent/analysis")
        predictions_response = client.get("/predictions")
        finance_response = client.get("/finance")
        sponsors_response = client.get("/sponsors")
        season_pass_response = client.get("/season-pass")
        live_events_response = client.get("/live-events")
        managers_response = client.get("/managers")
        simulation_matchmaking_response = client.post("/simulation-matchmaking/quick-game", json={})
        ultimate_league_tiers_response = client.get("/ultimate-league/tiers")
        ultimate_league_tournament_response = client.post("/ultimate-league/tournaments", json={})
        competitive_integrity_response = client.get("/api/competitive-integrity/managers")
        competitive_notifications_response = client.get("/api/notifications")
        broadcast_response = client.get("/broadcast/nonexistent")
        broadcast_rights_response = client.get("/broadcast-rights/competitions/nonexistent")
        broadcast_access_response = client.get("/broadcast-rights/matches/nonexistent/access")
        broadcast_jobs_response = client.post("/admin/broadcast-rights/jobs/run")
        fans_response = client.get("/fans/nonexistent")
        club_identity_response = client.get("/club/identity", params={"club_id": "nonexistent"})
        media_response = client.get("/media")
        ownership_groups_response = client.get("/ownership-groups")
        ownership_group_validation_response = client.get(
            "/ownership-groups/transfers/validate",
            params={
                "player_id": "nonexistent",
                "selling_club_id": "nonexistent",
                "buying_club_id": "nonexistent",
                "bid_amount": "1.0000",
            },
        )
        ownership_group_reputation_response = client.post("/admin/ownership-groups/reputation-cycle")
        fan_updates_response = client.post("/admin/ops/fan-updates")
        media_generation_response = client.post("/admin/ops/media-generation")
        identity_evolution_response = client.post("/admin/ops/identity-evolution")
        real_world_events_response = client.get("/real-world/events")
        career_get_response = client.get("/career/nonexistent")
        career_retire_response = client.post("/career/retire", json={})
        sync_update_response = client.post("/sync/update", json={})
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
    assert match_start_response.status_code == 422
    assert match_complete_response.status_code == 422
    assert replay_response.status_code == 404
    assert analysis_response.status_code == 404
    assert predictions_response.status_code == 401
    assert finance_response.status_code == 401
    assert sponsors_response.status_code == 401
    assert season_pass_response.status_code == 401
    assert live_events_response.status_code == 401
    assert managers_response.status_code == 200
    assert simulation_matchmaking_response.status_code == 422
    assert ultimate_league_tiers_response.status_code == 200
    assert ultimate_league_tournament_response.status_code == 422
    assert competitive_integrity_response.status_code == 401
    assert competitive_notifications_response.status_code == 401
    assert broadcast_response.status_code == 404
    assert broadcast_rights_response.status_code == 404
    assert broadcast_access_response.status_code == 401
    assert broadcast_jobs_response.status_code == 401
    assert fans_response.status_code == 404
    assert club_identity_response.status_code == 404
    assert media_response.status_code == 200
    assert ownership_groups_response.status_code == 401
    assert ownership_group_validation_response.status_code == 401
    assert ownership_group_reputation_response.status_code == 401
    assert fan_updates_response.status_code == 401
    assert media_generation_response.status_code == 401
    assert identity_evolution_response.status_code == 401
    assert real_world_events_response.status_code == 200
    assert career_get_response.status_code == 404
    assert career_retire_response.status_code == 401
    assert sync_update_response.status_code == 401
    assert regen_universe_response.status_code == 200
    assert regen_rising_stars_response.status_code == 200
    assert regen_bloodlines_response.status_code == 200
    assert regen_scouting_feed_response.status_code == 200
    assert youth_tournaments_response.status_code == 200
    assert youth_tournament_detail_response.status_code == 404
    assert player_story_response.status_code == 404
    assert player_dna_response.status_code == 404
    assert player_rivalries_response.status_code == 404


def test_streamer_tournaments_route_does_not_force_global_lazy_hydration(mounted_app) -> None:
    assert mounted_app.state.modules_hydrated is False

    with TestClient(mounted_app) as client:
        response = client.get("/streamer-tournaments")

    assert response.status_code == 200
    assert mounted_app.state.modules_hydrated is False
