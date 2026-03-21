from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubDynastyProgress(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_dynasty_progress"
    __table_args__ = (
        UniqueConstraint("club_id", name="uq_club_dynasty_progress_club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dynasty_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dynasty_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    dynasty_title: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Foundations",
        server_default="Foundations",
    )
    seasons_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consecutive_top_finishes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    participation_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    trophy_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    community_prestige_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_loyalty_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creator_legacy_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_season_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    showcase_summary_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
