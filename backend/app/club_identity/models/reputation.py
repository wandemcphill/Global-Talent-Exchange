from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class PrestigeTier(str, Enum):
    LOCAL = "Local"
    RISING = "Rising"
    ESTABLISHED = "Established"
    ELITE = "Elite"
    LEGENDARY = "Legendary"
    DYNASTY = "Dynasty"


class ReputationEventType(str, Enum):
    SCORE_DELTA = "score_delta"
    MILESTONE_UNLOCKED = "milestone_unlocked"
    INACTIVITY_DECAY = "inactivity_decay"


class ClubReputationProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_reputation_profile"
    __table_args__ = (UniqueConstraint("club_id", name="uq_club_reputation_profile_club_id"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    current_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    highest_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    prestige_tier: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PrestigeTier.LOCAL.value,
        server_default=PrestigeTier.LOCAL.value,
    )
    total_seasons: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_active_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_rollup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_top_competition_seasons: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    consecutive_league_titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consecutive_continental_titles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_league_titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_continental_qualifications: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_continental_titles: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_world_super_cup_qualifications: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_world_super_cup_titles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    total_top_scorer_awards: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_top_assist_awards: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class ReputationEventLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "reputation_event_log"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    score_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    milestone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    badge_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ReputationSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "reputation_snapshot"
    __table_args__ = (UniqueConstraint("club_id", "season", name="uq_reputation_snapshot_club_season"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score_before: Mapped[int] = mapped_column(Integer, nullable=False)
    season_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    score_after: Mapped[int] = mapped_column(Integer, nullable=False)
    prestige_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    badges: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    milestones: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rolled_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
