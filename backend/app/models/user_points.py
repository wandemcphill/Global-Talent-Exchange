from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserPointAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Dedicated per-user personal reward points account, isolated from Fan War and Club Loyalty points."""

    __tablename__ = "user_point_accounts"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    lifetime_earned: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    lifetime_spent: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )


class UserPointLedgerEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable append-only ledger entry for personal user point grants and spends."""

    __tablename__ = "user_point_ledger_entries"

    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_point_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    delta: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    source_scope: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="admin_grant",
        server_default="admin_grant",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["UserPointAccount", "UserPointLedgerEntry"]
