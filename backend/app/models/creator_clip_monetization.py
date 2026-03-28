from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorClipRevenueAttribution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_clip_revenue_attributions"
    __table_args__ = (
        UniqueConstraint(
            "export_id",
            "source_reference",
            name="uq_creator_clip_revenue_attributions_export_source",
        ),
        Index("ix_creator_clip_revenue_attributions_creator_user_id", "creator_user_id"),
        Index("ix_creator_clip_revenue_attributions_export_id", "export_id"),
        Index("ix_creator_clip_revenue_attributions_match_key", "match_key"),
        Index("ix_creator_clip_revenue_attributions_is_viral", "is_viral"),
    )

    export_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("highlight_share_exports.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_key: Mapped[str] = mapped_column(String(120), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rpm_per_view: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0020"),
        server_default="0.0020",
    )
    platform_payout_revenue_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    in_app_ad_revenue_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    sponsored_clip_revenue_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    gross_revenue_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    creator_base_share_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    platform_share_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    growth_pool_share_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    viral_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    referral_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    weekly_top_creator_bonus_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    creator_payout_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    growth_pool_retained_credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0.0000",
    )
    is_viral: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    wallet_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CreatorClipRevenueAttribution"]
