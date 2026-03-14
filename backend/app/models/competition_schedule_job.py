from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionScheduleJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_schedule_jobs"

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned", server_default="planned", index=True)
    requested_start_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    requested_dates_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assigned_dates_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    schedule_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    preview_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    alignment_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    alignment_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alignment_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_exclusive_windows: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionScheduleJob"]
