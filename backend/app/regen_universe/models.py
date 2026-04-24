from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class RegenSeason(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_universe_seasons"
    __table_args__ = (
        UniqueConstraint("season_number", name="uq_regen_universe_seasons_season_number"),
        Index("ix_regen_universe_seasons_is_active", "is_active"),
    )

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenAward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_universe_awards"
    __table_args__ = (
        UniqueConstraint("code", name="uq_regen_universe_awards_code"),
        Index("ix_regen_universe_awards_sort_order", "sort_order"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="seasonal", server_default="seasonal")
    ranking_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    eligibility_rules_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    is_regen_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenPerformanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_universe_performance_records"
    __table_args__ = (
        UniqueConstraint("season_id", "subject_key", name="uq_regen_universe_performance_records_season_subject"),
        Index("ix_regen_universe_performance_records_subject_key", "subject_key"),
        Index("ix_regen_universe_performance_records_player_id", "player_id"),
        Index("ix_regen_universe_performance_records_national_seed_id", "national_seed_id"),
        Index("ix_regen_universe_performance_records_position_group", "position_group"),
        Index("ix_regen_universe_performance_records_overall_score", "overall_score"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_universe_seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=True,
    )
    national_seed_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_regen_seeds.id", ondelete="CASCADE"),
        nullable=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_group: Mapped[str] = mapped_column(String(32), nullable=False)
    appearances: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    starts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    minutes_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    clean_sheets: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    matches_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    win_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    competition_importance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    previous_overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    improvement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    forward_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    midfielder_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    defender_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    goalkeeper_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    playmaker_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    scorer_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenRankingSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_universe_ranking_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "season_id",
            "category",
            "subject_key",
            name="uq_regen_universe_ranking_snapshots_category_subject",
        ),
        Index("ix_regen_universe_ranking_snapshots_season_category_rank", "season_id", "category", "rank"),
        Index("ix_regen_universe_ranking_snapshots_subject_key", "subject_key"),
        Index("ix_regen_universe_ranking_snapshots_player_id", "player_id"),
        Index("ix_regen_universe_ranking_snapshots_national_seed_id", "national_seed_id"),
    )

    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_universe_seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=True,
    )
    national_seed_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_regen_seeds.id", ondelete="CASCADE"),
        nullable=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenAwardWinner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_universe_award_winners"
    __table_args__ = (
        UniqueConstraint(
            "award_id",
            "season_id",
            "subject_key",
            name="uq_regen_universe_award_winners_award_season_subject",
        ),
        Index("ix_regen_universe_award_winners_season_id", "season_id"),
        Index("ix_regen_universe_award_winners_subject_key", "subject_key"),
        Index("ix_regen_universe_award_winners_player_id", "player_id"),
        Index("ix_regen_universe_award_winners_national_seed_id", "national_seed_id"),
    )

    award_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_universe_awards.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_universe_seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=True,
    )
    national_seed_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_regen_seeds.id", ondelete="CASCADE"),
        nullable=True,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    ranking_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenHallOfFame(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_universe_hall_of_fame"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_regen_universe_hall_of_fame_player_id"),
        Index("ix_regen_universe_hall_of_fame_legacy_score", "legacy_score"),
        Index("ix_regen_universe_hall_of_fame_peak_rank", "peak_rank"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    total_awards: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    peak_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seasons_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    legacy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenAchievement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_achievements"
    __table_args__ = (
        UniqueConstraint("achievement_key", name="uq_regen_achievements_achievement_key"),
        Index("ix_regen_achievements_subject_key", "subject_key"),
        Index("ix_regen_achievements_player_id", "player_id"),
        Index("ix_regen_achievements_national_seed_id", "national_seed_id"),
        Index("ix_regen_achievements_achievement_type", "achievement_type"),
        Index("ix_regen_achievements_earned_at", "earned_at"),
    )

    achievement_key: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=True,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    national_seed_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_regen_seeds.id", ondelete="CASCADE"),
        nullable=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_universe_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    achievement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenStoryEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_story_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_regen_story_events_event_key"),
        Index("ix_regen_story_events_subject_key", "subject_key"),
        Index("ix_regen_story_events_player_id", "player_id"),
        Index("ix_regen_story_events_national_seed_id", "national_seed_id"),
        Index("ix_regen_story_events_event_type", "event_type"),
        Index("ix_regen_story_events_occurred_at", "occurred_at"),
    )

    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(64), nullable=False)
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=True,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    national_seed_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_regen_seeds.id", ondelete="CASCADE"),
        nullable=True,
    )
    season_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_universe_seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
