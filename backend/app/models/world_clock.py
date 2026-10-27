from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utcnow


class WorldClockState(TimestampMixin, Base):
    __tablename__ = "world_clock_state"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default="default")
    epoch_real_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    virtual_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    progression_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paused_at_virtual_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    virtual_months_per_season: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["WorldClockState"]
