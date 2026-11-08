from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BrandAdvertiserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "brand_advertiser_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_brand_advertiser_profiles_user"),)

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(160), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    billing_email: Mapped[str] = mapped_column(String(320), nullable=False)


class BrandAdEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only campaign telemetry. Client events are analytics estimates, never payment instructions."""

    __tablename__ = "brand_ad_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_brand_ad_events_idempotency_key"),
        Index("ix_brand_ad_events_campaign_type", "campaign_id", "event_type"),
        Index("ix_brand_ad_events_created_at", "created_at"),
    )

    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_ad_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(96), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_source: Mapped[str] = mapped_column(String(16), nullable=False, default="client", server_default="client")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class BrandAdReviewEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "brand_ad_review_events"
    __table_args__ = (Index("ix_brand_ad_review_events_campaign", "campaign_id", "created_at"),)

    campaign_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_ad_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)


__all__ = ["BrandAdvertiserProfile", "BrandAdEvent", "BrandAdReviewEvent"]
