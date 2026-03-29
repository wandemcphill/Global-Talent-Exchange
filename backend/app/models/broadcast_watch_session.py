from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class BroadcastWatchSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broadcast_watch_sessions"
    __table_args__ = (
        Index("ix_broadcast_watch_sessions_user_id", "user_id"),
        Index("ix_broadcast_watch_sessions_channel_id", "channel_id"),
        Index("ix_broadcast_watch_sessions_current_match_id", "current_match_id"),
        Index("ix_broadcast_watch_sessions_status", "status"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[str] = mapped_column(String(48), nullable=False)
    current_match_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    watched_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    switch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reward_xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["BroadcastWatchSession"]
