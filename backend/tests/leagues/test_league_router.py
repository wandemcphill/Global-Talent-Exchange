from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.leagues.models import LeaguePlayerContribution
from app.leagues.repository import InMemoryLeagueEventRepository
from app.leagues.router import get_league_service, router
from app.leagues.service import LeagueSeasonLifecycleService


@pytest.fixture()
def league_api() -> tuple[TestClient, LeagueSeasonLifecycleService]:
    repository = InMemoryLeagueEventRepository()
    service = LeagueSeasonLifecycleService(repository=repository)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_league_service] = lambda: service

    with TestClient(app) as client:
        yield client, service


def _registration_payload(*, season_id: str = "league-api") -> dict[str, object]:
    return {
        "season_id": season_id,
        "buy_in_tier": 500,
        "season_start": str(date(2026, 3, 11)),
        "clubs": [
            {"club_id": "club-1", "club_name": "Club 1", "strength_rating": 90},
            {"club_id": "club-2", "club_name": "Club 2", "strength_rating": 88},
            {"club_id": "club-3", "club_name": "Club 3", "strength_rating": 84},
            {"club_id": "club-4", "club_name": "Club 4", "strength_rating": 80},
        ],
    }


def test_register_and_read_league_api_contracts(league_api) -> None:
    client, service = league_api

    register_response = client.post("/api/leagues/register", json=_registration_payload())

    assert register_response.status_code == 201
    registration = register_response.json()
    assert set(registration) == {
        "season_id",
        "buy_in_tier",
        "season_start",
        "registered_club_count",
        "group_size_target",
        "group_is_full",
        "scheduled_matches_per_club",
        "target_matches_per_club",
        "total_fixture_count",
        "total_pool",
        "status",
    }
    assert registration["season_id"] == "league-api"
    assert registration["registered_club_count"] == 4

    season = service.get_season_state("league-api")
    service.record_fixture_result(
        season_id="league-api",
        fixture_id=season.fixtures[0].fixture_id,
        home_goals=2,
        away_goals=1,
    )
    service.record_player_stats(
        season_id="league-api",
        player_contributions=(
            LeaguePlayerContribution(
                player_id="player-1",
                player_name="Ayo Striker",
                club_id="club-1",
                goals=2,
                assists=1,
            ),
            LeaguePlayerContribution(
                player_id="player-2",
                player_name="Bola Creator",
                club_id="club-2",
                goals=0,
                assists=1,
            ),
        ),
    )
    service.record_club_opt_out(season_id="league-api", club_id="club-2")

    standings_response = client.get("/api/leagues/league-api/standings")
    assert standings_response.status_code == 200
    standings_payload = standings_response.json()
    assert set(standings_payload) == {"season_id", "status", "rows"}
    assert set(standings_payload["rows"][0]) == {
        "position",
        "club_id",
        "club_name",
        "played",
        "wins",
        "draws",
        "losses",
        "goals_for",
        "goals_against",
        "goal_difference",
        "points",
        "direct_champions_league",
        "champions_league_playoff",
        "next_season_auto_entry",
        "table_color",
        "auto_entry_color",
    }

    fixtures_response = client.get("/api/leagues/league-api/fixtures")
    assert fixtures_response.status_code == 200
    fixtures_payload = fixtures_response.json()
    assert set(fixtures_payload) == {"season_id", "total_fixtures", "day_count", "fixtures"}
    assert set(fixtures_payload["fixtures"][0]) == {
        "fixture_id",
        "round_number",
        "day_number",
        "window_number",
        "kickoff_at",
        "home_club_id",
        "home_club_name",
        "away_club_id",
        "away_club_name",
        "result",
    }

    summary_response = client.get("/api/leagues/league-api/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert set(summary_payload) == {
        "season_id",
        "buy_in_tier",
        "season_start",
        "status",
        "registered_club_count",
        "group_size_target",
        "group_is_full",
        "scheduled_matches_per_club",
        "target_matches_per_club",
        "completed_fixture_count",
        "total_fixture_count",
        "prize_pool",
        "champion_prize",
        "top_scorer_award",
        "top_assist_award",
        "auto_entry_slots",
    }
    assert set(summary_payload["prize_pool"]) == {
        "total_pool",
        "winner_prize",
        "top_scorer_prize",
        "top_assist_prize",
        "champions_league_fund",
    }

    qualification_response = client.get("/api/leagues/league-api/qualification-markers")
    assert qualification_response.status_code == 200
    qualification_payload = qualification_response.json()
    assert set(qualification_payload) == {
        "season_id",
        "opted_out_club_ids",
        "auto_entry_slots",
        "rows",
    }
    assert qualification_payload["opted_out_club_ids"] == ["club-2"]


def test_register_endpoint_rejects_invalid_buy_in(league_api) -> None:
    client, _ = league_api

    payload = _registration_payload(season_id="league-invalid")
    payload["buy_in_tier"] = 42
    response = client.post("/api/leagues/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported league buy-in tier: 42"


def test_missing_season_returns_not_found(league_api) -> None:
    client, _ = league_api

    response = client.get("/api/leagues/unknown-season/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "League season unknown-season was not found"
