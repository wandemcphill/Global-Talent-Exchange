from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorLeaderboardSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_leaderboard_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "scope", "rank", name="uq_creator_leaderboard_snapshot_rank"),
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False, default="global", server_default="global")
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    total_signups: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    qualified_joins: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    active_participants: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    retained_users: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    approved_reward_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=Decimal("0.0000"),
        server_default="0",
    )
