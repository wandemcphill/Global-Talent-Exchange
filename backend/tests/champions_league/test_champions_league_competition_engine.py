from __future__ import annotations

from datetime import date

from app.champions_league.services.competition_engine import ChampionsLeagueCompetitionEngineService
from app.champions_league.services.tournament import ChampionsLeagueService
from app.common.enums.fixture_window import FixtureWindow


def test_champions_league_competition_engine_cycles_shared_windows_for_dense_playoff_day(build_candidates) -> None:
    playoff = ChampionsLeagueService().build_playoff_bracket(build_candidates())

    batch = ChampionsLeagueCompetitionEngineService().build_playoff_batch(
        competition_id="ucl-2026",
        season_id="ucl-season-2026",
        match_date=date(2026, 8, 20),
        playoff=playoff,
    )

    assert len(batch.fixtures) == 12
    assert batch.fixtures[0].window == FixtureWindow.SENIOR_1
    assert batch.fixtures[5].window == FixtureWindow.SENIOR_6
    assert batch.fixtures[6].window == FixtureWindow.SENIOR_1
    assert batch.fixtures[6].slot_sequence == 2
    assert batch.dispatch_requests[-1].season_id == "ucl-season-2026"
