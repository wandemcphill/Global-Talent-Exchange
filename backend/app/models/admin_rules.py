from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AdminFeatureFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_feature_flags"

    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="global", server_default="global")
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    updated_by_user: Mapped["User | None"] = relationship()


class AdminCalendarRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_calendar_rules"

    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    world_cup_exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    updated_by_user: Mapped["User | None"] = relationship()


class AdminRewardRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_reward_rules"

    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trading_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=2000, server_default="2000")
    gift_platform_rake_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=3000, server_default="3000")
    withdrawal_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    minimum_withdrawal_fee_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=5, server_default="5.0000")
    competition_platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    stability_controls_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    updated_by_user: Mapped["User | None"] = relationship()
