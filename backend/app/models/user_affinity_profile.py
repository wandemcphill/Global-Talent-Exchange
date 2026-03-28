from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserAffinityProfile(TimestampMixin, Base):
    __tablename__ = "user_affinity_profiles"
    __table_args__ = (Index("ix_user_affinity_profiles_updated_at", "updated_at"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    favorite_formats_json: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    favorite_creators_json: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    affinity_vector_json: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    avg_watch_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    skip_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    session_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["UserAffinityProfile"]
