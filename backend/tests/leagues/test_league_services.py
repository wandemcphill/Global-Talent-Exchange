from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.config.competition_constants import LEAGUE_GROUP_SIZE, LEAGUE_MATCHES_PER_CLUB, LEAGUE_MATCH_WINDOWS_PER_DAY
from backend.app.competition_engine import MatchDispatcher
from backend.app.competition_engine.queue_contracts import InMemoryQueuePublisher
from backend.app.competitions.models.league_events import (
    LeagueFixtureCompletedEvent,
    LeagueRegisteredClubEventData,
    LeagueSeasonRegisteredEvent,
)
from backend.app.leagues.models import LeagueClub, LeaguePlayerContribution, LeagueStandingRow
from backend.app.leagues.prizes import LeaguePrizeService
from backend.app.leagues.qualification import LeagueQualificationService
from backend.app.leagues.repository import DatabaseLeagueEventRepository, InMemoryLeagueEventRepository, LeagueEventRecord
from backend.app.leagues.service import LeagueSeasonLifecycleService
from backend.app.models.base import Base


def _clubs(count: int) -> tuple[LeagueClub, ...]:
    return tuple(
        LeagueClub(
            club_id=f"club-{index:02d}",
            club_name=f"Club {index:02d}",
            strength_rating=100 - index,
        )
        for index in range(1, count + 1)
    )


def _sample_standings() -> tuple[LeagueStandingRow, ...]:
    return tuple(
        LeagueStandingRow(
            position=index,
            club_id=f"club-{index}",
            club_name=f"Club {index}",
            played=38,
            wins=max(0, 20 - index),
            draws=index % 3,
            losses=index,
            goals_for=60 - index,
            goals_against=20 + index,
            goal_difference=(60 - index) - (20 + index),
            points=80 - (index * 3),
        )
        for index in range(1, 7)
    )


def test_twenty_team_fixture_generation_has_full_home_and_away_integrity() -> None:
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    season = service.register_season(
        season_id="league-20",
        buy_in_tier=1000,
        season_start=date(2026, 3, 11),
        clubs=_clubs(LEAGUE_GROUP_SIZE),
    )

    fixtures = season.fixtures
    assert len(fixtures) == 380

    club_match_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    home_away_pairs: Counter[tuple[str, str]] = Counter()
    clubs_per_round: defaultdict[int, set[str]] = defaultdict(set)
    for fixture in fixtures:
        club_match_counts[fixture.home_club_id] += 1
        club_match_counts[fixture.away_club_id] += 1
        pair_counts[tuple(sorted((fixture.home_club_id, fixture.away_club_id)))] += 1
        home_away_pairs[(fixture.home_club_id, fixture.away_club_id)] += 1
        assert fixture.home_club_id not in clubs_per_round[fixture.round_number]
        assert fixture.away_club_id not in clubs_per_round[fixture.round_number]
        clubs_per_round[fixture.round_number].add(fixture.home_club_id)
        clubs_per_round[fixture.round_number].add(fixture.away_club_id)

    assert set(club_match_counts.values()) == {LEAGUE_MATCHES_PER_CLUB}
    assert set(pair_counts.values()) == {2}
    for home_club_id, away_club_id in list(home_away_pairs):
        assert home_away_pairs[(home_club_id, away_club_id)] == 1
        assert home_away_pairs[(away_club_id, home_club_id)] == 1


def test_schedule_uses_six_windows_per_day_and_finishes_inside_seven_days() -> None:
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    season = service.register_season(
        season_id="league-schedule",
        buy_in_tier=500,
        season_start=date(2026, 3, 11),
        clubs=_clubs(LEAGUE_GROUP_SIZE),
    )

    windows_by_day: defaultdict[int, set[int]] = defaultdict(set)
    for fixture in season.fixtures:
        windows_by_day[fixture.day_number].add(fixture.window_number)

    assert season.scheduled_matches_per_club == LEAGUE_MATCHES_PER_CLUB
    assert max(windows_by_day) <= 7
    assert all(len(windows) <= LEAGUE_MATCH_WINDOWS_PER_DAY for windows in windows_by_day.values())
    assert len({fixture.round_number for fixture in season.fixtures}) == LEAGUE_MATCHES_PER_CLUB


def test_top_four_rollover_passes_slot_to_next_ranked_club() -> None:
    service = LeagueQualificationService()
    standings = _sample_standings()

    auto_entries = service.build_auto_entry_slots(
        standings,
        opted_out_club_ids={"club-2", "club-4"},
    )

    assert [slot.club_id for slot in auto_entries] == ["club-1", "club-3", "club-5", "club-6"]
    assert auto_entries[2].rolled_over is True
    assert auto_entries[3].rolled_over is True


def test_pool_splits_follow_configured_distribution() -> None:
    prize_service = LeaguePrizeService()
    standings = _sample_standings()

    prize_pool, champion_prize, top_scorer_award, top_assist_award = prize_service.calculate(
        buy_in_tier=1000,
        club_count=20,
        standings=standings,
        player_contributions=(
            LeaguePlayerContribution(player_id="p1", player_name="Striker 1", club_id="club-1", goals=12, assists=4),
            LeaguePlayerContribution(player_id="p2", player_name="Creator 1", club_id="club-2", goals=8, assists=10),
        ),
    )

    assert prize_pool.total_pool == pytest.approx(20_000.0)
    assert prize_pool.winner_prize == pytest.approx(10_000.0)
    assert prize_pool.top_scorer_prize == pytest.approx(2_000.0)
    assert prize_pool.top_assist_prize == pytest.approx(1_000.0)
    assert prize_pool.champions_league_fund == pytest.approx(7_000.0)
    assert champion_prize is not None
    assert champion_prize.club_id == "club-1"
    assert top_scorer_award.winners[0].split_amount == pytest.approx(2_000.0)
    assert top_assist_award.winners[0].split_amount == pytest.approx(1_000.0)


