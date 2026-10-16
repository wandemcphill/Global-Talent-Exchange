from __future__ import annotations

from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.ingestion.models import Player
    from app.models.user import User


def _player_model() -> type["Player"]:
    from app.ingestion.models import Player

    return Player


class PlayerMatchEventType(StrEnum):
    VIEWED = "player_viewed"
    SHORTLISTED = "player_shortlisted"
    SCOUTED = "player_scouted"
    CONTACTED = "player_contacted"


class UserPlayerEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "user_player_events"
    __table_args__ = (
        Index("ix_user_player_events_user_created_at", "user_id", "created_at"),
        Index("ix_user_player_events_player_created_at", "player_id", "created_at"),
        Index("ix_user_player_events_event_type_created_at", "event_type", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    player: Mapped["Player"] = relationship(_player_model, foreign_keys=[player_id])


class PlayerFeatureSnapshot(TimestampMixin, Base):
    __tablename__ = "player_features_snapshot"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dominant_foot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_free_agent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    current_club_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    player: Mapped["Player"] = relationship(_player_model, foreign_keys=[player_id])


class MatchWeight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "match_weights"
    __table_args__ = (
        UniqueConstraint("factor", name="uq_match_weights_factor"),
        Index("ix_match_weights_factor", "factor"),
    )

    factor: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
