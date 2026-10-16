from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class BroadcastRight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broadcast_rights"
    __table_args__ = (
        Index("ix_broadcast_rights_competition_id", "competition_id"),
        Index("ix_broadcast_rights_owner_id", "owner_id"),
        Index("ix_broadcast_rights_exclusivity", "exclusivity"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    acquisition_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    revenue_share_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    exclusivity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BroadcastRightsAuction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broadcast_rights_auctions"
    __table_args__ = (
        Index("ix_broadcast_rights_auctions_competition_id", "competition_id"),
        Index("ix_broadcast_rights_auctions_status", "status"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reserve_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    revenue_share_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    exclusivity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    winning_right_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("broadcast_rights.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BroadcastRightsBid(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broadcast_rights_bids"
    __table_args__ = (
        UniqueConstraint("auction_id", "bidder_user_id", name="uq_broadcast_rights_bids_auction_bidder"),
        Index("ix_broadcast_rights_bids_auction_id", "auction_id"),
        Index("ix_broadcast_rights_bids_status", "status"),
    )

    auction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("broadcast_rights_auctions.id", ondelete="CASCADE"),
        nullable=False,
    )
    bidder_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="submitted", server_default="submitted")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BroadcastAccessGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broadcast_access_grants"
    __table_args__ = (
        UniqueConstraint("broadcast_right_id", "user_id", name="uq_broadcast_access_grants_right_user"),
        Index("ix_broadcast_access_grants_user_id", "user_id"),
    )

    broadcast_right_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("broadcast_rights.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    granted_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ViewSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "view_sessions"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_view_sessions_match_user"),
        Index("ix_view_sessions_match_id", "match_id"),
        Index("ix_view_sessions_competition_id", "competition_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[str] = mapped_column(String(120), nullable=False)
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BroadcastRevenueDistribution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "broadcast_revenue_distributions"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_broadcast_revenue_distributions_reference_key"),
        Index("ix_broadcast_revenue_distributions_match_id", "match_id"),
        Index("ix_broadcast_revenue_distributions_recipient_id", "recipient_id"),
    )

    match_id: Mapped[str] = mapped_column(String(120), nullable=False)
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    broadcast_right_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("broadcast_rights.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    recipient_id: Mapped[str] = mapped_column(String(36), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    reference_key: Mapped[str] = mapped_column(String(160), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "BroadcastAccessGrant",
    "BroadcastRevenueDistribution",
    "BroadcastRight",
    "BroadcastRightsAuction",
    "BroadcastRightsBid",
    "ViewSession",
]
