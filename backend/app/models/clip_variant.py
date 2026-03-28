from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression

from app.models.base import Base, TimestampMixin


class ClipVariant(TimestampMixin, Base):
    __tablename__ = "clip_variants"
    __table_args__ = (
        UniqueConstraint("base_clip_id", "format_type", name="uq_clip_variants_base_clip_format"),
        Index("ix_clip_variants_base_clip_id", "base_clip_id"),
        Index("ix_clip_variants_base_clip_created_at", "base_clip_id", "created_at"),
        Index("ix_clip_variants_base_clip_viral_score", "base_clip_id", "viral_score"),
        Index("ix_clip_variants_base_clip_winner", "base_clip_id", "is_winner"),
    )

    variant_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    base_clip_id: Mapped[str] = mapped_column(String(160), nullable=False)
    format_type: Mapped[str] = mapped_column(String(32), nullable=False)

    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    watch_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    loop_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    drop_off_point_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    share_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    comment_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    viral_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")

    distribution_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2, server_default="0.2")
    promotion_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="exploring",
        server_default="exploring",
    )
    promotion_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=expression.true(),
    )
    pushed_to_trending: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    is_winner: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    winner_selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["ClipVariant"]
