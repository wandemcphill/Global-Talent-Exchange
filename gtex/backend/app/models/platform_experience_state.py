from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class PlatformExperienceState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_experience_states"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_platform_experience_states_user_device"),
        Index("ix_platform_experience_states_user_id", "user_id"),
        Index("ix_platform_experience_states_mode", "mode"),
        Index("ix_platform_experience_states_last_watch_at", "last_watch_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="mobile", server_default="mobile")
    current_match_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_channel_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    resume_position_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    commentary_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_watch_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    watch_history_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PlatformExperienceState"]
