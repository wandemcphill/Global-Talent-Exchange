from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StadiumEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stadium_events"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_stadium_events_match_id"),
        Index("ix_stadium_events_event_type", "event_type"),
        Index("ix_stadium_events_event_status", "event_status"),
        Index("ix_stadium_events_public_sales_starts_at", "public_sales_starts_at"),
    )

    stadium_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    match_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    calendar_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_match_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    venue_name: Mapped[str] = mapped_column(String(160), nullable=False)
    home_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    away_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="league", server_default="league")
    event_status: Mapped[str] = mapped_column(String(24), nullable=False, default="on_sale", server_default="on_sale")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    tier_distribution_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    base_price_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    early_access_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_sales_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sales_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    importance_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.5000"), server_default="0.5000")
    rivalry_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    player_popularity_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000")
    demand_multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("1.0000"), server_default="1.0000")
    tickets_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tickets_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    resale_ticket_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    resale_volume: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    platform_cut_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    club_share_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    jackpot_pool_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    loyalty_points_distributed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StadiumTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stadium_tickets"
    __table_args__ = (
        UniqueConstraint("match_id", "seat_code", name="uq_stadium_tickets_match_seat"),
        Index("ix_stadium_tickets_event_id_status", "event_id", "status"),
        Index("ix_stadium_tickets_user_id", "user_id"),
        Index("ix_stadium_tickets_match_id", "match_id"),
    )

    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("stadium_events.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    match_id: Mapped[str] = mapped_column(String(120), nullable=False)
    seat_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    seat_code: Mapped[str] = mapped_column(String(24), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    original_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="sold", server_default="sold")
    resale_listing_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    loyalty_points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    exclusive_drop_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TicketWaitlist(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ticket_waitlists"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_ticket_waitlists_match_user"),
        Index("ix_ticket_waitlists_match_id_status", "match_id", "status"),
        Index("ix_ticket_waitlists_user_id", "user_id"),
    )

    match_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seat_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", server_default="queued")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TicketReaction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ticket_reactions"
    __table_args__ = (
        Index("ix_ticket_reactions_match_id_created_at", "match_id", "created_at"),
        Index("ix_ticket_reactions_ticket_id", "ticket_id"),
        Index("ix_ticket_reactions_user_id", "user_id"),
    )

    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("stadium_tickets.id", ondelete="CASCADE"), nullable=False)
    match_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(16), nullable=False)
    crowd_delta: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    influence_multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())


__all__ = [
    "StadiumEvent",
    "StadiumTicket",
    "TicketReaction",
    "TicketWaitlist",
]
