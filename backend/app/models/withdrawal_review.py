from __future__ import annotations

from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import ForeignKey, JSON, Numeric, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.treasury import TreasuryWithdrawalRequest
    from app.models.user import User
    from app.models.wallet import PayoutRequest


class WithdrawalReview(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "withdrawal_reviews"
    __table_args__ = (
        Index("ix_withdrawal_reviews_withdrawal_id", "withdrawal_request_id"),
        Index("ix_withdrawal_reviews_created_at", "created_at"),
    )

    withdrawal_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("treasury_withdrawal_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payout_request_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("payout_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status_from: Mapped[str] = mapped_column(String(32), nullable=False)
    status_to: Mapped[str] = mapped_column(String(32), nullable=False)
    processor_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payout_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=Decimal("0.0000"))
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    withdrawal_request: Mapped["TreasuryWithdrawalRequest"] = relationship("TreasuryWithdrawalRequest", foreign_keys=[withdrawal_request_id])
    payout_request: Mapped["PayoutRequest | None"] = relationship("PayoutRequest", foreign_keys=[payout_request_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_user_id])


__all__ = ["WithdrawalReview"]
