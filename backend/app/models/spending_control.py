from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from app.models.user import User


class SpendingControlDecision(StrEnum):
    APPROVED = "approved"
    REVIEW = "review"
    BLOCKED = "blocked"


class SpendingControlAuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "spending_control_audit_events"
    __table_args__ = (
        Index("ix_spending_control_audit_events_actor_created_at", "actor_user_id", "created_at"),
        Index("ix_spending_control_audit_events_target_created_at", "target_user_id", "created_at"),
        Index("ix_spending_control_audit_events_scope_decision", "control_scope", "decision"),
        Index("ix_spending_control_audit_events_reference_key", "reference_key"),
    )

    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    control_scope: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    decision: Mapped[SpendingControlDecision] = mapped_column(
        Enum(SpendingControlDecision, name="spending_control_decision", native_enum=False),
        nullable=False,
    )
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ledger_unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
    )
    primary_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_rules_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    actor_user: Mapped["User | None"] = relationship(foreign_keys=[actor_user_id])
    target_user: Mapped["User | None"] = relationship(foreign_keys=[target_user_id])
