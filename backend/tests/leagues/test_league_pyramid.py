from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.competitions.models.league_events import LeagueClubHeldEvent, LeagueFixtureCompletedEvent
from app.leagues.models import LeagueClub, LeagueMatchResult
from app.leagues.pyramid import (
    DIVISION_LADDER,
    PyramidClub,
    child_level,
    next_division_level,
    parent_level,
    plan_division_cohorts,
)
from app.leagues.repository import DatabaseLeagueEventRepository, InMemoryLeagueEventRepository, LeagueEventRecord
from app.models.base import Base
from app.leagues.service import LeagueSeasonLifecycleService, LeagueValidationError


def test_regional_pyramid_splits_full_divisions_and_leaves_one_club_idle():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    nigeria = [
        PyramidClub(club_id=f"ng-{index:02d}", club_name=f"Nigeria {index}", region_code="CAF")
        for index in range(21)
    ]
    europe = [
        PyramidClub(
            club_id="eu-1",
            club_name="Europe One",
            division_level="division_1",
            region_code="UEFA",
        ),
        PyramidClub(
            club_id="eu-2",
            club_name="Europe Two",
            division_level="division_1",
            region_code="UEFA",
        ),
    ]
    seasons, idle = service.open_regional_seasons(
        clubs=[*nigeria, *europe],
        season_start=date(2026, 8, 1),
        season_label="2030",
    )

    by_key = {(season.region_code, season.division_level, season.cohort_index): season for season in seasons}
    foundation = by_key[("CAF", "foundation", 0)]
    top = by_key[("UEFA", "division_1", 0)]
    assert len(seasons) == 2
    assert len(foundation.clubs) == 20
    assert foundation.scheduled_matches_per_club == 19
    assert foundation.buy_in_tier == 0
    assert top.buy_in_tier == 0
    assert foundation.prize_pool.total_pool == 500
    assert top.prize_pool.total_pool == 4000
    assert top.scheduled_matches_per_club == 2
    assert top.division_level == "division_1"
    assert [club.club_id for cohort in idle for club in cohort.clubs] == ["ng-20"]
    assert idle[0].parent_level == "division_7"


def test_one_season_stays_in_one_division_and_entry_is_free():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    clubs = (
        LeagueClub(club_id="foundation-club", club_name="Foundation"),
        LeagueClub(club_id="top-club", club_name="Top"),
    )
    with pytest.raises(LeagueValidationError, match="one division"):
        service.register_season(
            buy_in_tier=1000,
            season_start=date(2026, 8, 1),
            clubs=clubs,
            club_divisions={"foundation-club": "foundation", "top-club": "division_1"},
        )
    season = service.register_season(
        buy_in_tier=1000,
        season_start=date(2026, 8, 1),
        clubs=clubs,
        division_level="foundation",
        club_divisions={"foundation-club": "division_1", "top-club": "division_1"},
    )
    assert season.buy_in_tier == 0
    assert season.division_level == "division_1"
    assert season.prize_pool.total_pool == 4000


def test_finished_foundation_season_feeds_the_division_above():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    clubs = [
        PyramidClub(club_id="ape", club_name="Ape", region_code="CAF"),
        PyramidClub(club_id="bear", club_name="Bear", region_code="CAF"),
        PyramidClub(club_id="cat", club_name="Cat", region_code="CAF"),
        PyramidClub(club_id="dog", club_name="Dog", region_code="CAF"),
    ]
    seasons, idle = service.open_regional_seasons(
        clubs=clubs,
        season_start=date(2026, 8, 1),
        season_label="2030",
    )
    assert idle == ()
    season = seasons[0]
    for fixture in season.fixtures:
        if fixture.home_club_id == "ape":
            home_goals, away_goals = 1, 0
        elif fixture.away_club_id == "ape":
            home_goals, away_goals = 0, 1
        else:
            home_goals, away_goals = 0, 0
        service.record_fixture_result(
            season_id=season.season_id,
            fixture_id=fixture.fixture_id,
            home_goals=home_goals,
            away_goals=away_goals,
        )

    rolled = service.rollover_regional_seasons(seasons)
    by_id = {club.club_id: club.division_level for club in rolled}
    assert by_id == {
        "ape": "division_7",
        "bear": "division_7",
        "cat": "division_7",
        "dog": "foundation",
    }
    next_seasons, next_idle = service.open_regional_seasons(
        clubs=rolled,
        season_start=date(2027, 8, 1),
        season_label="2031",
    )
    assert [club.club_id for season in next_seasons for club in season.clubs] == ["ape", "bear", "cat"]
    assert next_seasons[0].division_level == "division_7"
    assert next_seasons[0].buy_in_tier == 0
    assert next_seasons[0].scheduled_matches_per_club == 2
    assert [club.club_id for cohort in next_idle for club in cohort.clubs] == ["dog"]


