from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerRivalry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_rivalries"
    __table_args__ = (
        UniqueConstraint("player_a_id", "player_b_id", name="uq_player_rivalries_player_pair"),
        Index("ix_player_rivalries_player_a_id", "player_a_id"),
        Index("ix_player_rivalries_player_b_id", "player_b_id"),
        Index("ix_player_rivalries_intensity_score", "intensity_score"),
    )

    player_a_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_b_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    intensity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    history_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PlayerRivalry"]
