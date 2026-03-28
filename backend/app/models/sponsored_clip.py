from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SponsoredClip(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sponsored_clips"
    __table_args__ = (
        Index("ix_sponsored_clips_advertiser_id", "advertiser_id"),
        Index("ix_sponsored_clips_clip_id", "clip_id"),
        Index("ix_sponsored_clips_start_time", "start_time"),
        Index("ix_sponsored_clips_end_time", "end_time"),
        Index("ix_sponsored_clips_is_active", "is_active"),
    )

    advertiser_id: Mapped[str] = mapped_column(String(36), nullable=False)
    clip_id: Mapped[str] = mapped_column(String(120), nullable=False)
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    bid_cpm: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_formats_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_creators_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_regions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    impressions_served: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_watch_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    clip_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["SponsoredClip"]
