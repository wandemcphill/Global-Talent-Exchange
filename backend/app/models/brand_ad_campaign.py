from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BrandAdCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Approved brand campaign delivered to public GTEX advertising placements."""

    __tablename__ = "brand_ad_campaigns"
    __table_args__ = (
        CheckConstraint(
            "placement IN ('homepage_rail', 'homepage_hero', 'partner_showcase', 'auth_canvas')",
            name="valid_placement",
        ),
        Index(
            "ix_brand_ad_campaigns_delivery",
            "placement",
            "is_approved",
            "is_active",
            "start_at",
            "end_at",
        ),
        Index("ix_brand_ad_campaigns_priority", "priority"),
    )

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


__all__ = ["BrandAdCampaign"]
