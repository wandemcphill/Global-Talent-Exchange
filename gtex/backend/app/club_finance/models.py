from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SponsorTier(StrEnum):
    LOCAL = "local"
    REGIONAL = "regional"
    GLOBAL = "global"


class ClubFinanceProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_finance_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_club_finance_profiles_user_id"),
        Index("ix_club_finance_profiles_balance", "balance"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    weekly_wages: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    sponsorship_income: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    match_income: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    broadcast_income: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    transfer_profit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    expenses: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    transfers_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    forced_sale_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    forced_sale_player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_weekly_cycle_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class Sponsor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_finance_sponsors"
    __table_args__ = (
        UniqueConstraint("name", name="uq_club_finance_sponsors_name"),
        Index("ix_club_finance_sponsors_tier", "tier"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tier: Mapped[SponsorTier] = mapped_column(
        Enum(SponsorTier, name="club_finance_sponsor_tier", native_enum=False),
        nullable=False,
    )
    payout: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    requirements_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class ClubFinanceTransaction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "club_finance_transactions"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_club_finance_transactions_reference_key"),
        Index("ix_club_finance_transactions_user_id", "user_id"),
        Index("ix_club_finance_transactions_transaction_type", "transaction_type"),
    )

    finance_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_finance_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    sponsor_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_finance_sponsors.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


__all__ = ["ClubFinanceProfile", "ClubFinanceTransaction", "Sponsor", "SponsorTier"]
