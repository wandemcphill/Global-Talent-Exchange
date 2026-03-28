from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, utcnow


class CompetitionQueueRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "competition_queue_records"
    __table_args__ = (
        UniqueConstraint("queue_name", "idempotency_key", name="uq_competition_queue_records_queue_key"),
    )

    queue_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    job_name: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    aggregate_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    partition_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", server_default="queued", index=True)
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

    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
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
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending", index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    relay_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["CompetitionQueueRecord", "EventOutbox"]
