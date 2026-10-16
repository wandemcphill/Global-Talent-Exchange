from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.main import create_app
from app.models.competition_match import CompetitionMatch
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.user import User
from app.services.competition_match_service import CompetitionMatchService


def test_router_contracts_cover_fixture_submission_and_manual_settlement(
    client,
    app: FastAPI,
    session: Session,
) -> None:
    app.state.user_state["current_user"] = session.get(User, "fan-one")
    app.state.user_state["current_admin"] = session.get(User, "admin-user")

    fixture_response = client.put(
        "/admin/fan-predictions/matches/match-1/fixture",
        json={
            "promo_pool_fancoin": "75.0000",
            "badge_code": "manual-mvp",
            "metadata_json": {"campaign": "week-1"},
        },
    )
    assert fixture_response.status_code == 200, fixture_response.text
    assert fixture_response.json()["promo_pool_fancoin"] == "75.0000"

    tokens_response = client.get("/fan-predictions/me/tokens")
    assert tokens_response.status_code == 200, tokens_response.text
    assert tokens_response.json()["available_tokens"] == 6

    submission_response = client.post(
        "/fan-predictions/matches/match-1/submissions",
        json={
            "winner_club_id": "club-alpha",
            "first_goal_scorer_player_id": "player-hero",
            "total_goals": 1,
            "mvp_player_id": "player-hero",
            "fan_segment_club_id": "club-alpha",
        },
    )
    assert submission_response.status_code == 201, submission_response.text
    assert submission_response.json()["tokens_spent"] == 1

    app.state.user_state["current_user"] = session.get(User, "fan-two")
    second_submission_response = client.post(
        "/fan-predictions/matches/match-1/submissions",
        json={
            "winner_club_id": "club-bravo",
            "first_goal_scorer_player_id": "player-hero",
            "total_goals": 0,
            "mvp_player_id": "player-bravo",
            "fan_segment_club_id": "club-bravo",
        },
    )
    assert second_submission_response.status_code == 201, second_submission_response.text
    app.state.user_state["current_user"] = session.get(User, "fan-one")

    match_service = CompetitionMatchService(session)
    match_service.record_event(
        competition_id="competition-1",
        match_id="match-1",
        event_type="goal",
        minute=4,
        added_time=None,
        club_id="club-alpha",
        player_id="player-hero",
        secondary_player_id=None,
        card_type=None,
        highlight=True,
        metadata_json={},
    )
    match = session.get(CompetitionMatch, "match-1")
    rule_set = session.get(CompetitionRuleSet, "rules-1")
    assert match is not None
    assert rule_set is not None
    match_service.complete_match(match=match, rule_set=rule_set, home_score=1, away_score=0, winner_club_id="club-alpha")
    session.commit()

    settle_response = client.post(
        "/admin/fan-predictions/matches/match-1/settlement",
        json={
            "mvp_player_id": "player-hero",
            "disburse_rewards": True,
        },
    )
    assert settle_response.status_code == 200, settle_response.text
    settle_payload = settle_response.json()
    assert settle_payload["status"] == "settled"
    fancoin_grant = next(item for item in settle_payload["reward_grants"] if item["reward_type"] == "fancoin")
    assert fancoin_grant["fancoin_amount"] == "75.0000"

    leaderboard_response = client.get("/fan-predictions/leaderboards/weekly")
    assert leaderboard_response.status_code == 200, leaderboard_response.text
    assert leaderboard_response.json()["entries"][0]["user_id"] == "fan-one"


def test_main_app_registers_fan_prediction_routes(test_settings) -> None:
    app = create_app(settings=test_settings, run_migration_check=False)
    paths = {route.path for route in app.routes}
    assert "/fan-predictions/me/tokens" in paths
    assert "/admin/fan-predictions/matches/{match_id}/fixture" in paths
