from __future__ import annotations

from typing import Any

from sqlalchemy import Date, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class YouthTournament(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "youth_tournaments"

    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    age_limit: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    participants_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    rewards_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fixtures_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    standings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    top_players_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled", server_default="scheduled", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["YouthTournament"]
