from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClipModerationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clip_moderation_events"
    __table_args__ = (
        Index("ix_clip_moderation_events_clip_id", "clip_id"),
        Index("ix_clip_moderation_events_status", "status"),
    )

    clip_id: Mapped[str] = mapped_column(String(160), nullable=False)
    reporter_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="reported", server_default="reported")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["ClipModerationEvent"]
