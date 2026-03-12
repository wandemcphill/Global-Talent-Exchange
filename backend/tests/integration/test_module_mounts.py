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
    assert "/api/clubs/{club_id}/reputation" in paths
    assert "/api/clubs/{club_id}/dynasty" in paths
    assert "/api/clubs/{club_id}/identity" in paths
    assert "/api/replays/public/featured" in paths
    assert "/api/notifications/me" in paths


def test_integrated_read_routes_are_reachable(integration_client, demo_auth_headers) -> None:
    fast_cups_response = integration_client.get("/api/fast-cups/upcoming")
    world_super_cup_response = integration_client.get("/api/world-super-cup/countdown")
    reputation_response = integration_client.get("/api/clubs/royal-lagos-fc/reputation")
    replay_response = integration_client.get("/api/replays/public/featured")
    notifications_response = integration_client.get("/api/notifications/me", headers=demo_auth_headers)

    assert fast_cups_response.status_code == 200
    assert world_super_cup_response.status_code == 200
    assert reputation_response.status_code == 200
    assert replay_response.status_code == 200
    assert notifications_response.status_code == 200
