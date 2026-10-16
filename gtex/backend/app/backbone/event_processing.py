from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import utcnow
from app.models.event_backbone import EventConsumerState, EventDeadLetter

PROCESSING_STATUS = "processing"
PROCESSED_STATUS = "processed"
FAILED_STATUS = "failed"
DEAD_LETTER_STATUS = "dead_letter"
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_CLAIM_TTL_SECONDS = 300
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EventProcessingClaim:
    consumer_name: str
    event_id: str
    event_type: str
    aggregate_id: str | None
    claim_token: str
    attempt_count: int
    payload_json: dict[str, Any]
    headers_json: dict[str, Any]


def claim_event(
    session: Session,
    *,
    consumer_name: str,
    event_id: str,
    event_type: str,
    aggregate_id: str | None,
    payload_json: dict[str, Any] | None = None,
    headers_json: dict[str, Any] | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    claim_ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
) -> EventProcessingClaim | None:
    record = _load_record_for_update(session, consumer_name=consumer_name, event_id=event_id)
    now = utcnow()
    payload = dict(payload_json or {})
    headers = dict(headers_json or {})

    if record is None:
        savepoint = session.begin_nested()
        try:
            record = EventConsumerState(
                consumer_name=consumer_name,
                event_id=event_id,
                event_type=event_type,
                aggregate_id=aggregate_id,
                status=PROCESSING_STATUS,
                attempt_count=1,
                claim_token=str(uuid4()),
                payload_json=payload,
                headers_json=headers,
                last_attempt_at=now,
            )
            session.add(record)
            session.flush()
        except IntegrityError:
            savepoint.rollback()
            record = _load_record_for_update(session, consumer_name=consumer_name, event_id=event_id)
            if record is None:
                raise
        else:
            savepoint.commit()
            return _claim_from_record(record)

    if record.status in {PROCESSED_STATUS, DEAD_LETTER_STATUS}:
        return None

    stale_after = now - timedelta(seconds=max(int(claim_ttl_seconds), 1))
    if (
        record.status == PROCESSING_STATUS
        and record.last_attempt_at is not None
        and _as_utc(record.last_attempt_at) > stale_after
    ):
        return None

    if int(record.attempt_count or 0) >= max(int(max_attempts), 1):
        _mark_dead_letter(record, error=record.last_error)
        _upsert_dead_letter(session, record)
        session.flush()
        return None

    record.status = PROCESSING_STATUS
    record.attempt_count = int(record.attempt_count or 0) + 1
    record.claim_token = str(uuid4())
    record.event_type = event_type
    record.aggregate_id = aggregate_id
    record.payload_json = payload
    record.headers_json = headers
    record.last_attempt_at = now
    record.last_error = None
    session.flush()
    return _claim_from_record(record)


def mark_event_processed(session: Session, *, claim: EventProcessingClaim) -> None:
    record = _load_record_for_update(session, consumer_name=claim.consumer_name, event_id=claim.event_id)
    if record is None or record.claim_token != claim.claim_token:
        return
    record.status = PROCESSED_STATUS
    record.claim_token = None
    record.last_error = None
    record.processed_at = utcnow()
    session.flush()


def mark_event_failed(
    session_factory: sessionmaker[Session],
    *,
    claim: EventProcessingClaim,
    error: BaseException,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> bool:
    with session_factory() as session:
        record = _load_record_for_update(session, consumer_name=claim.consumer_name, event_id=claim.event_id)
        if record is None or record.claim_token != claim.claim_token:
            session.rollback()
            return False
        error_message = f"{type(error).__name__}: {error}"
        if int(record.attempt_count or 0) >= max(int(max_attempts), 1):
            _mark_dead_letter(record, error=error_message)
            _upsert_dead_letter(session, record)
            logger.error(
                "event_processing.dead_lettered consumer=%s event_id=%s event_type=%s attempts=%s error=%s",
                record.consumer_name,
                record.event_id,
                record.event_type,
                record.attempt_count,
                error_message,
            )
            session.commit()
            return True
        record.status = FAILED_STATUS
        record.claim_token = None
        record.last_error = error_message
        record.last_attempt_at = utcnow()
        logger.warning(
            "event_processing.failed consumer=%s event_id=%s event_type=%s attempts=%s error=%s",
            record.consumer_name,
            record.event_id,
            record.event_type,
            record.attempt_count,
            error_message,
        )
        session.commit()
        return False


def _claim_from_record(record: EventConsumerState) -> EventProcessingClaim:
    return EventProcessingClaim(
        consumer_name=record.consumer_name,
        event_id=record.event_id,
        event_type=record.event_type,
        aggregate_id=record.aggregate_id,
        claim_token=str(record.claim_token or ""),
        attempt_count=int(record.attempt_count or 0),
        payload_json=dict(record.payload_json or {}),
        headers_json=dict(record.headers_json or {}),
    )


def _mark_dead_letter(record: EventConsumerState, *, error: str | None) -> None:
    record.status = DEAD_LETTER_STATUS
    record.claim_token = None
    record.last_error = error
    record.dead_lettered_at = utcnow()


def _upsert_dead_letter(session: Session, record: EventConsumerState) -> None:
    existing = session.scalar(
        select(EventDeadLetter).where(
            EventDeadLetter.consumer_name == record.consumer_name,
            EventDeadLetter.event_id == record.event_id,
        )
    )
    if existing is None:
        existing = EventDeadLetter(
            consumer_name=record.consumer_name,
            event_id=record.event_id,
            event_type=record.event_type,
            aggregate_id=record.aggregate_id,
        )
        session.add(existing)
    existing.event_type = record.event_type
    existing.aggregate_id = record.aggregate_id
    existing.attempts = int(record.attempt_count or 0)
    existing.payload_json = dict(record.payload_json or {})
    existing.headers_json = dict(record.headers_json or {})
    existing.last_error = record.last_error
    existing.dead_lettered_at = record.dead_lettered_at or utcnow()


def _load_record_for_update(session: Session, *, consumer_name: str, event_id: str) -> EventConsumerState | None:
    statement = select(EventConsumerState).where(
        EventConsumerState.consumer_name == consumer_name,
        EventConsumerState.event_id == event_id,
    )
    if _supports_row_locks(session):
        statement = statement.with_for_update()
    return session.scalar(statement)


def _supports_row_locks(session: Session) -> bool:
    bind = session.get_bind()
    return bind is not None and bind.dialect.name != "sqlite"


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)


__all__ = [
    "DEFAULT_CLAIM_TTL_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "EventProcessingClaim",
    "claim_event",
    "mark_event_failed",
    "mark_event_processed",
]
