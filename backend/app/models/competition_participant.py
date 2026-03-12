from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CompetitionParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_participants"
    __table_args__ = (
        UniqueConstraint("competition_id", "club_id", name="uq_competition_participants_competition_club"),
    )

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="joined", server_default="joined")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    paid_entry_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
