from __future__ import annotations

from datetime import date

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.replay_visibility import ReplayVisibility
from app.common.schemas.competition import CompetitionDispatchRequest, CompetitionScheduleRequest, ScheduledFixture
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.queue_contracts import InMemoryQueuePublisher
from app.competition_engine.scheduler import CompetitionScheduler, CompetitionWindowResolver


def test_window_resolver_cycles_senior_windows_into_follow_up_slot_sequences() -> None:
    scheduler = CompetitionScheduler()
    match_date = date(2026, 8, 1)
    plan = scheduler.build_schedule(
        (
            CompetitionScheduleRequest(
                competition_id="ucl-2026",
                competition_type=CompetitionType.CHAMPIONS_LEAGUE,
                requested_dates=(match_date,),
                required_windows=len(FixtureWindow.senior_windows()),
            ),
        )
    )

    resolver = CompetitionWindowResolver.from_plan(plan, competition_id="ucl-2026")

    assert resolver.slot_for(match_date, 0) == (FixtureWindow.SENIOR_1, 1)
    assert resolver.slot_for(match_date, 5) == (FixtureWindow.SENIOR_6, 1)
    assert resolver.slot_for(match_date, 6) == (FixtureWindow.SENIOR_1, 2)
    assert resolver.slot_for(match_date, 7) == (FixtureWindow.SENIOR_2, 2)


def test_match_dispatcher_dispatch_requests_batches_shared_contracts() -> None:
    publisher = InMemoryQueuePublisher()
    dispatcher = MatchDispatcher(queue_publisher=publisher)
    fixture = ScheduledFixture(
        fixture_id="fixture-1",
        competition_id="academy-2026",
        competition_type=CompetitionType.ACADEMY,
        round_number=3,
        home_club_id="club-1",
        away_club_id="club-2",
        match_date=date(2026, 8, 2),
        window=FixtureWindow.ACADEMY_OPEN,
        slot_sequence=4,
        replay_visibility=ReplayVisibility.COMPETITION,
    )

    records = dispatcher.dispatch_requests(
        (
            CompetitionDispatchRequest(
                fixture=fixture,
                season_id="academy-2026",
                competition_name="Academy Competition",
                stage_name="league_round",
                home_club_name="Club 1",
                away_club_name="Club 2",
            ),
        )
    )

    assert len(records) == 1
    assert records[0].payload["competition_name"] == "Academy Competition"
    assert records[0].payload["stage_name"] == "league_round"
    assert records[0].payload["slot_sequence"] == 4
    assert len(publisher.list_published("match_simulation")) == 1
