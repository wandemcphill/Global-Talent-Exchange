from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, event, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin


class LedgerEventType(StrEnum):
    ORDER_ACCEPTED = "order.accepted"
    ORDER_FUNDS_RESERVED = "order.funds_reserved"
    ORDER_EXECUTED = "order.executed"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_RELEASED = "order.released"


class LedgerEventRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ledger_event_records"

    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[LedgerEventType] = mapped_column(
        Enum(
            LedgerEventType,
            name="ledger_event_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


@event.listens_for(LedgerEventRecord, "before_update", propagate=True)
def _prevent_ledger_event_updates(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Ledger events are append-only and cannot be updated.")


@event.listens_for(LedgerEventRecord, "before_delete", propagate=True)
def _prevent_ledger_event_deletes(_: Any, __: Any, ___: Any) -> None:
    raise ValueError("Ledger events are append-only and cannot be deleted.")
