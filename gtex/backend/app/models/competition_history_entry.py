from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompetitionHistoryEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_history_entries"
    __table_args__ = (
        UniqueConstraint(
            "competition_id",
            "subject_id",
            name="uq_competition_history_entries_competition_subject",
        ),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_participants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reward_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_rewards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resolved_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_name: Mapped[str] = mapped_column(String(160), nullable=False)
    placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    earnings_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(12), nullable=False, default="credit", server_default="credit")
    reward_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_rewarded", server_default="not_rewarded")
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    badge_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title_awarded: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ranking_points_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["CompetitionHistoryEntry"]
