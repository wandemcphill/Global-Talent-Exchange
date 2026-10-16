from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubDynastyMilestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_dynasty_milestones"
    __table_args__ = (
        UniqueConstraint(
            "club_id",
            "milestone_type",
            "required_value",
            name="uq_club_dynasty_milestones_club_type_required",
        ),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    milestone_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    required_value: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dynasty_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
