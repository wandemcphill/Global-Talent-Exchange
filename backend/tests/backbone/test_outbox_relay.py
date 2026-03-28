from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.backbone.outbox_relay import OutboxRelayService
from app.backbone.routing import OutboxTopicRouter
from app.core.database import ensure_database_schema_current
from app.core.event_backbone import build_outbox_event
from app.core.events import DomainEvent
from app.models.event_backbone import EventOutbox


class FakeKafkaProducer:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.closed = False

    def send(
        self,
        *,
        topic: str,
        value: dict[str, object],
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.messages.append(
            {
                "topic": topic,
                "value": value,
                "key": key,
                "headers": headers,
            }
        )

    def close(self) -> None:
        self.closed = True


def _build_session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'outbox-relay.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    ensure_database_schema_current(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_outbox_relay_routes_queue_events_to_kafka_topics(tmp_path) -> None:
    engine, session_factory = _build_session_factory(tmp_path)

    with session_factory() as session:
        session.add(
            build_outbox_event(
                domain_event=DomainEvent(
                    name="competition_engine.queue.match_simulation.queued",
                    event_id="8c7f8474-53c4-43ef-b724-b6b66a3e10b5",
                    payload={
                        "job_name": "match_simulation",
                        "queue_name": "match_simulation",
                        "idempotency_key": "match-simulation:fixture-200",
                        "job_payload": {"fixture_id": "fixture-200"},
                    },
                    aggregate_id="fixture-200",
                    aggregate_type="competition_queue",
                    producer="competition-engine",
                    partition_key="fixture-200",
                    headers={"delivery_mode": "durable"},
                )
            )
        )
        session.commit()

    producer = FakeKafkaProducer()
    relay = OutboxRelayService(
        session_factory=session_factory,
        producer=producer,
        router=OutboxTopicRouter(topic_prefix="gtex"),
        batch_size=10,
        poll_interval_ms=50,
    )

    delivered = relay.relay_once()

    assert delivered == 1
    assert producer.messages == [
        {
            "topic": "gtex.match.scheduled",
            "value": {
                "event_id": "8c7f8474-53c4-43ef-b724-b6b66a3e10b5",
                "event_type": "competition_engine.queue.match_simulation.queued",
                "aggregate_id": "fixture-200",
                "aggregate_type": "competition_queue",
                "version": 1,
                "timestamp": producer.messages[0]["value"]["timestamp"],  # type: ignore[index]
                "producer": "competition-engine",
                "partition_key": "fixture-200",
                "payload": {
                    "job_name": "match_simulation",
                    "queue_name": "match_simulation",
                    "idempotency_key": "match-simulation:fixture-200",
                    "job_payload": {"fixture_id": "fixture-200"},
                },
                "headers": {"delivery_mode": "durable"},
            },
            "key": "fixture-200",
            "headers": {
                "event_type": "competition_engine.queue.match_simulation.queued",
                "producer": "competition-engine",
            },
        }
    ]

    with session_factory() as session:
        row = session.scalar(select(EventOutbox).where(EventOutbox.event_id == "8c7f8474-53c4-43ef-b724-b6b66a3e10b5"))
        assert row is not None
        assert row.status == "processed"
        assert row.processed_at is not None
        assert row.relay_attempts == 1
        assert row.last_error is None

    engine.dispose()
