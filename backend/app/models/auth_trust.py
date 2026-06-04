from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RecoveryQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recovery_questions"
    __table_args__ = (
        CheckConstraint("position IN (1, 2)", name="ck_recovery_questions_position_two_slots"),
        UniqueConstraint("user_id", "position", name="uq_recovery_questions_user_position"),
        Index("ix_recovery_questions_user_id", "user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    answer_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship()


class TrustedDevice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trusted_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_trusted_devices_user_device"),
        Index("ix_trusted_devices_user_id", "user_id"),
        Index("ix_trusted_devices_device_id", "device_id"),
        Index("ix_trusted_devices_trusted", "trusted"),
        Index("ix_trusted_devices_user_last_seen_at", "user_id", "last_seen_at"),
        Index("uq_trusted_devices_token_hash", "trusted_device_token_hash", unique=True),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(String(120), nullable=False)
    install_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    os: Mapped[str | None] = mapped_column(String(80), nullable=True)
    device_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ip_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    trusted_device_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()


class LoginAttempt(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_email_created_at", "email", "created_at"),
        Index("ix_login_attempts_device_id_created_at", "device_id", "created_at"),
        Index("ix_login_attempts_ip_created_at", "ip_address", "created_at"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")


class SecurityEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_user_id_created_at", "user_id", "created_at"),
        Index("ix_security_events_user_event_created_at", "user_id", "event_type", "created_at"),
        Index("ix_security_events_event_type", "event_type"),
        Index("ix_security_events_severity", "severity"),
    )

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="info", server_default="info")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User | None"] = relationship()


__all__ = [
    "LoginAttempt",
    "RecoveryQuestion",
    "SecurityEvent",
    "TrustedDevice",
]