def _play(service, season, *, winner: str | None = None, loser: str | None = None) -> None:
    for fixture in season.fixtures:
        home = fixture.home_club_id
        away = fixture.away_club_id
        if winner in {home, away}:
            home_goals, away_goals = (1, 0) if home == winner else (0, 1)
        elif loser in {home, away}:
            home_goals, away_goals = (0, 1) if home == loser else (1, 0)
        else:
            home_goals, away_goals = 0, 0
        service.record_fixture_result(
            season_id=season.season_id,
            fixture_id=fixture.fixture_id,
            home_goals=home_goals,
            away_goals=away_goals,
        )


def test_relegated_club_meets_the_club_left_waiting_in_foundation():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    clubs = [
        PyramidClub(club_id="ape", club_name="Ape", region_code="CAF"),
        PyramidClub(club_id="bear", club_name="Bear", region_code="CAF"),
        PyramidClub(club_id="cat", club_name="Cat", region_code="CAF"),
        PyramidClub(club_id="dog", club_name="Dog", region_code="CAF"),
        PyramidClub(club_id="elk", club_name="Elk", division_level="division_7", region_code="CAF"),
        PyramidClub(club_id="fox", club_name="Fox", division_level="division_7", region_code="CAF"),
        PyramidClub(club_id="goat", club_name="Goat", division_level="division_7", region_code="CAF"),
        PyramidClub(club_id="hog", club_name="Hog", division_level="division_7", region_code="CAF"),
    ]
    seasons, idle = service.open_regional_seasons(
        clubs=clubs,
        season_start=date(2026, 8, 1),
        season_label="2030",
    )
    assert idle == ()
    by_level = {season.division_level: season for season in seasons}
    _play(service, by_level["foundation"], winner="ape")
    _play(service, by_level["division_7"], loser="hog")

    opened, still_idle = service.open_next_regional_seasons(
        seasons,
        season_start=date(2027, 8, 1),
        season_label="2031",
    )
    by_level = {season.division_level: season for season in opened}
    assert still_idle == ()
    assert [club.club_id for club in by_level["foundation"].clubs] == ["dog", "hog"]
    assert by_level["foundation"].scheduled_matches_per_club == 1
    assert [club.club_id for club in by_level["division_7"].clubs] == ["ape", "bear", "cat"]
    assert [club.club_id for club in by_level["division_6"].clubs] == ["elk", "fox", "goat"]
    assert by_level["division_6"].buy_in_tier == 0
    assert by_level["division_6"].prize_pool.total_pool == 800
    assert by_level["division_6"].scheduled_matches_per_club == 4


def test_idle_club_is_remembered_for_the_following_season():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    clubs = [
        PyramidClub(club_id="ape", club_name="Ape", region_code="CAF"),
        PyramidClub(club_id="bear", club_name="Bear", region_code="CAF"),
        PyramidClub(club_id="cat", club_name="Cat", region_code="CAF"),
        PyramidClub(club_id="dog", club_name="Dog", region_code="CAF"),
    ]
    seasons, _idle = service.open_regional_seasons(
        clubs=clubs,
        season_start=date(2026, 8, 1),
        season_label="2030",
    )
    _play(service, seasons[0], winner="ape")
    opened, waiting = service.open_next_regional_seasons(
        seasons,
        season_start=date(2027, 8, 1),
        season_label="2031",
    )
    assert [club.club_id for cohort in waiting for club in cohort.clubs] == ["dog"]
    _play(service, opened[0])
    _opened_again, waiting_again = service.open_next_regional_seasons(
        opened,
        season_start=date(2028, 8, 1),
        season_label="2032",
    )
    assert [club.club_id for cohort in waiting_again for club in cohort.clubs] == ["dog"]
    assert all(club.club_id != "dog" for season in _opened_again for club in season.clubs)


