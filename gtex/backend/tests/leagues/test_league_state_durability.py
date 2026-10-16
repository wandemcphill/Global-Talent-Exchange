"""League season state must outlive a single application instance.

The lifecycle service is event-sourced, but the router used to build it over a
module-level ``InMemoryLeagueEventRepository``: a per-process dict. Every season
vanished on restart, and two web workers each held their own divergent copy.
These tests pin the durable wiring at the HTTP boundary -- two independent
FastAPI instances over one database must agree -- and pin the fallback that
keeps standalone/unit use working when no database is wired.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.competitions.models.league_events import LeagueFixtureCompletedEvent
from app.leagues.models import LeagueClub
from app.leagues.repository import (
    DatabaseLeagueEventRepository,
    InMemoryLeagueEventRepository,
    LeagueEventRecord,
    build_league_event_repository,
    get_league_event_repository,
)
from app.leagues.router import router
from app.leagues.service import LeagueSeasonLifecycleService, LeagueSeasonNotFoundError

ORGANISER = SimpleNamespace(id="league-organiser")


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    LeagueEventRecord.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def concurrent_session_factory(tmp_path):
    """A file-backed database so each thread gets its own real connection.

    The shared-connection in-memory fixture cannot model concurrency: every
    session would ride one DBAPI connection and serialise by accident.
    """
    database_path = (tmp_path / "league-events.db").as_posix()
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    LeagueEventRecord.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def _clubs() -> tuple[LeagueClub, ...]:
    return tuple(
        LeagueClub(club_id=f"club-{index}", club_name=f"Club {index}", strength_rating=90 - index)
        for index in range(1, 5)
    )


def _build_instance(session_factory) -> FastAPI:
    """A fresh application instance, as a second worker or a restart would be."""
    app = FastAPI()
    app.include_router(router)
    app.state.session_factory = session_factory
    app.dependency_overrides[get_current_user] = lambda: ORGANISER
    return app


def _registration_payload(season_id: str) -> dict[str, object]:
    return {
        "season_id": season_id,
        "buy_in_tier": 500,
        "season_start": str(date(2026, 3, 11)),
        "clubs": [
            {"club_id": f"club-{index}", "club_name": f"Club {index}", "strength_rating": 90 - index}
            for index in range(1, 5)
        ],
    }


def test_router_wires_the_database_repository_when_a_session_factory_exists(session_factory) -> None:
    app = _build_instance(session_factory)
    with TestClient(app) as client:
        assert client.post("/api/leagues/register", json=_registration_payload("wired")).status_code == 201

    repository = build_league_event_repository(session_factory)
    assert isinstance(repository, DatabaseLeagueEventRepository)
    assert len(repository.list_events("wired")) == 1


def test_state_written_by_one_instance_is_visible_to_another(session_factory) -> None:
    writer = _build_instance(session_factory)
    with TestClient(writer) as client:
        created = client.post("/api/leagues/register", json=_registration_payload("shared"))
    assert created.status_code == 201

    # A completely separate application object -- a second worker, or the same
    # service after a restart. It shares only the database.
    reader = _build_instance(session_factory)
    with TestClient(reader) as client:
        summary = client.get("/api/leagues/shared/summary")

    assert summary.status_code == 200
    assert summary.json()["season_id"] == "shared"
    assert summary.json()["registered_club_count"] == 4


def test_state_survives_disposal_of_the_writing_instance(session_factory) -> None:
    writer = _build_instance(session_factory)
    with TestClient(writer) as client:
        client.post("/api/leagues/register", json=_registration_payload("restart"))
    del writer

    survivor = _build_instance(session_factory)
    with TestClient(survivor) as client:
        standings = client.get("/api/leagues/restart/standings")

    assert standings.status_code == 200
    assert len(standings.json()["rows"]) == 4


def test_a_fixture_result_recorded_on_one_instance_is_read_on_another(session_factory) -> None:
    writer = _build_instance(session_factory)
    with TestClient(writer) as client:
        client.post("/api/leagues/register", json=_registration_payload("results"))
        fixtures = client.get("/api/leagues/results/fixtures").json()
    fixture_id = fixtures["fixtures"][0]["fixture_id"]

    LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(session_factory)).record_fixture_result(
        season_id="results", fixture_id=fixture_id, home_goals=3, away_goals=1
    )

    reader = _build_instance(session_factory)
    with TestClient(reader) as client:
        summary = client.get("/api/leagues/results/summary").json()

    assert summary["completed_fixture_count"] == 1
    assert summary["status"] == "in_progress"


def test_repeated_identical_fixture_results_do_not_corrupt_standings(session_factory) -> None:
    """Duplicate delivery must be absorbed by the fold, not double-counted."""
    service = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(session_factory))
    state = service.register_season(
        buy_in_tier=500,
        clubs=_clubs(),
        season_start=date(2026, 3, 11),
        season_id="idempotent",
    )
    fixture_id = state.fixtures[0].fixture_id

    for _ in range(3):
        service.record_fixture_result(season_id="idempotent", fixture_id=fixture_id, home_goals=2, away_goals=0)

    reread = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(session_factory)).get_season_state(
        "idempotent"
    )

    assert reread.completed_fixture_count == 1
    assert sum(row.played for row in reread.standings) == 2
    assert sum(row.points for row in reread.standings) == 3


def test_a_later_result_for_the_same_fixture_wins_deterministically(session_factory) -> None:
    repository = DatabaseLeagueEventRepository(session_factory)
    service = LeagueSeasonLifecycleService(repository=repository)
    state = service.register_season(
        buy_in_tier=500,
        clubs=_clubs(),
        season_start=date(2026, 3, 11),
        season_id="ordering",
    )
    fixture_id = state.fixtures[0].fixture_id

    for index, (home_goals, away_goals) in enumerate(((1, 0), (2, 2), (0, 4))):
        repository.append(
            LeagueFixtureCompletedEvent(
                season_id="ordering",
                fixture_id=fixture_id,
                home_goals=home_goals,
                away_goals=away_goals,
                recorded_at=datetime(2026, 3, 12, 10, index, tzinfo=timezone.utc),
            )
        )

    fixtures = {
        fixture.fixture_id: fixture
        for fixture in LeagueSeasonLifecycleService(repository=repository).get_season_state("ordering").fixtures
    }
    result = fixtures[fixture_id].result
    assert (result.home_goals, result.away_goals) == (0, 4)


def test_concurrent_result_writers_all_land_without_corrupting_state(concurrent_session_factory) -> None:
    factory = concurrent_session_factory
    service = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(factory))
    state = service.register_season(
        buy_in_tier=500,
        clubs=_clubs(),
        season_start=date(2026, 3, 11),
        season_id="concurrent",
    )
    fixture_ids = [fixture.fixture_id for fixture in state.fixtures[:6]]

    def record(fixture_id: str) -> None:
        LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(factory)).record_fixture_result(
            season_id="concurrent", fixture_id=fixture_id, home_goals=1, away_goals=0
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(record, fixture_ids))

    reread = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(factory)).get_season_state(
        "concurrent"
    )

    assert reread.completed_fixture_count == len(fixture_ids)
    assert sum(row.played for row in reread.standings) == 2 * len(fixture_ids)


def test_falls_back_to_the_process_local_repository_without_a_database() -> None:
    assert build_league_event_repository(None) is get_league_event_repository()


def test_falls_back_when_the_event_table_has_not_been_migrated_in() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        assert isinstance(build_league_event_repository(factory), InMemoryLeagueEventRepository)
    finally:
        engine.dispose()


def test_unknown_season_still_reports_not_found_on_the_durable_repository(session_factory) -> None:
    service = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(session_factory))
    with pytest.raises(LeagueSeasonNotFoundError):
        service.get_season_state("never-registered")
