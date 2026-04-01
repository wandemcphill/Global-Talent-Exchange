from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserWallet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_wallets"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_wallets_user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    currency: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="credit",
        server_default="credit",
    )
    compliance_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="verified",
        server_default="verified",
    )

    user: Mapped["User"] = relationship(back_populates="wallet_profile")


class WalletTransactionRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_wallet_transactions_reference"),
        Index("ix_wallet_transactions_user_created_at", "user_id", "created_at"),
        Index("ix_wallet_transactions_status", "status"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    reference: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="wallet_transactions")


__all__ = ["UserWallet", "WalletTransactionRecord"]
