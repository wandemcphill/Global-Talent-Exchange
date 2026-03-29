from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ClubToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_tokens"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_tokens_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_supply: Mapped[int] = mapped_column(Integer, nullable=False, default=1_000_000, server_default="1000000")
    circulating_supply: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    holder_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("1.0000"), server_default="1.0000")
    governance_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    performance_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    win_rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    fan_demand_score: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    treasury_balance_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubHolding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_holdings"
    __table_args__ = (
        UniqueConstraint("user_id", "club_id", name="uq_club_holdings_user_club"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tokens_owned: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    reward_tokens_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubTreasury(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_treasuries"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_treasuries_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    balance_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    lifetime_inflow_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    lifetime_outflow_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    winnings_pool_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    sponsorship_pool_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    entry_fee_pool_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    reserve_ratio_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1500, server_default="1500")
    profit_share_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    governance_budget_ratio_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=2500, server_default="2500")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubTreasuryEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_treasury_entries"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_club_treasury_entries_reference_key"),
    )

    treasury_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_treasuries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("governance_proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    balance_after_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubGovernanceState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_governance_states"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_governance_states_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    formation: Mapped[str] = mapped_column(String(16), nullable=False, default="4-3-3", server_default="4-3-3")
    playstyle: Mapped[str] = mapped_column(String(64), nullable=False, default="balanced", server_default="balanced")
    budget_rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    transfer_policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fan_mandate_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_proposal_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("governance_proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_executed_proposal_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("governance_proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubDividendDistribution(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "club_dividend_distributions"
    __table_args__ = (
        UniqueConstraint("reference_key", "user_id", name="uq_club_dividend_distributions_reference_user"),
    )

    treasury_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_treasuries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False)
    gross_amount_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    tokens_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "ClubDividendDistribution",
    "ClubGovernanceState",
    "ClubHolding",
    "ClubToken",
    "ClubTreasury",
    "ClubTreasuryEntry",
]
