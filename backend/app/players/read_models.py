from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class PlayerSummaryReadModel(TimestampMixin, Base):
    __tablename__ = "player_summary_read_models"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        primary_key=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    current_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_competition_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_competition_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    last_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_value_credits: Mapped[float] = mapped_column(Float, nullable=False)
    previous_value_credits: Mapped[float] = mapped_column(Float, nullable=False)
    movement_pct: Mapped[float] = mapped_column(Float, nullable=False)
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_interest_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
