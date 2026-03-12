from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ClubTrophy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_trophies"

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trophy_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    trophy_name: Mapped[str] = mapped_column(String(120), nullable=False)
    competition_source: Mapped[str] = mapped_column(String(120), nullable=False)
    competition_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    season_label: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    campaign_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prestige_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
