from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.simulation_matchmaking.router import router


@pytest.fixture()
def client() -> TestClient:
    application = FastAPI()
    application.include_router(router)
    with TestClient(application) as test_client:
        yield test_client


def _profile(
    user_id: str,
    club_id: str,
    club_name: str,
    *,
    manager_rating: int,
    style: str,
    pressing: str,
    tempo: str,
    squad_strength: int,
    squad_depth: int,
    region: str = "AF-WEST",
) -> dict[str, object]:
    return {
        "user_id": user_id,
        "club_id": club_id,
        "club_name": club_name,
        "manager_rating": manager_rating,
        "tactical_profile": {
            "style": style,
            "pressing": pressing,
            "tempo": tempo,
        },
        "squad_strength": squad_strength,
        "squad_depth": squad_depth,
        "preferred_match_type": ["quick", "tournament", "hosted"],
        "connection_quality": "good",
        "region": region,
        "availability": "online",
    }


def _register_profiles(client: TestClient, prefix: str, *profiles: dict[str, object]) -> None:
    for profile in profiles:
        response = client.put(f"{prefix}/profiles/{profile['user_id']}", json=profile)
        assert response.status_code == 200


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_profile_upsert_round_trip(client: TestClient, prefix: str) -> None:
    payload = _profile(
        "user_123",
        "club_abc",
        "Lagos United",
        manager_rating=1420,
        style="possession",
        pressing="high",
        tempo="fast",
        squad_strength=78,
        squad_depth=65,
    )

    put_response = client.put(f"{prefix}/profiles/user_123", json=payload)
    get_response = client.get(f"{prefix}/profiles/user_123")

    assert put_response.status_code == 200
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["club_name"] == "Lagos United"
    assert body["manager_rating"] == 1420
    assert body["tactical_profile"]["style"] == "possession"


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_game_prefers_tactical_clash_when_requested(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
        _profile(
            "user_789",
            "club_ghi",
            "Abuja Control",
            manager_rating=1410,
            style="balanced",
            pressing="medium",
            tempo="normal",
            squad_strength=77,
            squad_depth=67,
        ),
    )

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "preferences": {
                "match_style": "tactical_clash",
                "allow_tactical_clash": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["opponent"]["user_id"] == "user_456"
    assert body["match_context"]["type"] == "tactical_clash"
    assert body["simulation_bridge"]["recommended_mode"] == "live"
    assert body["simulation_bridge"]["match_engine_request"]["home_team"]["team_name"] == "Lagos United"


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_game_requires_human_opponent_when_queue_empty(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
    )

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "preferences": {
                "match_style": "balanced",
                "allow_tactical_clash": True,
            },
        },
    )

    assert response.status_code == 409
    assert "No suitable quick-game opponent" in response.json()["detail"]


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_game_rejects_ai_or_bot_opponents(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
    )

    response = client.post(
        f"{prefix}/quick-game",
        json={
            "mode": "quick_game",
            "user_id": "user_123",
            "include_bots": True,
            "preferences": {
                "match_style": "balanced",
                "allow_tactical_clash": True,
            },
        },
    )

    assert response.status_code == 422
    assert "human-only" in response.text


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_quick_tournament_avoids_same_style_in_round_one(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
        _profile(
            "user_789",
            "club_ghi",
            "Abuja Control",
            manager_rating=1410,
            style="balanced",
            pressing="medium",
            tempo="normal",
            squad_strength=77,
            squad_depth=67,
        ),
        _profile(
            "user_654",
            "club_jkl",
            "Kumasi Direct",
            manager_rating=1395,
            style="direct",
            pressing="high",
            tempo="fast",
            squad_strength=76,
            squad_depth=63,
        ),
    )

    response = client.post(
        f"{prefix}/quick-tournament",
        json={
            "mode": "quick_tournament",
            "user_id": "user_123",
            "size": 4,
            "preferences": {
                "avoid_same_style_early": True,
                "allow_bots": False,
                "preferred_execution_mode": "hybrid",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["narrative"] == "Clash of styles tournament"
    first_round = body["bracket"][0]["matches"]
    assert len(first_round) == 2
    for match in first_round:
        assert match["home"]["tactical_profile"]["style"] != match["away"]["tactical_profile"]["style"]


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_hosted_competition_preview_exposes_marketplace_hooks(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
        _profile(
            "user_789",
            "club_ghi",
            "Abuja Control",
            manager_rating=1410,
            style="balanced",
            pressing="medium",
            tempo="normal",
            squad_strength=77,
            squad_depth=67,
        ),
        _profile(
            "user_654",
            "club_jkl",
            "Kumasi Direct",
            manager_rating=1395,
            style="direct",
            pressing="high",
            tempo="fast",
            squad_strength=76,
            squad_depth=63,
        ),
    )

    response = client.post(
        f"{prefix}/hosted-competitions/preview",
        json={
            "host_user_id": "user_123",
            "competition_type": "transfer_showcase_cup",
            "target_club_count": 4,
            "simulation_mode": "hybrid",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "knockout"
    assert len(body["qualified_clubs"]) == 4
    assert body["marketplace_hooks"]["transfer_demand_updates"] is True


@pytest.mark.parametrize("prefix", ["/simulation-matchmaking", "/api/simulation-matchmaking"])
def test_hosted_competition_preview_rejects_ai_or_bot_clubs(client: TestClient, prefix: str) -> None:
    _register_profiles(
        client,
        prefix,
        _profile(
            "user_123",
            "club_abc",
            "Lagos United",
            manager_rating=1420,
            style="possession",
            pressing="high",
            tempo="fast",
            squad_strength=78,
            squad_depth=65,
        ),
        _profile(
            "user_456",
            "club_def",
            "Accra Breakers",
            manager_rating=1440,
            style="counter",
            pressing="medium",
            tempo="fast",
            squad_strength=80,
            squad_depth=66,
        ),
    )

    response = client.post(
        f"{prefix}/hosted-competitions/preview",
        json={
            "host_user_id": "user_123",
            "competition_type": "transfer_showcase_cup",
            "target_club_count": 4,
            "simulation_mode": "hybrid",
            "allow_bots": True,
        },
    )

    assert response.status_code == 422
    assert "do not allow AI or bot participants" in response.text
