from __future__ import annotations

from datetime import date, datetime, timezone

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.replay_visibility import ReplayVisibility
from app.competition_engine.queue_contracts import InMemoryQueuePublisher, MatchSimulationJob
from app.core.events import InMemoryEventPublisher


def test_queue_publisher_emits_broker_ready_job_payload_for_worker_consumers() -> None:
    event_publisher = InMemoryEventPublisher()
    publisher = InMemoryQueuePublisher(event_publisher=event_publisher)

    publisher.publish(
        MatchSimulationJob(
            fixture_id="fixture-bridge",
            competition_id="league-bridge",
            competition_type=CompetitionType.LEAGUE,
            match_date=date(2026, 3, 11),
            window=FixtureWindow.SENIOR_2,
            season_id="league-bridge",
            competition_name="Bridge League",
            stage_name="Round 3",
            round_number=3,
            scheduled_kickoff_at=datetime(2026, 3, 11, 18, 0, tzinfo=timezone.utc),
            simulation_seed=17,
            home_club_id="club-1",
            home_club_name="Club One",
            home_strength_rating=82,
            away_club_id="club-2",
            away_club_name="Club Two",
            away_strength_rating=79,
            replay_visibility=ReplayVisibility.COMPETITION,
        )
    )

    queued_event = event_publisher.published_events[-1]
    assert queued_event.name == "competition_engine.queue.match_simulation.queued"
    assert queued_event.payload["idempotency_key"] == "match-simulation:fixture-bridge:2026-03-11:senior_2:1"
    assert queued_event.payload["job_payload"]["competition_name"] == "Bridge League"
    assert queued_event.payload["job_payload"]["stage_name"] == "Round 3"
    assert queued_event.payload["job_payload"]["scheduled_kickoff_at"] == "2026-03-11T18:00:00Z"
