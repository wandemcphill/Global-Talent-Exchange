from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CalendarSeason(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_seasons"
    __table_args__ = (UniqueConstraint("season_key", name="uq_calendar_seasons_season_key"),)

    season_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class CalendarEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("event_key", name="uq_calendar_events_event_key"),)

    season_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("calendar_seasons.id", ondelete="SET NULL"), nullable=True, index=True)
    event_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    family: Mapped[str] = mapped_column(String(48), nullable=False, default="general", index=True)
    age_band: Mapped[str] = mapped_column(String(16), nullable=False, default="senior", index=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    exclusive_windows: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pause_other_gtx_competitions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="public")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class CompetitionLifecycleRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_lifecycle_runs"

    event_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_title: Mapped[str] = mapped_column(String(200), nullable=False)
    competition_format: Mapped[str] = mapped_column(String(32), nullable=False, default="cup")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned", index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="registration", index=True)
    generated_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_dates_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    launched_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
