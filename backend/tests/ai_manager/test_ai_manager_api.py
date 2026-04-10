from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from types import SimpleNamespace

from app.auth.dependencies import get_current_user
from app.ai_manager.router import router


@pytest.fixture()
def client() -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


def _profile(club_id: str) -> dict[str, object]:
    return {
        "club_id": club_id,
        "personality_profile": {
            "aggression": 0.72,
            "risk": 0.61,
            "youth_bias": 0.78,
            "discipline": 0.58,
            "adaptability": 0.91,
        },
        "tactical_style": "possession",
        "financial_strategy": "balanced",
    }


def _squad() -> list[dict[str, object]]:
    return [
        {
            "player_id": "gk1",
            "name": "Safe Hands",
            "primary_position": "GK",
            "secondary_positions": [],
            "rating": 80,
            "potential": 84,
            "age": 28,
            "fatigue": 0.18,
            "stamina": 0.84,
            "form": 0.66,
            "injury_risk": 0.16,
            "availability": "available",
            "wage_cost": 6000,
            "transfer_value": 2200000,
            "morale": 0.7,
        },
        {
            "player_id": "rb1",
            "name": "Overlap One",
            "primary_position": "RB",
            "secondary_positions": ["RWB"],
            "rating": 77,
            "potential": 82,
            "age": 24,
            "fatigue": 0.27,
            "stamina": 0.8,
            "form": 0.62,
            "injury_risk": 0.21,
            "availability": "available",
            "wage_cost": 4200,
            "transfer_value": 1800000,
            "morale": 0.68,
        },
        {
            "player_id": "cb1",
            "name": "Wall Alpha",
            "primary_position": "CB",
            "secondary_positions": [],
            "rating": 82,
            "potential": 84,
            "age": 29,
            "fatigue": 0.22,
            "stamina": 0.77,
            "form": 0.63,
            "injury_risk": 0.19,
            "availability": "available",
            "wage_cost": 11000,
            "transfer_value": 2500000,
            "morale": 0.73,
        },
        {
            "player_id": "cb2",
            "name": "Wall Beta",
            "primary_position": "CB",
            "secondary_positions": [],
            "rating": 79,
            "potential": 80,
            "age": 27,
            "fatigue": 0.3,
            "stamina": 0.75,
            "form": 0.58,
            "injury_risk": 0.2,
            "availability": "available",
            "wage_cost": 5000,
            "transfer_value": 2100000,
            "morale": 0.65,
        },
        {
            "player_id": "lb1",
            "name": "Overlap Two",
            "primary_position": "LB",
            "secondary_positions": ["LWB"],
            "rating": 76,
            "potential": 79,
            "age": 25,
            "fatigue": 0.25,
            "stamina": 0.78,
            "form": 0.61,
            "injury_risk": 0.18,
            "availability": "available",
            "wage_cost": 4300,
            "transfer_value": 1700000,
            "morale": 0.67,
        },
        {
            "player_id": "cm1",
            "name": "Tempo Boss",
            "primary_position": "CM",
            "secondary_positions": ["DM"],
            "rating": 81,
            "potential": 83,
            "age": 26,
            "fatigue": 0.31,
            "stamina": 0.8,
            "form": 0.69,
            "injury_risk": 0.2,
            "availability": "available",
            "wage_cost": 7000,
            "transfer_value": 2600000,
            "morale": 0.72,
        },
        {
            "player_id": "cm2",
            "name": "Young Eight",
            "primary_position": "CM",
            "secondary_positions": ["AM"],
            "rating": 73,
            "potential": 89,
            "age": 19,
            "fatigue": 0.28,
            "stamina": 0.81,
            "form": 0.57,
            "injury_risk": 0.18,
            "availability": "available",
            "wage_cost": 1900,
            "transfer_value": 1400000,
            "morale": 0.74,
        },
        {
            "player_id": "cm3",
            "name": "Shield Six",
            "primary_position": "DM",
            "secondary_positions": ["CM"],
            "rating": 78,
            "potential": 79,
            "age": 28,
            "fatigue": 0.33,
            "stamina": 0.79,
            "form": 0.55,
            "injury_risk": 0.22,
            "availability": "available",
            "wage_cost": 5600,
            "transfer_value": 1800000,
            "morale": 0.65,
        },
        {
            "player_id": "rw1",
            "name": "Cut Inside",
            "primary_position": "RW",
            "secondary_positions": ["LW"],
            "rating": 80,
            "potential": 85,
            "age": 23,
            "fatigue": 0.29,
            "stamina": 0.82,
            "form": 0.71,
            "injury_risk": 0.23,
            "availability": "available",
            "wage_cost": 6400,
            "transfer_value": 2800000,
            "morale": 0.76,
        },
        {
            "player_id": "lw1",
            "name": "Wide Spark",
            "primary_position": "LW",
            "secondary_positions": ["RW"],
            "rating": 79,
            "potential": 83,
            "age": 24,
            "fatigue": 0.26,
            "stamina": 0.83,
            "form": 0.68,
            "injury_risk": 0.2,
            "availability": "available",
            "wage_cost": 6100,
            "transfer_value": 2500000,
            "morale": 0.74,
        },
        {
            "player_id": "st1",
            "name": "Press Lead",
            "primary_position": "ST",
            "secondary_positions": ["CF"],
            "rating": 83,
            "potential": 86,
            "age": 25,
            "fatigue": 0.35,
            "stamina": 0.8,
            "form": 0.72,
            "injury_risk": 0.24,
            "availability": "available",
            "wage_cost": 9000,
            "transfer_value": 3200000,
            "morale": 0.78,
        },
        {
            "player_id": "st2",
            "name": "Bench Prospect",
            "primary_position": "ST",
            "secondary_positions": ["LW"],
            "rating": 68,
            "potential": 84,
            "age": 18,
            "fatigue": 0.22,
            "stamina": 0.79,
            "form": 0.44,
            "injury_risk": 0.18,
            "availability": "available",
            "wage_cost": 1200,
            "transfer_value": 900000,
            "morale": 0.69,
        },
        {
            "player_id": "cb3",
            "name": "Tired Veteran",
            "primary_position": "CB",
            "secondary_positions": [],
            "rating": 75,
            "potential": 75,
            "age": 33,
            "fatigue": 0.79,
            "stamina": 0.46,
            "form": 0.38,
            "injury_risk": 0.74,
            "availability": "available",
            "wage_cost": 13000,
            "transfer_value": 700000,
            "morale": 0.41,
        },
    ]