def test_top_scorer_and_assist_ties_split_evenly() -> None:
    prize_service = LeaguePrizeService()
    standings = _sample_standings()

    _, _, top_scorer_award, top_assist_award = prize_service.calculate(
        buy_in_tier=300,
        club_count=20,
        standings=standings,
        player_contributions=(
            LeaguePlayerContribution(player_id="p1", player_name="Finisher 1", club_id="club-1", goals=10, assists=4),
            LeaguePlayerContribution(player_id="p2", player_name="Finisher 2", club_id="club-2", goals=10, assists=3),
            LeaguePlayerContribution(player_id="p3", player_name="Creator 1", club_id="club-3", goals=2, assists=9),
            LeaguePlayerContribution(player_id="p4", player_name="Creator 2", club_id="club-4", goals=1, assists=9),
        ),
    )

    assert len(top_scorer_award.winners) == 2
    assert len(top_assist_award.winners) == 2
    assert all(winner.split_amount == pytest.approx(300.0) for winner in top_scorer_award.winners)
    assert all(winner.split_amount == pytest.approx(150.0) for winner in top_assist_award.winners)


def test_minimum_size_fallback_creates_valid_short_group_schedule() -> None:
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    season = service.register_season(
        season_id="league-small",
        buy_in_tier=25,
        season_start=date(2026, 3, 11),
        clubs=_clubs(6),
    )

    assert season.group_is_full is False
    assert season.group_size_target == LEAGUE_GROUP_SIZE
    assert season.scheduled_matches_per_club == 10
    assert season.target_matches_per_club == LEAGUE_MATCHES_PER_CLUB
    assert len(season.fixtures) == 30


def test_league_dispatch_jobs_use_shared_window_and_queue_contracts() -> None:
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    season = service.register_season(
        season_id="league-dispatch",
        buy_in_tier=300,
        season_start=date(2026, 3, 11),
        clubs=_clubs(6),
    )

    publisher = InMemoryQueuePublisher()
    jobs = service.build_match_dispatch_jobs(
        season_id=season.season_id,
        dispatcher=MatchDispatcher(queue_publisher=publisher),
    )

    assert len(jobs) == len(season.fixtures)
    assert jobs[0].payload["competition_type"] == "league"
    assert jobs[0].payload["window"] == "senior_1"
    assert jobs[0].payload["stage_name"] == "league_round"


def test_standings_sort_points_goal_difference_and_goals_for() -> None:
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    clubs = (
        LeagueClub(club_id="club-a", club_name="Club A"),
        LeagueClub(club_id="club-b", club_name="Club B"),
        LeagueClub(club_id="club-c", club_name="Club C"),
        LeagueClub(club_id="club-d", club_name="Club D"),
    )
    season = service.register_season(
        season_id="league-table",
        buy_in_tier=150,
        season_start=date(2026, 3, 11),
        clubs=clubs,
    )

    fixture_map = {fixture.fixture_id: fixture for fixture in season.fixtures}
    fixtures_to_finish = (
        (next(fixture_id for fixture_id, fixture in fixture_map.items() if fixture.home_club_id == "club-a" and fixture.away_club_id == "club-b"), 2, 0),
        (next(fixture_id for fixture_id, fixture in fixture_map.items() if fixture.home_club_id == "club-c" and fixture.away_club_id == "club-d"), 1, 0),
        (next(fixture_id for fixture_id, fixture in fixture_map.items() if fixture.home_club_id == "club-a" and fixture.away_club_id == "club-c"), 1, 0),
        (next(fixture_id for fixture_id, fixture in fixture_map.items() if fixture.home_club_id == "club-b" and fixture.away_club_id == "club-d"), 2, 0),
    )
    for fixture_id, home_goals, away_goals in fixtures_to_finish:
        service.record_fixture_result(
            season_id="league-table",
            fixture_id=fixture_id,
            home_goals=home_goals,
            away_goals=away_goals,
        )

    updated = service.get_season_state("league-table")
    assert [row.club_id for row in updated.standings[:2]] == ["club-a", "club-b"]


def test_database_repository_round_trips_league_events() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[LeagueEventRecord.__table__])
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    repository = DatabaseLeagueEventRepository(session_local)

    registered = LeagueSeasonRegisteredEvent(
        season_id="league-persisted",
        buy_in_tier=500,
        season_start=date(2026, 3, 11),
        registered_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        clubs=(
            LeagueRegisteredClubEventData(
                club_id="club-1",
                club_name="Club 1",
                strength_rating=90,
            ),
        ),
    )
    completed = LeagueFixtureCompletedEvent(
        season_id="league-persisted",
        fixture_id="fixture-1",
        home_goals=2,
        away_goals=1,
        recorded_at=datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc),
    )

    repository.append(registered)
    repository.append(completed)
    events = repository.list_events("league-persisted")

    assert len(events) == 2
    assert isinstance(events[0], LeagueSeasonRegisteredEvent)
    assert isinstance(events[1], LeagueFixtureCompletedEvent)
    assert events[0].clubs[0].club_id == "club-1"
    assert events[1].fixture_id == "fixture-1"

    engine.dispose()
