from __future__ import annotations

from datetime import datetime, timezone

from app.common.enums.fixture_window import FixtureWindow
from app.world_super_cup.services.competition_engine import WorldSuperCupCompetitionEngineService
from app.world_super_cup.services.tournament import WorldSuperCupService


def test_world_super_cup_competition_engine_builds_shared_dispatch_batch() -> None:
    plan = WorldSuperCupService().build_demo_tournament(datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc))

    batch = WorldSuperCupCompetitionEngineService().build_batch(plan, season_id="wsc-2026")

    total_matches = len(plan.qualification.playoff_matches)
    total_matches += len(plan.group_stage.matches)
    total_matches += sum(len(round_entry.matches) for round_entry in plan.knockout.rounds)

    assert len(batch.fixtures) == total_matches
    assert batch.schedule_plan.reservations
    assert batch.fixtures[0].window in FixtureWindow.senior_windows()
    assert max(fixture.slot_sequence for fixture in batch.fixtures) >= 2