@pytest.mark.parametrize("prefix", ["/ai-manager", "/api/ai-manager"])
def test_profile_round_trip(client: TestClient, prefix: str) -> None:
    put_response = client.put(f"{prefix}/profiles/club-lagos", json=_profile("club-lagos"))
    get_response = client.get(f"{prefix}/profiles/club-lagos")

    assert put_response.status_code == 200
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["club_id"] == "club-lagos"
    assert body["tactical_style"] == "possession"
    assert body["risk_tolerance"] == pytest.approx(0.61)


@pytest.mark.parametrize("prefix", ["/ai-manager", "/api/ai-manager"])
def test_autopilot_activates_offline_and_applies_finance_guardrails(client: TestClient, prefix: str) -> None:
    client.put(f"{prefix}/profiles/club-lagos", json=_profile("club-lagos"))

    response = client.post(
        f"{prefix}/autopilot/run",
        json={
            "club_id": "club-lagos",
            "user_last_active_hours": 9,
            "club_strength": 78,
            "opponent": {
                "club_name": "Capital Giants",
                "strength": 84,
                "tactical_style": "direct",
            },
            "squad": _squad(),
            "finance": {
                "revenue": 100000,
                "wage_bill": 79000,
                "transfer_budget": 3500,
                "cash_balance": 9000,
                "scouting_budget": 1500,
                "training_budget": 1200,
            },
            "market": {
                "hours_since_last_transfer": 72,
                "targets": [
                    {
                        "player_id": "fa1",
                        "name": "Free Midfielder",
                        "position": "CM",
                        "skill": 76,
                        "potential": 81,
                        "fit_to_tactic": 0.84,
                        "wage_cost": 2400,
                        "asking_price": 0,
                        "age": 22,
                        "is_free_agent": True,
                    },
                    {
                        "player_id": "buy1",
                        "name": "Expensive Star",
                        "position": "ST",
                        "skill": 88,
                        "potential": 90,
                        "fit_to_tactic": 0.9,
                        "wage_cost": 12000,
                        "asking_price": 25000,
                        "age": 24,
                        "is_free_agent": False,
                    },
                ],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["activation"]["ai_active"] is True
    assert body["activation"]["reward_penalty_multiplier"] == pytest.approx(0.85)
    assert body["squad_plan"]["formation"] == "4-1-4-1"
    assert any(action["action"] == "prioritize_free_agents" for action in body["finance_actions"])
    assert body["transfer_actions"][0]["action"] == "sign_free_agent"
    assert any(action["action"] == "promote_youth" for action in body["transfer_actions"])
    assert any(item["focus"] == "recovery" for item in body["training_plan"])


@pytest.mark.parametrize("prefix", ["/ai-manager", "/api/ai-manager"])
def test_live_decision_chases_goal_and_triggers_substitution(client: TestClient, prefix: str) -> None:
    client.put(f"{prefix}/profiles/club-lagos", json=_profile("club-lagos"))

    response = client.post(
        f"{prefix}/autopilot/live-decision",
        json={
            "club_id": "club-lagos",
            "minute": 72,
            "score_for": 0,
            "score_against": 1,
            "xg_for": 0.6,
            "xg_against": 1.4,
            "possession_share": 0.37,
            "red_cards_for": 0,
            "red_cards_against": 0,
            "average_stamina": 0.34,
            "opponent_switched_shape": True,
            "substitutions_used": 2,
            "maximum_substitutions": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["directive"] == "go_all_out_attack"
    assert body["formation"] == "3-4-3"
    assert body["tempo"] == "fast"
    assert body["pressing"] == "high"
    assert body["trigger_substitution"] is True
    assert body["substitution_reason"] is not None


@pytest.mark.parametrize("prefix", ["/ai-manager", "/api/ai-manager"])
def test_reward_preview_caps_ai_farming_and_keeps_premium_out_of_outcomes(client: TestClient, prefix: str) -> None:
    standard = client.post(
        f"{prefix}/economy/reward-preview",
        json={
            "base_reward": 1000,
            "difficulty_multiplier": 1.2,
            "division": "d1",
            "win_streak": 5,
            "tournament_stage_weight": 0.5,
            "entry_fee_pool": 200,
            "entry_fee_multiplier": 3,
            "ai_active": True,
            "premium_features_enabled": False,
        },
    )
    premium = client.post(
        f"{prefix}/economy/reward-preview",
        json={
            "base_reward": 1000,
            "difficulty_multiplier": 1.2,
            "division": "d1",
            "win_streak": 5,
            "tournament_stage_weight": 0.5,
            "entry_fee_pool": 200,
            "entry_fee_multiplier": 3,
            "ai_active": True,
            "premium_features_enabled": True,
        },
    )

    assert standard.status_code == 200
    assert premium.status_code == 200
    standard_body = standard.json()
    premium_body = premium.json()
    assert standard_body["raw_win_streak_bonus"] == pytest.approx(0.25)
    assert standard_body["applied_win_streak_bonus"] == pytest.approx(0.15)
    assert standard_body["final_reward"] == premium_body["final_reward"]
    assert premium_body["premium_efficiency_tools"] == [
        "cosmetic upgrades",
        "training acceleration",
        "advanced scouting analytics",
    ]
    assert premium_body["competitive_integrity_passed"] is True
