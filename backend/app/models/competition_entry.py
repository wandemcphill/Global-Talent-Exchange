from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_entries"
    __table_args__ = (
        UniqueConstraint("competition_id", "club_id", name="uq_competition_entries_competition_club"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(24), nullable=False, default="direct", server_default="direct")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    invite_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_invites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seed_preference: Mapped[int | None] = mapped_column(nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionEntry"]
