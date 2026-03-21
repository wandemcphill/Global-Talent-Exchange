from __future__ import annotations

from datetime import date

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerInjuryCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_injury_cases"

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, default="minor", server_default="minor", index=True)
    injury_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expected_return_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    recovered_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_match_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recovery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_availability_sync_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
