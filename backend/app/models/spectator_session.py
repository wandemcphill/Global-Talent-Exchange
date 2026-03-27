from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class SpectatorSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "spectator_sessions"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_spectator_sessions_match_user"),
    )

    match_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )


__all__ = ["SpectatorSession"]
