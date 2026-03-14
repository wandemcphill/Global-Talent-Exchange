from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    allow_wallet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_market: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_story: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_competition: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_social: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_broadcasts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(nullable=False, default=dict)


class NotificationSubscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "subscription_key", name="uq_notification_subscriptions_user_key"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_key: Mapped[str] = mapped_column(String(140), nullable=False, index=True)
    subscription_type: Mapped[str] = mapped_column(String(48), nullable=False, default="general")
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(nullable=False, default=dict)


class PlatformAnnouncement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "platform_announcements"

    announcement_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="all")
    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="info")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deliver_as_notification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(nullable=False, default=dict)
    published_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
