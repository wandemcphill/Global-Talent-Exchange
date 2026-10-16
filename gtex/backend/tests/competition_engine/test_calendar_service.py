from __future__ import annotations

from datetime import date

import pytest

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.schemas.competition import (
    CompetitionReference,
    FixtureWindowSlot,
    LeagueFixtureRequest,
)
from app.competition_engine.calendar_service import CalendarConflictError, CalendarService
from app.config.competition_constants import LEAGUE_MATCH_WINDOWS_PER_DAY


def _fixture(*, fixture_id: str, home_club_id: str, away_club_id: str) -> LeagueFixtureRequest:
    return LeagueFixtureRequest(
        fixture_id=fixture_id,
        competition_id="league-alpha",
        competition_type=CompetitionType.LEAGUE,
        round_number=1,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
    )


def test_schedule_league_fixtures_generates_daily_calendar_without_club_collisions() -> None:
    service = CalendarService()
    competition = CompetitionReference(
        competition_id="league-alpha",
        competition_type=CompetitionType.LEAGUE,
    )
    fixtures = tuple(
        _fixture(
            fixture_id=f"fixture-{index}",
            home_club_id=f"club-{(index * 2) - 1}",
            away_club_id=f"club-{index * 2}",
        )
        for index in range(1, 11)
    )

    scheduled = service.schedule_league_fixtures(
        competition,
        match_date=date(2026, 3, 18),
        fixtures=fixtures,
    )

    assert len(scheduled) == 10
    assert len({fixture.fixture_id for fixture in scheduled}) == 10
    assert len({fixture.window for fixture in scheduled}) <= LEAGUE_MATCH_WINDOWS_PER_DAY
    assert {fixture.window for fixture in scheduled}.issubset(set(FixtureWindow.senior_windows()))
    assert scheduled[0].window is FixtureWindow.SENIOR_1
    assert scheduled[1].window is FixtureWindow.SENIOR_2


def test_detect_conflicts_rejects_same_club_in_same_window() -> None:
    service = CalendarService()
    slot = FixtureWindowSlot(match_date=date(2026, 3, 19), window=FixtureWindow.SENIOR_1)
    first = _fixture(fixture_id="fixture-a", home_club_id="club-1", away_club_id="club-2")
    second = _fixture(fixture_id="fixture-b", home_club_id="club-1", away_club_id="club-3")

    service.schedule_fixture(first, slot)
    conflicts = service.detect_conflicts(second, slot)

    assert len(conflicts) == 1
    assert conflicts[0].conflict_code == "club_double_booked"

    with pytest.raises(CalendarConflictError, match="same fixture window"):
        service.schedule_fixture(second, slot)


def test_open_window_slot_sequences_allow_distinct_sub_windows_on_same_day() -> None:
    service = CalendarService()
    first = LeagueFixtureRequest(
        fixture_id="academy-1",
        competition_id="academy-alpha",
        competition_type=CompetitionType.ACADEMY,
        round_number=1,
        home_club_id="club-1",
        away_club_id="club-2",
    )
    second = LeagueFixtureRequest(
        fixture_id="academy-2",
        competition_id="academy-alpha",
        competition_type=CompetitionType.ACADEMY,
        round_number=2,
        home_club_id="club-1",
        away_club_id="club-3",
    )

    scheduled_first = service.schedule_fixture(
        first,
        FixtureWindowSlot(
            match_date=date(2026, 3, 19),
            window=FixtureWindow.ACADEMY_OPEN,
            slot_sequence=1,
        ),
    )
    conflicts = service.detect_conflicts(
        second,
        FixtureWindowSlot(
            match_date=date(2026, 3, 19),
            window=FixtureWindow.ACADEMY_OPEN,
            slot_sequence=2,
        ),
    )

    assert scheduled_first.slot_sequence == 1
    assert conflicts == ()
