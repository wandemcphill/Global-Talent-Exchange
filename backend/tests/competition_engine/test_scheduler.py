from __future__ import annotations

from datetime import date

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.schemas.competition import CompetitionScheduleRequest
from app.competition_engine.scheduler import CompetitionScheduler


def test_scheduler_prevents_senior_window_collisions_between_competitions() -> None:
    scheduler = CompetitionScheduler()
    scheduled_day = date(2026, 4, 1)

    plan = scheduler.build_schedule(
        (
            CompetitionScheduleRequest(
                competition_id="league-alpha",
                competition_type=CompetitionType.LEAGUE,
                requested_dates=(scheduled_day,),
                preferred_windows=(FixtureWindow.SENIOR_1,),
                priority=10,
            ),
            CompetitionScheduleRequest(
                competition_id="league-beta",
                competition_type=CompetitionType.LEAGUE,
                requested_dates=(scheduled_day,),
                preferred_windows=(FixtureWindow.SENIOR_1, FixtureWindow.SENIOR_2),
                priority=20,
            ),
        )
    )

    assignments = {assignment.competition_id: assignment for assignment in plan.assignments}
    assert assignments["league-alpha"].windows == (FixtureWindow.SENIOR_1,)
    assert assignments["league-beta"].windows == (FixtureWindow.SENIOR_2,)


def test_world_super_cup_pauses_senior_competitions_but_not_academy_or_fast_cups() -> None:
    scheduler = CompetitionScheduler()
    scheduled_day = date(2026, 6, 12)

    plan = scheduler.build_schedule(
        (
            CompetitionScheduleRequest(
                competition_id="wsc",
                competition_type=CompetitionType.WORLD_SUPER_CUP,
                requested_dates=(scheduled_day,),
                priority=0,
                requires_exclusive_windows=True,
            ),
            CompetitionScheduleRequest(
                competition_id="league-alpha",
                competition_type=CompetitionType.LEAGUE,
                requested_dates=(scheduled_day,),
            ),
            CompetitionScheduleRequest(
                competition_id="ucl",
                competition_type=CompetitionType.CHAMPIONS_LEAGUE,
                requested_dates=(scheduled_day,),
            ),
            CompetitionScheduleRequest(
                competition_id="academy-alpha",
                competition_type=CompetitionType.ACADEMY,
                requested_dates=(scheduled_day,),
            ),
            CompetitionScheduleRequest(
                competition_id="fast-cup-alpha",
                competition_type=CompetitionType.FAST_CUP,
                requested_dates=(scheduled_day,),
            ),
        )
    )

    paused_ids = {entry.competition_id for entry in plan.paused_competitions}
    assert paused_ids == {"league-alpha", "ucl"}

    world_super_cup_reservation = next(
        reservation
        for reservation in plan.reservations
        if reservation.competition_id == "wsc"
    )
    assert world_super_cup_reservation.windows == FixtureWindow.senior_windows()

    assignments = {assignment.competition_id: assignment for assignment in plan.assignments}
    assert assignments["academy-alpha"].windows == (FixtureWindow.ACADEMY_OPEN,)
    assert assignments["fast-cup-alpha"].windows == (FixtureWindow.FAST_CUP_OPEN,)


def test_academy_requests_expand_into_shared_open_window_slot_sequences() -> None:
    scheduler = CompetitionScheduler()
    scheduled_day = date(2026, 4, 3)

    plan = scheduler.build_schedule(
        (
            CompetitionScheduleRequest(
                competition_id="academy-alpha",
                competition_type=CompetitionType.ACADEMY,
                requested_dates=(scheduled_day,),
                required_windows=4,
            ),
        )
    )

    assignment = plan.assignments[0]
    assert assignment.windows == (FixtureWindow.ACADEMY_OPEN,)
    assert assignment.slot_sequences == (1, 2, 3, 4)