def test_finished_table_promotes_the_top_three_only():
    assert next_division_level("foundation", final_position=1, field_size=20) == "division_7"
    assert next_division_level("foundation", final_position=4, field_size=20) == "foundation"
    assert next_division_level("foundation", final_position=20, field_size=20) == "foundation"
    assert next_division_level("division_7", final_position=20, field_size=20) == "foundation"
    assert next_division_level("division_1", final_position=1, field_size=20) == "division_1"
    cohorts = plan_division_cohorts(
        [PyramidClub(club_id="a", club_name="A", region_code="caf"), PyramidClub(club_id="b", club_name="B")]
    )
    assert cohorts[0].region_code == "CAF"
    assert cohorts[0].parent_level == "division_7"
    assert cohorts[0].child_level is None


def test_single_club_is_remembered_with_an_idle_result_and_stays():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    seasons, idle = service.open_regional_seasons(
        clubs=[PyramidClub(club_id="solo", club_name="Solo", region_code="CAF")],
        season_start=date(2026, 8, 1),
        season_label="2030",
    )
    assert seasons == ()
    assert [club.club_id for cohort in idle for club in cohort.clubs] == ["solo"]
    held = [
        event
        for event in service.repository.list_events("pyramid-idle-2030")
        if isinstance(event, LeagueClubHeldEvent)
    ]
    assert [event.club_id for event in held] == ["solo"]
    assert held[0].division_level == "foundation"

    hold = service.get_season_state("2030-CAF-foundation-idle-0")
    results = [
        event
        for event in service.repository.list_events(hold.season_id)
        if isinstance(event, LeagueFixtureCompletedEvent)
    ]
    assert hold.status == "completed"
    assert hold.idle_result == LeagueMatchResult(home_goals=0, away_goals=0)
    assert len(results) == 1
    assert hold.fixtures == ()
    assert hold.division_level == "foundation"

    opened, still_idle = service.open_next_regional_seasons(
        [hold],
        season_start=date(2027, 8, 1),
        season_label="2031",
    )
    assert opened == ()
    assert [club.club_id for cohort in still_idle for club in cohort.clubs] == ["solo"]
    assert still_idle[0].division_level == "foundation"
    assert still_idle[0].clubs[0].division_level == "foundation"


def test_opening_one_foundation_cohort_records_the_regional_ladder():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    clubs = [
        PyramidClub(club_id="ape", club_name="Ape", region_code="CAF"),
        PyramidClub(club_id="bear", club_name="Bear", region_code="CAF"),
    ]
    seasons, idle = service.open_regional_seasons(
        clubs=clubs,
        season_start=date(2026, 8, 1),
        season_label="2030",
    )
    assert idle == ()
    assert len(seasons) == 1
    assert seasons[0].division_level == "foundation"
    assert seasons[0].total_fixture_count > 0

    chain = service.region_division_chain("CAF")
    assert [event.division_level for event in chain] == list(DIVISION_LADDER)
    for event in chain:
        assert event.region_code == "CAF"
        assert event.parent_level == parent_level(event.division_level)
        assert event.child_level == child_level(event.division_level)
        if event.division_level == "foundation":
            continue
        assert service.repository.list_events(f"2030-CAF-{event.division_level}-0") == ()

    service.open_regional_seasons(
        clubs=clubs,
        season_start=date(2027, 8, 1),
        season_label="2031",
    )
    assert len(service.region_division_chain("CAF")) == 8


def test_region_ladder_and_idle_result_round_trip_in_sqlite() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[LeagueEventRecord.__table__])
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    service = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(session_local))
    service.open_regional_seasons(
        clubs=[PyramidClub(club_id="solo", club_name="Solo", region_code="CAF")],
        season_start=date(2026, 8, 1),
        season_label="2030",
    )

    reread = LeagueSeasonLifecycleService(repository=DatabaseLeagueEventRepository(session_local))
    chain = reread.region_division_chain("caf")
    assert [event.division_level for event in chain] == list(DIVISION_LADDER)
    assert chain[0].parent_level == "division_7"
    assert chain[0].child_level is None
    assert chain[-1].parent_level is None
    assert chain[-1].child_level == "division_2"
    hold = reread.get_season_state("2030-CAF-foundation-idle-0")
    assert hold.status == "completed"
    assert hold.idle_result == LeagueMatchResult(home_goals=0, away_goals=0)
    assert hold.division_level == "foundation"
    assert hold.fixtures == ()
    engine.dispose()
