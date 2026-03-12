from __future__ import annotations

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerLifecycleEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_lifecycle_events"

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    event_status: Mapped[str] = mapped_column(String(24), nullable=False, default="recorded", server_default="recorded", index=True)
    occurred_on: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    effective_from: Mapped[Date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[str] = mapped_column(String(200), nullable=False)
    details_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
