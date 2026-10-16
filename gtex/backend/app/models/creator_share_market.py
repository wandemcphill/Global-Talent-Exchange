from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorClubShareMarketControl(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_share_market_controls"
    __table_args__ = (
        UniqueConstraint("control_key", name="uq_creator_club_share_market_controls_control_key"),
    )

    control_key: Mapped[str] = mapped_column(String(32), nullable=False, default="default", server_default="default")
    max_shares_per_club: Mapped[int] = mapped_column(Integer, nullable=False, default=10000, server_default="10000")
    max_shares_per_fan: Mapped[int] = mapped_column(Integer, nullable=False, default=250, server_default="250")
    shareholder_revenue_share_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=2000, server_default="2000")
    issuance_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    purchase_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    max_primary_purchase_value_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("2500.0000"),
        server_default="2500.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubShareMarket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_share_markets"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_creator_club_share_markets_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issued_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    share_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    max_shares_issued: Mapped[int] = mapped_column(Integer, nullable=False)
    shares_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_shares_per_fan: Mapped[int] = mapped_column(Integer, nullable=False)
    creator_controlled_shares: Mapped[int] = mapped_column(Integer, nullable=False)
    shareholder_revenue_share_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    total_purchase_volume_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    total_revenue_distributed_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubShareHolding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_share_holdings"
    __table_args__ = (
        UniqueConstraint("club_id", "user_id", name="uq_creator_club_share_holdings_club_user"),
    )

    market_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_club_share_markets.id", ondelete="CASCADE"),
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
    share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_spent_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    revenue_earned_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubSharePurchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_share_purchases"

    market_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_club_share_markets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_count: Mapped[int] = mapped_column(Integer, nullable=False)
    share_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_price_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubShareDistribution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_share_distributions"
    __table_args__ = (
        UniqueConstraint(
            "club_id",
            "source_type",
            "source_reference_id",
            name="uq_creator_club_share_distributions_club_source_ref",
        ),
    )

    market_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_club_share_markets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    source_reference_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_league_seasons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    eligible_revenue_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    shareholder_pool_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    creator_retained_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    shareholder_revenue_share_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    distributed_share_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="settled", server_default="settled")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorClubSharePayout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_club_share_payouts"
    __table_args__ = (
        UniqueConstraint("distribution_id", "user_id", name="uq_creator_club_share_payouts_distribution_user"),
    )

    distribution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_club_share_distributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    holding_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_club_share_holdings.id", ondelete="SET NULL"),
        nullable=True,
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
    share_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payout_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ownership_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CreatorClubShareDistribution",
    "CreatorClubShareHolding",
    "CreatorClubShareMarket",
    "CreatorClubShareMarketControl",
    "CreatorClubSharePayout",
    "CreatorClubSharePurchase",
]
