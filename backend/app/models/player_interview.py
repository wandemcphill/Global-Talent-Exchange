from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerInterview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_interviews"

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
    interview_type: Mapped[str] = mapped_column(String(32), nullable=False, default="post_match", server_default="post_match")
    sentiment: Mapped[str] = mapped_column(String(24), nullable=False, default="composed", server_default="composed")
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PlayerInterview"]
