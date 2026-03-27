from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_relationships"
    __table_args__ = (
        UniqueConstraint("player_id", "teammate_player_id", name="uq_player_relationships_pair"),
        Index("ix_player_relationships_player_id", "player_id"),
        Index("ix_player_relationships_teammate_player_id", "teammate_player_id"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    teammate_player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    tactical_fit: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    matches_together: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_match_together_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PlayerRelationship"]
