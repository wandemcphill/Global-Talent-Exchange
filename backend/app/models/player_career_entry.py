from __future__ import annotations

from sqlalchemy import Date, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerCareerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_career_entries"

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    club_name: Mapped[str] = mapped_column(String(160), nullable=False)
    season_label: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    squad_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    appearances: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    average_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    honours_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_on: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_on: Mapped[Date | None] = mapped_column(Date, nullable=True)
