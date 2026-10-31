from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BrandAdCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Approved brand or music campaign delivered to GTEX placements."""

    __tablename__ = "brand_ad_campaigns"
    __table_args__ = (
        CheckConstraint(
            "placement IN ('homepage_rail', 'homepage_hero', 'partner_showcase', 'auth_canvas', "
            "'music_track', 'music_artist', 'music_playlist')",
            name="valid_placement",
        ),
        CheckConstraint("campaign_type IN ('brand', 'music')", name="valid_campaign_type"),
        CheckConstraint(
            "status IN ('draft', 'pending', 'approved', 'rejected', 'paused', 'archived')",
            name="valid_status",
        ),
        CheckConstraint("pricing_model IN ('CPM', 'CPC')", name="valid_pricing_model"),
        Index(
            "ix_brand_ad_campaigns_delivery",
            "placement",
            "campaign_type",
            "status",
            "is_approved",
            "is_active",
            "start_at",
            "end_at",
        ),
        Index("ix_brand_ad_campaigns_priority", "priority"),
        Index("ix_brand_ad_campaigns_advertiser", "advertiser_id", "status"),
    )

    # For advertiser-created campaigns this is the authenticated users.id.
    # Kept nullable and without a FK to preserve any legacy admin-seeded rows.
    advertiser_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    brand_name: Mapped[str] = mapped_column(String(160), nullable=False)
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(String(360), nullable=False, default="", server_default="")
    placement: Mapped[str] = mapped_column(String(40), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    creative_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

    campaign_type: Mapped[str] = mapped_column(String(16), nullable=False, default="brand", server_default="brand")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    budget_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    pricing_model: Mapped[str] = mapped_column(String(8), nullable=False, default="CPM", server_default="CPM")
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0"), server_default="0"
    )

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    music_target_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    music_target_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    music_title: Mapped[str | None] = mapped_column(String(180), nullable=True)
    music_artist_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    music_playlist_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    music_genre: Mapped[str | None] = mapped_column(String(80), nullable=True)


__all__ = ["BrandAdCampaign"]
