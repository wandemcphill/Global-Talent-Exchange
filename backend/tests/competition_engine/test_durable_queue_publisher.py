from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.competition_engine.queue_contracts import DurableQueuePublisher, MatchSimulationJob
from app.core.database import ensure_database_schema_current
from app.core.events import InMemoryEventPublisher
from app.models.event_backbone import CompetitionQueueRecord, EventOutbox


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'durable-queue.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    ensure_database_schema_current(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _job() -> MatchSimulationJob:
    return MatchSimulationJob(
        fixture_id="fixture-100",
        competition_id="league-alpha",
        competition_type=CompetitionType.LEAGUE,
        match_date=date(2026, 8, 1),
        window=FixtureWindow.SENIOR_1,
    )


def test_durable_queue_publisher_persists_outbox_and_publishes_after_commit(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    event_publisher = InMemoryEventPublisher()

    with session_factory() as session:
        publisher = DurableQueuePublisher(session=session, event_publisher=event_publisher)
        record = publisher.publish(_job())

        queued = session.scalars(select(CompetitionQueueRecord)).all()
        outbox = session.scalars(select(EventOutbox)).all()

        assert record.queue_name == "match_simulation"
        assert len(queued) == 1
        assert len(outbox) == 1
        assert outbox[0].aggregate_id == "fixture-100"
        assert len(event_publisher.published_events) == 0

        session.commit()

    assert len(event_publisher.published_events) == 1
    assert event_publisher.published_events[0].event_id == outbox[0].event_id
    engine.dispose()


def test_durable_queue_publisher_is_idempotent_and_supports_session_factory_mode(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)
    event_publisher = InMemoryEventPublisher()
    publisher = DurableQueuePublisher(session_factory=session_factory, event_publisher=event_publisher)

    first = publisher.publish(_job())
    second = publisher.publish(_job())

    assert first.idempotency_key == second.idempotency_key
    assert len(event_publisher.published_events) == 1
    assert len(publisher.list_published("match_simulation")) == 1

    with session_factory() as session:
        assert len(session.scalars(select(CompetitionQueueRecord)).all()) == 1
        assert len(session.scalars(select(EventOutbox)).all()) == 1

    engine.dispose()
