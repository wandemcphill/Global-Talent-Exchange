from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

CREATOR_APPLICATION_NOT_APPLIED = "not_applied"
CREATOR_APPLICATION_PENDING = "pending"
CREATOR_APPLICATION_ADDITIONAL_INFO = "additional_info_required"
CREATOR_APPLICATION_VERIFICATION_REQUESTED = "verification_requested"
CREATOR_APPLICATION_APPROVED = "approved"
CREATOR_APPLICATION_REJECTED = "rejected"
CREATOR_APPLICATION_SUSPENDED = "suspended"


class CreatorApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_applications"
    __table_args__ = (
        Index("ix_creator_applications_user_id", "user_id"),
        Index("ix_creator_applications_status", "status"),
        Index("ix_creator_applications_requested_handle", "requested_handle"),
        Index("ix_creator_applications_platform", "platform"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    requested_handle: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False)
    profile_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    follower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    selfie_attachment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    social_links_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_history_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CreatorApplication",
    "CREATOR_APPLICATION_NOT_APPLIED",
    "CREATOR_APPLICATION_PENDING",
    "CREATOR_APPLICATION_ADDITIONAL_INFO",
    "CREATOR_APPLICATION_VERIFICATION_REQUESTED",
    "CREATOR_APPLICATION_APPROVED",
    "CREATOR_APPLICATION_REJECTED",
    "CREATOR_APPLICATION_SUSPENDED",
]
