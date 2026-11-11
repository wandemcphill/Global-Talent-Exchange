from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth.dependencies import get_current_user
from app.leagues.models import LeaguePlayerContribution
from app.leagues.repository import InMemoryLeagueEventRepository
from app.leagues.router import get_league_service, router
from app.leagues.service import LeagueSeasonLifecycleService


def _build_league_app(service: LeagueSeasonLifecycleService) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_league_service] = lambda: service
    return app


@pytest.fixture()
def league_api() -> tuple[TestClient, LeagueSeasonLifecycleService]:
    repository = InMemoryLeagueEventRepository()
    service = LeagueSeasonLifecycleService(repository=repository)
    app = _build_league_app(service)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="league-organiser")

    with TestClient(app) as client:
        yield client, service


@pytest.fixture()
def anonymous_league_api() -> tuple[TestClient, LeagueSeasonLifecycleService]:
    """A client with no authenticated identity, to exercise the auth boundary."""
    repository = InMemoryLeagueEventRepository()
    service = LeagueSeasonLifecycleService(repository=repository)

    with TestClient(_build_league_app(service)) as client:
        yield client, service


def _registration_payload(*, season_id: str = "league-api") -> dict[str, object]:
    return {
        "season_id": season_id,
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
    assert registration["buy_in_tier"] == 0
    assert registration["total_pool"] == 500
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


def test_register_endpoint_ignores_buy_in_and_records_zero(league_api) -> None:
    client, _ = league_api

    payload = _registration_payload(season_id="league-free")
    payload["buy_in_tier"] = 42
    response = client.post("/api/leagues/register", json=payload)

    assert response.status_code == 201
    assert response.json()["buy_in_tier"] == 0
    assert response.json()["total_pool"] == 500


def test_rollover_waits_until_every_division_is_finished(league_api) -> None:
    client, _service = league_api
    registered = client.post("/api/leagues/register", json=_registration_payload())
    assert registered.status_code == 201

    response = client.post(
        "/api/leagues/rollover",
        json={
            "season_ids": ["league-api"],
            "season_label": "2031",
            "season_start": "2027-08-01",
        },
    )

    assert response.status_code == 400
    assert "finish" in response.json()["detail"]


def test_missing_season_returns_not_found(league_api) -> None:
    client, _ = league_api

    response = client.get("/api/leagues/unknown-season/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "League season unknown-season was not found"


def test_register_endpoint_rejects_unauthenticated_callers(anonymous_league_api) -> None:
    """League seasons are shared state; an anonymous caller must not create one."""
    client, service = anonymous_league_api

    response = client.post("/api/leagues/register", json=_registration_payload(season_id="anon-season"))

    assert response.status_code == 401
    assert service.repository.list_events("anon-season") == ()


def test_legacy_register_endpoint_rejects_unauthenticated_callers(anonymous_league_api) -> None:
    client, service = anonymous_league_api

    response = client.post("/leagues/register", json=_registration_payload(season_id="anon-legacy"))

    assert response.status_code == 401
    assert service.repository.list_events("anon-legacy") == ()


def test_register_endpoint_accepts_authenticated_callers(league_api) -> None:
    client, service = league_api

    response = client.post("/api/leagues/register", json=_registration_payload(season_id="authed-season"))

    assert response.status_code == 201
    assert service.get_season_state("authed-season").season_id == "authed-season"


def test_rollover_writes_the_new_division_onto_the_owner_club() -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401
    from app.models import Base
    from app.owner_console.models import OwnerClubState

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    clubs = (("ape", "Ape"), ("bear", "Bear"), ("cat", "Cat"), ("dog", "Dog"))
    with session_factory() as session:
        for club_id, club_name in clubs:
            session.add(
                OwnerClubState(
                    club_id=club_id,
                    owner_user_id="owner",
                    club_name=club_name,
                    stage="active",
                    manager_json={},
                    facilities_json={},
                    value_history_json=[],
                )
            )
        session.commit()

    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    app = _build_league_app(service)
    app.state.session_factory = session_factory
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="league-organiser")
    with TestClient(app) as client:
        registered = client.post(
            "/api/leagues/register",
            json={
                "season_id": "owner-foundation",
                "buy_in_tier": 25,
                "season_start": "2026-08-01",
                "clubs": [
                    {"club_id": club_id, "club_name": club_name, "strength_rating": 50} for club_id, club_name in clubs
                ],
            },
        )
        assert registered.status_code == 201, registered.text
        season = service.get_season_state("owner-foundation")
        assert season.division_level == "foundation"
        assert season.region_code == "UNASSIGNED"
        assert season.scheduled_matches_per_club == 3
        for fixture in season.fixtures:
            home = fixture.home_club_id
            away = fixture.away_club_id
            if home == "ape":
                home_goals, away_goals = 1, 0
            elif away == "ape":
                home_goals, away_goals = 0, 1
            else:
                home_goals, away_goals = 0, 0
            service.record_fixture_result(
                season_id=season.season_id,
                fixture_id=fixture.fixture_id,
                home_goals=home_goals,
                away_goals=away_goals,
            )
        rolled = client.post(
            "/api/leagues/rollover",
            json={
                "season_ids": ["owner-foundation"],
                "season_label": "2031",
                "season_start": "2027-08-01",
            },
        )
        assert rolled.status_code == 200, rolled.text
        assert "2031-UNASSIGNED-division_7-0" in rolled.json()["opened_season_ids"]
        assert rolled.json()["idle_club_ids"] == ["dog"]

    with session_factory() as session:
        levels = dict(session.execute(select(OwnerClubState.club_id, OwnerClubState.division_level)).all())
    assert levels == {
        "ape": "division_7",
        "bear": "division_7",
        "cat": "division_7",
        "dog": "foundation",
    }
