from __future__ import annotations

from typing import Any

from sqlalchemy import Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NewsArticle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "news_articles"

    article_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    headline_variants_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    related_match_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    related_player_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    related_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    related_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    perception_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["NewsArticle"]
