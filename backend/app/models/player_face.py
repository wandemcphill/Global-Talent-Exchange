from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class PlayerFace(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "player_faces"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_faces_player_id"),
        Index("ix_player_faces_avatar_seed", "avatar_seed"),
        Index("ix_player_faces_generated_at", "generated_at"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    avatar_seed: Mapped[str] = mapped_column(String(128), nullable=False)
    facial_features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    hairstyle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skin_tone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accessories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=utcnow,
        onupdate=utcnow,
    )


__all__ = ["PlayerFace"]
