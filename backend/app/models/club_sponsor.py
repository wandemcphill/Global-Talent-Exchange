from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SponsorOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sponsor_offers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_sponsor_offers_code"),
        Index("ix_sponsor_offers_category", "category"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    offer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="club", server_default="club")
    base_value_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    default_duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    approved_surfaces_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    creative_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class SponsorOfferRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sponsor_offer_rules"
    __table_args__ = (Index("ix_sponsor_offer_rules_sponsor_offer_id", "sponsor_offer_id"),)

    sponsor_offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("sponsor_offers.id", ondelete="CASCADE"), nullable=False)
    min_fan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    min_reputation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    min_club_valuation: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    min_media_popularity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    min_competition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    min_rivalry_visibility: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    required_prestige_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    competition_allowlist_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class ClubSponsor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_sponsors"
    __table_args__ = (
        Index("ix_club_sponsors_club_id", "club_id"),
        Index("ix_club_sponsors_sponsor_offer_id", "sponsor_offer_id"),
        Index("ix_club_sponsors_status", "status"),
    )

    club_id: Mapped[str] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False)
    sponsor_offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("sponsor_offers.id", ondelete="RESTRICT"), nullable=False)
    contract_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_sponsorship_contracts.id", ondelete="SET NULL"), nullable=True)
    sponsor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="club", server_default="club")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    contract_value_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="USD", server_default="USD")
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_surfaces_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    creative_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    analytics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["ClubSponsor", "SponsorOffer", "SponsorOfferRule"]
