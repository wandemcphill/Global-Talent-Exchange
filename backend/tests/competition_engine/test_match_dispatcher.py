from __future__ import annotations

from datetime import date

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.replay_visibility import ReplayVisibility
from backend.app.common.schemas.competition import ScheduledFixture
from backend.app.competition_engine.match_dispatcher import MatchDispatchContext, MatchDispatcher
from backend.app.competition_engine.queue_contracts import InMemoryQueuePublisher


def test_match_dispatcher_publishes_queue_jobs_instead_of_running_inline() -> None:
    publisher = InMemoryQueuePublisher()
    dispatcher = MatchDispatcher(queue_publisher=publisher)
    fixture = ScheduledFixture(
        fixture_id="fixture-10",
        competition_id="cup-final",
        competition_type=CompetitionType.FAST_CUP,
        round_number=4,
        home_club_id="club-1",
        away_club_id="club-2",
        match_date=date(2026, 7, 8),
        window=FixtureWindow.FAST_CUP_OPEN,
        replay_visibility=ReplayVisibility.PUBLIC,
        is_cup_match=True,
        allow_penalties=True,
    )

    first = dispatcher.dispatch_match_simulation(fixture, is_final=True)
    second = dispatcher.dispatch_match_simulation(fixture, is_final=True)

    assert first.queue_name == "match_simulation"
    assert first.idempotency_key == second.idempotency_key
    assert len(publisher.list_published("match_simulation")) == 1


def test_match_dispatcher_batches_fixture_context_overrides() -> None:
    publisher = InMemoryQueuePublisher()
    dispatcher = MatchDispatcher(queue_publisher=publisher)
    fixtures = (
        ScheduledFixture(
            fixture_id="academy-1",
            competition_id="academy-season",
            competition_type=CompetitionType.ACADEMY,
            round_number=1,
            home_club_id="club-1",
            away_club_id="club-2",
            match_date=date(2026, 7, 8),
            window=FixtureWindow.ACADEMY_OPEN,
            slot_sequence=3,
        ),
    )

    records = dispatcher.dispatch_match_simulations(
        fixtures,
        fixture_context_by_id={
            "academy-1": MatchDispatchContext(
                season_id="academy-season",
                competition_name="academy",
                stage_name="academy_league",
                home_club_name="Club 1",
                away_club_name="Club 2",
            )
        },
    )

    assert len(records) == 1
    assert records[0].payload["slot_sequence"] == 3
    assert records[0].payload["stage_name"] == "academy_league"
