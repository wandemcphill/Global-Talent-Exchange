from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CompetitionInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_invites"
    __table_args__ = (
        UniqueConstraint("competition_id", "club_id", name="uq_competition_invites_competition_club"),
    )

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    invited_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
