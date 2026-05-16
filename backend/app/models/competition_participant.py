from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class CompetitionParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_participants"
    __table_args__ = (
        UniqueConstraint("competition_id", "club_id", name="uq_competition_participants_competition_club"),
        Index("ix_competition_participants_user_id", "user_id"),
        Index("ix_competition_participants_escrow_status", "escrow_status"),
        Index("ix_competition_participants_wallet_ledger_id", "wallet_ledger_id"),
    )

    competition_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entry_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="joined", server_default="joined")
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    group_key: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    paid_entry_fee_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    entry_fee_currency: Mapped[str] = mapped_column(
        String(12), nullable=False, default="credit", server_default="credit"
    )
    escrow_status: Mapped[str] = mapped_column(String(24), nullable=False, default="none", server_default="none")
    wallet_ledger_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payout_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    draws: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goal_diff: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    advanced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
