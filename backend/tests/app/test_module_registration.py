from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.modules import DOMAIN_MODULES

from backend.tests.app._module_registration_contract_data import EXPECTED_REGISTERED_MODULES


def test_real_app_registers_competition_and_identity_modules() -> None:
    registered_modules = {module.name for module in DOMAIN_MODULES}

    assert EXPECTED_REGISTERED_MODULES.issubset(registered_modules)


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
    assert ai_manager_response.status_code == 401
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


@pytest.mark.parametrize(
    ("path", "headers", "expected_status"),
    (
        ("/api/v2/broadcast/home", {"X-API-Version": "2"}, 200),
        ("/api/v2/match-viewer/nonexistent", {"X-API-Version": "2"}, 404),
    ),
)
def test_live_broadcast_and_match_viewer_routes_do_not_force_global_lazy_hydration(
    mounted_app,
    path: str,
    headers: dict[str, str],
    expected_status: int,
) -> None:
    assert mounted_app.state.modules_hydrated is False

    with TestClient(mounted_app) as client:
        response = client.get(path, headers=headers)

    assert response.status_code == expected_status
    assert mounted_app.state.modules_hydrated is False
