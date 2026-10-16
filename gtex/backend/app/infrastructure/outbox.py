from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
from uuid import uuid4
from typing import Any, Protocol

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.backbone.kafka import KafkaJsonProducer
from app.backbone.routing import OutboxTopicRouter
from app.core.event_backbone import build_outbox_event
from app.core.events import DomainEvent, EventPublisher
from app.models.event_backbone import EventDeadLetter, EventOutbox
from app.observability.tracing import start_producer_span

OutboxEvent = EventOutbox
OUTBOX_RELAY_CONSUMER = "outbox-relay"
DEFAULT_MAX_RELAY_ATTEMPTS = 5
DEFAULT_CLAIM_TTL_SECONDS = 300
logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrokerPublisher(Protocol):
    def publish(self, row: OutboxEvent) -> None: ...

    def close(self) -> None: ...


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
    max_attempts: int = DEFAULT_MAX_RELAY_ATTEMPTS,
    claim_ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
) -> int:
    with session_factory() as session:
        claims = _claim_pending_rows(
            session,
            batch_size=batch_size,
            claim_ttl_seconds=claim_ttl_seconds,
        )
        session.commit()
        if not claims:
            return 0

    delivered = 0
    for row_id, claim_token in claims:
        row = _load_claimed_event_for_publish(
            session_factory=session_factory,
            row_id=row_id,
            claim_token=claim_token,
        )
        if row is None:
            continue
        try:
            publisher.publish(row)
        except Exception as exc:
            with session_factory() as session:
                _mark_publish_failure(
                    session,
                    row_id=row_id,
                    claim_token=claim_token,
                    error=exc,
                    max_attempts=max_attempts,
                )
                session.commit()
            continue
        with session_factory() as session:
            claimed = _load_claimed_row(session, row_id=row_id, claim_token=claim_token)
            if claimed is None:
                continue
            claimed.status = "processed"
            claimed.processed_at = utcnow()
            claimed.last_error = None
            claimed.claimed_at = None
            claimed.claim_token = None
            session.commit()
            delivered += 1
    return delivered


@dataclass(slots=True)
class RedisKafkaOutboxPublisher:
    event_publisher: EventPublisher | None = None
    kafka_producer: KafkaJsonProducer | None = None
    topic_router: OutboxTopicRouter = field(default_factory=OutboxTopicRouter)

    def publish(self, row: OutboxEvent) -> None:
        if self.kafka_producer is not None:
            topic = self.topic_router.topic_for(row.event_type)
            headers = {str(key): str(value) for key, value in dict(row.headers_json or {}).items() if value is not None}
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


def _claim_pending_rows(
    session: Session,
    *,
    batch_size: int,
    claim_ttl_seconds: int,
) -> list[tuple[str, str]]:
    stale_before = utcnow() - timedelta(seconds=max(int(claim_ttl_seconds), 1))
    statement = (
        select(OutboxEvent)
        .where(
            or_(
                OutboxEvent.status == "pending",
                and_(
                    OutboxEvent.status == "processing",
                    OutboxEvent.claimed_at.is_not(None),
                    OutboxEvent.claimed_at < stale_before,
                ),
            )
        )
        .order_by(OutboxEvent.occurred_at.asc(), OutboxEvent.id.asc())
        .limit(batch_size)
    )
    if _supports_row_locks(session):
        statement = statement.with_for_update(skip_locked=True)
    rows = list(session.scalars(statement).all())
    if not rows:
        return []
    now = utcnow()
    claims: list[tuple[str, str]] = []
    for row in rows:
        claim_token = str(uuid4())
        row.status = "processing"
        row.claimed_at = now
        row.claim_token = claim_token
        row.last_error = None
        row.relay_attempts = int(row.relay_attempts or 0) + 1
        claims.append((row.id, claim_token))
    session.flush()
    return claims


def _load_claimed_row(session: Session, *, row_id: str, claim_token: str) -> OutboxEvent | None:
    return session.scalar(
        select(OutboxEvent).where(
            OutboxEvent.id == row_id,
            OutboxEvent.claim_token == claim_token,
        )
    )


def _load_claimed_event_for_publish(
    *,
    session_factory: sessionmaker[Session],
    row_id: str,
    claim_token: str,
) -> OutboxEvent | None:
    with session_factory() as session:
        row = _load_claimed_row(session, row_id=row_id, claim_token=claim_token)
        if row is None:
            return None
        session.expunge(row)
        return row


def _mark_publish_failure(
    session: Session,
    *,
    row_id: str,
    claim_token: str,
    error: BaseException,
    max_attempts: int,
) -> None:
    row = _load_claimed_row(session, row_id=row_id, claim_token=claim_token)
    if row is None:
        return
    error_message = f"{type(error).__name__}: {error}"
    exhausted = int(row.relay_attempts or 0) >= max(int(max_attempts), 1)
    row.status = "dead_letter" if exhausted else "pending"
    row.last_error = error_message
    row.claimed_at = None
    row.claim_token = None
    if exhausted:
        row.dead_lettered_at = utcnow()
        _upsert_dead_letter(session, row=row, error_message=error_message)
        logger.error(
            "outbox.dead_lettered event_id=%s event_type=%s attempts=%s error=%s",
            row.event_id,
            row.event_type,
            row.relay_attempts,
            error_message,
        )
    else:
        logger.warning(
            "outbox.publish_failed event_id=%s event_type=%s attempts=%s error=%s",
            row.event_id,
            row.event_type,
            row.relay_attempts,
            error_message,
        )
    session.flush()


def _upsert_dead_letter(session: Session, *, row: OutboxEvent, error_message: str) -> None:
    record = session.scalar(
        select(EventDeadLetter).where(
            EventDeadLetter.consumer_name == OUTBOX_RELAY_CONSUMER,
            EventDeadLetter.event_id == row.event_id,
        )
    )
    if record is None:
        record = EventDeadLetter(
            consumer_name=OUTBOX_RELAY_CONSUMER,
            event_id=row.event_id,
            event_type=row.event_type,
            aggregate_id=row.aggregate_id,
        )
        session.add(record)
    record.event_type = row.event_type
    record.aggregate_id = row.aggregate_id
    record.attempts = int(row.relay_attempts or 0)
    record.payload_json = dict(row.payload_json or {})
    record.headers_json = dict(row.headers_json or {})
    record.last_error = error_message
    record.dead_lettered_at = row.dead_lettered_at or utcnow()


def _supports_row_locks(session: Session) -> bool:
    bind = session.get_bind()
    return bind is not None and bind.dialect.name != "sqlite"


__all__ = [
    "OutboxEvent",
    "RedisKafkaOutboxPublisher",
    "flush_to_broker",
    "write_event",
]
