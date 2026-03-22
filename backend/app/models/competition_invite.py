from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CompetitionInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_invites"
    __table_args__ = (
        UniqueConstraint("competition_id", "club_id", name="uq_competition_invites_competition_club"),
        UniqueConstraint("invite_code", name="uq_competition_invites_invite_code"),
    )

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    invited_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
