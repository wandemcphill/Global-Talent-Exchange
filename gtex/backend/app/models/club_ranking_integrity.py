from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClubRankingEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_ranking_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_club_ranking_events_event_key"),
        Index("ix_club_ranking_events_club_created", "club_id", "created_at"),
        Index("ix_club_ranking_events_competition", "competition_id"),
        Index("ix_club_ranking_events_match", "match_id"),
        Index("ix_club_ranking_events_status", "integrity_status"),
    )

    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    event_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    opponent_club_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    result: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown", server_default="unknown")
    base_points: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    opponent_strength_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("1.0000"), server_default="1"
    )
    competition_size_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("1.0000"), server_default="1"
    )
    competition_tier_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("1.0000"), server_default="1"
    )
    stage_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("1.0000"), server_default="1"
    )
    anti_farm_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("1.0000"), server_default="1"
    )
    placement_bonus: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    raw_points_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    final_points_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    integrity_status: Mapped[str] = mapped_column(String(24), nullable=False, default="clean", server_default="clean")
    reason: Mapped[str] = mapped_column(
        String(255), nullable=False, default="ranked_result", server_default="ranked_result"
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CompetitionIntegrityScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_integrity_scores"
    __table_args__ = (
        UniqueConstraint("competition_id", name="uq_competition_integrity_scores_competition"),
        Index("ix_competition_integrity_scores_review", "review_required"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unique_participants: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    repeated_pair_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    forfeit_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0.0000"), server_default="0"
    )
    suspicious_owner_links: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    quality_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), nullable=False, default=Decimal("100.00"), server_default="100"
    )
    ranking_weight: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("1.0000"), server_default="1"
    )
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ClubRankingAbuseFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "club_ranking_abuse_flags"
    __table_args__ = (
        UniqueConstraint("flag_key", name="uq_club_ranking_abuse_flags_flag_key"),
        Index("ix_club_ranking_abuse_flags_club_status", "club_id", "status"),
        Index("ix_club_ranking_abuse_flags_competition", "competition_id"),
        Index("ix_club_ranking_abuse_flags_type", "flag_type"),
    )

    flag_key: Mapped[str] = mapped_column(String(180), nullable=False)
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = ["ClubRankingAbuseFlag", "ClubRankingEvent", "CompetitionIntegrityScore"]
