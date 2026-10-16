from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionProgressProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_progress_profiles"

    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    resolved_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ranking_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_championships: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_podiums: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_competitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_earnings_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    best_placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    badges_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    titles_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionProgressProfile"]
