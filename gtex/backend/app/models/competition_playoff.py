from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionPlayoff(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_playoffs"

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_rounds.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    slot_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winner_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionPlayoff"]
