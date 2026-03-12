from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubTrophyCabinet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_trophy_cabinets"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_trophy_cabinets_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    featured_trophy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    display_theme_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    showcase_order_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    total_trophies: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
