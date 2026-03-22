from __future__ import annotations

from datetime import datetime, timezone

from app.common.enums.fixture_window import FixtureWindow
from app.world_super_cup.services.calendar import WorldSuperCupCalendarService
from app.world_super_cup.services.tournament import WorldSuperCupService


def test_world_super_cup_schedule_packs_into_three_days() -> None:
    plan = WorldSuperCupService().build_demo_tournament(datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc))

    kickoff_times = [match.kickoff_at for match in plan.qualification.playoff_matches]
    kickoff_times.extend(match.kickoff_at for match in plan.group_stage.matches)
    for knockout_round in plan.knockout.rounds:
        kickoff_times.extend(match.kickoff_at for match in knockout_round.matches)

    unique_days = {kickoff.date() for kickoff in kickoff_times}
    assert 2 <= len(unique_days) <= 3

    earliest = min(kickoff_times)
    latest = max(kickoff_times)
    assert (latest.date() - earliest.date()).days <= 2


def test_world_super_cup_calendar_uses_shared_scheduler_for_three_day_window() -> None:
    calendar = WorldSuperCupCalendarService()
    plan = calendar.build_schedule_plan(datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc))

    assert len(plan.assignments) == 3
    assert len(plan.reservations) == 3
    assert all(assignment.windows == FixtureWindow.senior_windows() for assignment in plan.assignments)
    assert plan.assignments[0].exclusive is True
