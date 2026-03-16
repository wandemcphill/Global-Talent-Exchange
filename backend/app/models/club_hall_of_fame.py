from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ClubHallOfFameEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_hall_of_fame_entries"
    __table_args__ = (
        Index("ix_club_hall_of_fame_entries_club_id", "club_id"),
        Index("ix_club_hall_of_fame_entries_category", "entry_category"),
        Index("ix_club_hall_of_fame_entries_player_id", "player_id"),
        Index("ix_club_hall_of_fame_entries_regen_id", "regen_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_category: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    regen_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_label: Mapped[str] = mapped_column(String(180), nullable=False)
    entry_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stat_line_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    era_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inducted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    source_scope: Mapped[str] = mapped_column(String(48), nullable=False, default="manual", server_default="manual")
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["ClubHallOfFameEntry"]
