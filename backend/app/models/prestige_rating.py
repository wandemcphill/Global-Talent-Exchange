from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PrestigeRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prestige_ratings"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "scope", "season_key", name="uq_prestige_ratings_entity_scope"),
    )

    entity_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    season_key: Mapped[str] = mapped_column(String(80), nullable=False, default="lifetime", server_default="lifetime", index=True)
    prestige_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    trophies: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    win_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    player_development: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    earnings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    difficulty_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    perception_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    prestige_tier: Mapped[str] = mapped_column(String(24), nullable=False, default="Bronze", server_default="Bronze")
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["PrestigeRating"]
