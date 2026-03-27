from __future__ import annotations


def test_openapi_exposes_newly_integrated_module_routes(integration_client) -> None:
    response = integration_client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/leagues/register" in paths
    assert "/api/champions-league/qualification-map" in paths
    assert "/api/world-super-cup/qualification/explanation" in paths
    assert "/api/academy/registration" in paths
    assert "/api/fast-cups/upcoming" in paths
    assert "/api/match-engine/replay" in paths
    assert "/api/matches/{match_id}/replay" in paths
    assert "/api/matches/{match_id}/analysis" in paths
    assert "/api/matches/{match_id}/highlights" in paths
    assert "/api/predictions" in paths
    assert "/api/predictions/leaderboard" in paths
    assert "/api/finance" in paths
    assert "/api/sponsors" in paths
    assert "/api/season-pass" in paths
    assert "/api/season-pass/claim" in paths
    assert "/api/live-events" in paths
    assert "/managers" in paths
    assert "/managers/leaderboard" in paths
    assert "/api/manager-duels/leaderboard" in paths
    assert "/api/simulation-matchmaking/quick-game" in paths
    assert "/api/clubs/{club_id}/reputation" in paths
    assert "/api/clubs/{club_id}/dynasty" in paths
    assert "/api/clubs/{club_id}/identity" in paths
    assert "/api/replays/public/featured" in paths
    assert "/api/notifications/me" in paths


def test_integrated_read_routes_are_reachable(integration_client, demo_auth_headers) -> None:
    fast_cups_response = integration_client.get("/api/fast-cups/upcoming")
    world_super_cup_response = integration_client.get("/api/world-super-cup/countdown")
    simulation_matchmaking_response = integration_client.post("/api/simulation-matchmaking/quick-game", json={})
    match_replay_response = integration_client.get("/api/matches/nonexistent/replay")
    match_analysis_response = integration_client.get("/api/matches/nonexistent/analysis")
    predictions_response = integration_client.get("/api/predictions")
    finance_response = integration_client.get("/api/finance")
    sponsors_response = integration_client.get("/api/sponsors")
    season_pass_response = integration_client.get("/api/season-pass")
    live_events_response = integration_client.get("/api/live-events")
    managers_response = integration_client.get("/managers")
    reputation_response = integration_client.get("/api/clubs/royal-lagos-fc/reputation")
    replay_archive_response = integration_client.get("/api/replays/public/featured")
    notifications_response = integration_client.get("/api/notifications/me", headers=demo_auth_headers)

    assert fast_cups_response.status_code == 200
    assert world_super_cup_response.status_code == 200
    assert simulation_matchmaking_response.status_code == 422
    assert match_replay_response.status_code == 404
    assert match_analysis_response.status_code == 404
    assert predictions_response.status_code == 401
    assert finance_response.status_code == 401
    assert sponsors_response.status_code == 401
    assert season_pass_response.status_code == 401
    assert live_events_response.status_code == 401
    assert managers_response.status_code == 200
    assert reputation_response.status_code == 200
    assert replay_archive_response.status_code == 200
    assert notifications_response.status_code == 200
