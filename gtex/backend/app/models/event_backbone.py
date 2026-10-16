from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CompetitionQueueRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "competition_queue_records"
    __table_args__ = (UniqueConstraint("queue_name", "idempotency_key", name="uq_competition_queue_records_queue_key"),)

    queue_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    job_name: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    partition_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="queued", server_default="queued", index=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class EventOutbox(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "event_outbox"

    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    partition_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    producer: Mapped[str] = mapped_column(String(128), nullable=False, default="gtex", server_default="gtex")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    headers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", server_default="pending", index=True
    )
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    relay_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventConsumerState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_consumer_states"
    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id", name="uq_event_consumer_states_consumer_event"),
        Index("ix_event_consumer_states_status_updated_at", "status", "updated_at"),
        Index("ix_event_consumer_states_event_type_status", "event_type", "status"),
    )

    consumer_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="processing", server_default="processing", index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    headers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class EventDeadLetter(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "event_dead_letters"
    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id", name="uq_event_dead_letters_consumer_event"),
        Index("ix_event_dead_letters_consumer_dead_lettered_at", "consumer_name", "dead_lettered_at"),
    )

    consumer_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    headers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dead_lettered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )


__all__ = ["CompetitionQueueRecord", "EventConsumerState", "EventDeadLetter", "EventOutbox"]
