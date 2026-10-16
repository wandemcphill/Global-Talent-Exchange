from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralAnalyticsDaily(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_analytics_daily"
    __table_args__ = (
        UniqueConstraint("analytics_date", "scope", "scope_id", name="uq_referral_analytics_daily_scope"),
    )

    analytics_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    creator_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    share_code_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("share_codes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    signups_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    qualified_users_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    retained_day_7_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    retained_day_30_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    reward_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    blocked_reward_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    approved_reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
