from __future__ import annotations

from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, JSON, Numeric, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from backend.app.models.wallet import LedgerUnit

if TYPE_CHECKING:
    from backend.app.models.user import User


class EconomyBurnEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "economy_burn_events"
    __table_args__ = (
        Index("ix_economy_burn_events_source", "source_type", "source_id"),
        Index("ix_economy_burn_events_created_at", "created_at"),
    )

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    unit: Mapped[LedgerUnit] = mapped_column(
        Enum(LedgerUnit, name="ledger_unit", native_enum=False),
        nullable=False,
        default=LedgerUnit.CREDIT,
    )
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])


__all__ = ["EconomyBurnEvent"]
