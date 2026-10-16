from __future__ import annotations

from datetime import date

from app.common.enums.fixture_window import FixtureWindow
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.queue_contracts import InMemoryQueuePublisher
from app.leagues.competition_engine import LeagueCompetitionEngineService
from app.leagues.models import LeagueClub
from app.leagues.repository import InMemoryLeagueEventRepository
from app.leagues.service import LeagueSeasonLifecycleService


def test_league_competition_engine_builds_shared_schedule_batch() -> None:
    season = _build_season()

    batch = LeagueCompetitionEngineService().build_batch(season)

    assert batch.competition_id == season.season_id
    assert len(batch.fixtures) == len(season.fixtures)
    assert len(batch.dispatch_requests) == len(season.fixtures)
    assert batch.schedule_plan.assignments[0].windows[0] == FixtureWindow.SENIOR_1
    assert batch.dispatch_requests[0].scheduled_kickoff_at == season.fixtures[0].kickoff_at


def test_league_competition_engine_dispatches_shared_queue_jobs() -> None:
    season = _build_season()
    publisher = InMemoryQueuePublisher()
    service = LeagueCompetitionEngineService(
        dispatcher=MatchDispatcher(queue_publisher=publisher),
    )

    records = service.dispatch_season(season)

    assert len(records) == len(season.fixtures)
    assert records[0].payload["competition_type"] == "league"
    assert records[0].payload["stage_name"] == "league_round"


def _build_season():
    service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
    return service.register_season(
        season_id="league-engine",
        buy_in_tier=300,
        season_start=date(2026, 3, 11),
        clubs=tuple(
            LeagueClub(
                club_id=f"club-{index:02d}",
                club_name=f"Club {index:02d}",
                strength_rating=100 - index,
            )
            for index in range(1, 7)
        ),
    )
