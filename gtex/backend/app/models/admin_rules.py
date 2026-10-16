from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AdminFeatureFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_feature_flags"

    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="global", server_default="global")
    launch_state: Mapped[str] = mapped_column(String(32), nullable=False, default="public", server_default="public")
    allowed_roles_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_regions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    beta_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    kill_switch_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    maintenance_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by_user: Mapped["User | None"] = relationship()


class AdminFeatureFlagAuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "admin_feature_flag_audit_log"

    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    next_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    actor: Mapped["User | None"] = relationship()


class AdminBetaAccessGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_beta_access_grants"
    __table_args__ = (UniqueConstraint("feature_key", "user_id", name="uq_admin_beta_access_grants_feature_user"),)

    feature_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    granted_by_user: Mapped["User | None"] = relationship(foreign_keys=[granted_by_user_id])


class AdminCalendarRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_calendar_rules"

    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    world_cup_exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by_user: Mapped["User | None"] = relationship()


class AdminRewardRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_reward_rules"
    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trading_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=2000, server_default="2000")
    gift_platform_rake_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=3000, server_default="3000")
    withdrawal_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    minimum_withdrawal_fee_credits: Mapped[float] = mapped_column(
        Numeric(18, 4), nullable=False, default=5, server_default="5.0000"
    )
    # Product default is 30%; Admin may change the active rule without code changes.
    competition_platform_fee_bps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3000, server_default="3000"
    )
    stability_controls_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by_user: Mapped["User | None"] = relationship()
