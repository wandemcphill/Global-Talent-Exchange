from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerFanReaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_fan_reactions"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("news_articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    reaction_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    intensity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    headline: Mapped[str] = mapped_column(String(220), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PlayerFanReaction"]
