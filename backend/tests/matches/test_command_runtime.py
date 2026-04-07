from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.events import DomainEvent, InMemoryEventPublisher
from app.matches.command_runtime import LocalMatchCommandBridge
from app.models.base import Base
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.event_backbone import CompetitionQueueRecord
from app.models.event_backbone import EventOutbox


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Competition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            CompetitionQueueRecord.__table__,
            EventOutbox.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_local_match_command_bridge_queues_simulation_for_existing_match() -> None:
    session_factory = _build_session_factory()
    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id="match-bridge-1",
                competition_id="competition-1",
                round_id="round-1",
                round_number=3,
                stage="league",
                home_club_id="home-1",
                away_club_id="away-1",
                match_date=date(2026, 3, 11),
                window="senior_2",
                slot_sequence=1,
                status="queued",
                metadata_json={},
            )
        )
        session.commit()

    event_publisher = InMemoryEventPublisher()
    bridge = LocalMatchCommandBridge(
        session_factory=session_factory,
        event_publisher=event_publisher,
    )
    event_publisher.subscribe(bridge.handle_event)

    event_publisher.publish(
        DomainEvent(
            name="orchestrator.command.match.start",
            payload={
                "match_id": "match-bridge-1",
                "command_name": "StartMatchCommand",
                "match_status": "queued",
                "command": {
                    "payload": {
                        "match_id": "match-bridge-1",
                    }
                },
            },
            aggregate_id="match-bridge-1",
        )
    )

    event_names = [event.name for event in event_publisher.published_events]
    assert event_names == [
        "orchestrator.command.match.start",
        "competition.match.scheduled",
        "competition_engine.queue.match_simulation.queued",
    ]

    scheduled_payload = event_publisher.published_events[1].payload
    assert scheduled_payload["fixture_id"] == "match-bridge-1"
    assert scheduled_payload["competition_context"]["competition_id"] == "competition-1"
    assert scheduled_payload["competition_context"]["competition_type"] == "league"

    with session_factory() as session:
        queue_record = session.scalar(
            select(CompetitionQueueRecord).where(CompetitionQueueRecord.aggregate_id == "match-bridge-1")
        )
        assert queue_record is not None
        assert queue_record.queue_name == "match_simulation"
        assert queue_record.job_name == "match_simulation"
        assert queue_record.status == "queued"
        assert queue_record.payload_json["fixture_id"] == "match-bridge-1"
        assert queue_record.payload_json["competition_id"] == "competition-1"
        assert queue_record.payload_json["home_club_id"] == "home-1"
        assert queue_record.payload_json["away_club_id"] == "away-1"
        assert queue_record.payload_json["window"] == "senior_2"
