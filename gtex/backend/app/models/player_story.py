from __future__ import annotations

from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class PlayerStory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "player_stories"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_stories_player_id"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    narrative_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


__all__ = ["PlayerStory"]
