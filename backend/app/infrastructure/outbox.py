from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.backbone.kafka import KafkaJsonProducer
from app.backbone.routing import OutboxTopicRouter
from app.core.event_backbone import build_outbox_event
from app.core.events import DomainEvent, EventPublisher
from app.models.event_backbone import EventOutbox
from app.observability.tracing import start_producer_span

OutboxEvent = EventOutbox


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrokerPublisher(Protocol):
    def publish(self, row: OutboxEvent) -> None:
        ...

    def close(self) -> None:
        ...


def write_event(event: Any, *, session: Session) -> OutboxEvent:
    outbox_event = event if isinstance(event, EventOutbox) else build_outbox_event(domain_event=event)
    session.add(outbox_event)
    session.flush()
    return outbox_event


def flush_to_broker(
    *,
    session_factory: sessionmaker[Session],
    publisher: BrokerPublisher,
    batch_size: int = 100,
) -> int:
    with session_factory() as session:
        rows = list(
            session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.occurred_at.asc(), OutboxEvent.id.asc())
                .limit(batch_size)
            ).all()
        )
        if not rows:
            return 0

        delivered = 0
        for row in rows:
            row.relay_attempts += 1
            try:
                publisher.publish(row)
            except Exception as exc:
                row.status = "pending"
                row.last_error = f"{type(exc).__name__}: {exc}"
                continue
            row.status = "processed"
            row.processed_at = utcnow()
            row.last_error = None
            delivered += 1
        session.commit()
        return delivered


@dataclass(slots=True)
class RedisKafkaOutboxPublisher:
    event_publisher: EventPublisher | None = None
    kafka_producer: KafkaJsonProducer | None = None
    topic_router: OutboxTopicRouter = field(default_factory=OutboxTopicRouter)

    def publish(self, row: OutboxEvent) -> None:
        if self.kafka_producer is not None:
            topic = self.topic_router.topic_for(row.event_type)
            headers = {
                str(key): str(value)
                for key, value in dict(row.headers_json or {}).items()
                if value is not None
            }
            headers.setdefault("event_type", row.event_type)
            headers.setdefault("producer", row.producer)
            with start_producer_span(
                "outbox.relay.publish",
                carrier=dict(row.headers_json or {}),
                attributes={
                    "messaging.destination.name": topic,
                    "messaging.operation": "publish",
                    "messaging.message.id": row.event_id,
                    "event_type": row.event_type,
                },
            ):
                self.kafka_producer.send(
                    topic=topic,
                    key=row.partition_key or row.aggregate_id or row.event_id,
                    value=_envelope(row),
                    headers=headers,
                )

        if self.event_publisher is not None:
            self.event_publisher.publish(_domain_event(row))

    def close(self) -> None:
        if self.kafka_producer is not None:
            self.kafka_producer.close()


def _domain_event(row: OutboxEvent) -> DomainEvent:
    return DomainEvent(
        name=row.event_type,
        payload=dict(row.payload_json or {}),
        event_id=row.event_id,
        occurred_at=row.occurred_at,
        aggregate_id=row.aggregate_id,
        aggregate_type=row.aggregate_type,
        version=row.version,
        producer=row.producer,
        partition_key=row.partition_key,
        headers=dict(row.headers_json or {}),
    )


def _envelope(row: OutboxEvent) -> dict[str, Any]:
    return {
        "event_id": row.event_id,
        "event_type": row.event_type,
        "aggregate_id": row.aggregate_id,
        "aggregate_type": row.aggregate_type,
        "version": row.version,
        "timestamp": row.occurred_at.isoformat(),
        "producer": row.producer,
        "partition_key": row.partition_key,
        "payload": dict(row.payload_json or {}),
        "headers": dict(row.headers_json or {}),
    }


__all__ = [
    "OutboxEvent",
    "RedisKafkaOutboxPublisher",
    "flush_to_broker",
    "write_event",
]
