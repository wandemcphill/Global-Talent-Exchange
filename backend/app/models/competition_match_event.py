from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class CompetitionMatchEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "competition_match_events"

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    added_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    secondary_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    card_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    highlight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionMatchEvent"]
