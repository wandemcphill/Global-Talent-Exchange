from __future__ import annotations

from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.fast_cups.models.domain import FastCupDivision
from backend.app.fast_cups.services.competition_engine import FastCupCompetitionEngineService


def test_fast_cup_competition_engine_batches_simulated_bracket(select_cup, fill_cup, ecosystem, base_now) -> None:
    cup = select_cup(ecosystem, now=base_now, division=FastCupDivision.SENIOR, size=32)
    filled = fill_cup(ecosystem, cup)
    bracket = ecosystem.bracket_service.simulate_bracket(filled)

    batch = FastCupCompetitionEngineService().build_batch(filled, bracket)

    assert len(batch.fixtures) == bracket.total_matches
    assert all(fixture.window == FixtureWindow.FAST_CUP_OPEN for fixture in batch.fixtures)
    assert batch.dispatch_requests[-1].is_final is True
    assert max(fixture.slot_sequence for fixture in batch.fixtures) >= 2
