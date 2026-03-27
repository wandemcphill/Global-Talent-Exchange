from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class MatchEventType(StrEnum):
    GOAL = "goal"
    SHOT = "shot"
    PASS = "pass"
    TACKLE = "tackle"
    FOUL = "foul"
    CARD = "card"
    SUBSTITUTION = "substitution"
    FORMATION_CHANGE = "formation_change"
    CHANCE_CREATED = "chance_created"


class MatchEventTeam(StrEnum):
    HOME = "home"
    AWAY = "away"


class MatchEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "match_events"
    __table_args__ = (
        Index("ix_match_events_match_id_minute_created", "match_id", "minute", "created_at"),
        Index("ix_match_events_match_id_sequence", "match_id", "sequence"),
    )

    match_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[MatchEventType] = mapped_column(
        Enum(MatchEventType, name="match_event_type", native_enum=False),
        nullable=False,
        index=True,
    )
    team: Mapped[MatchEventTeam] = mapped_column(
        Enum(MatchEventTeam, name="match_event_team", native_enum=False),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["MatchEvent", "MatchEventTeam", "MatchEventType"]
