from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class FanWarProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_war_profiles"
    __table_args__ = (
        UniqueConstraint("entity_key", name="uq_fan_war_profiles_entity_key"),
        UniqueConstraint("slug", name="uq_fan_war_profiles_slug"),
        Index("ix_fan_war_profiles_profile_type", "profile_type"),
        Index("ix_fan_war_profiles_country_code", "country_code"),
        Index("ix_fan_war_profiles_club_id", "club_id"),
        Index("ix_fan_war_profiles_creator_profile_id", "creator_profile_id"),
    )

    profile_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    creator_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    country_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scoring_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rivalry_profile_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    prestige_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CountryCreatorAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "country_creator_assignments"
    __table_args__ = (
        UniqueConstraint("creator_profile_id", name="uq_country_creator_assignments_creator_profile_id"),
        Index("ix_country_creator_assignments_country_code", "represented_country_code"),
    )

    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    represented_country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    represented_country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    eligible_country_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assignment_rule: Mapped[str] = mapped_column(
        String(48),
        nullable=False,
        default="admin_approved",
        server_default="admin_approved",
    )
    allow_admin_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    assigned_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class NationsCupEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nations_cup_entries"
    __table_args__ = (
        UniqueConstraint("competition_id", "creator_profile_id", name="uq_nations_cup_entries_competition_creator"),
        UniqueConstraint("competition_id", "country_code", name="uq_nations_cup_entries_competition_country"),
        Index("ix_nations_cup_entries_competition_status", "competition_id", "status"),
        Index("ix_nations_cup_entries_group_key", "group_key"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("country_creator_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    group_key: Mapped[str | None] = mapped_column(String(24), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="qualified", server_default="qualified")
    fan_energy_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    country_prestige_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creator_prestige_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    fanbase_prestige_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    advanced_to_knockout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    record_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FanWarPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fan_war_points"
    __table_args__ = (
        UniqueConstraint("profile_id", "dedupe_key", name="uq_fan_war_points_profile_dedupe_key"),
        Index("ix_fan_war_points_source_type", "source_type"),
        Index("ix_fan_war_points_awarded_at", "awarded_at"),
        Index("ix_fan_war_points_nations_cup_entry_id", "nations_cup_entry_id"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fan_war_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nations_cup_entry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("nations_cup_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    base_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    weighted_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    engagement_units: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    spend_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    quality_multiplier_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=10000, server_default="10000")
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class NationsCupFanMetric(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nations_cup_fan_metrics"
    __table_args__ = (
        UniqueConstraint("competition_id", "entry_id", name="uq_nations_cup_fan_metrics_competition_entry"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_competitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("nations_cup_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    creator_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    watch_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gift_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    prediction_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tournament_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creator_support_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_support_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    watch_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    gift_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    prediction_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tournament_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    creator_support_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    club_support_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_energy: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    contribution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unique_supporter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class FanbaseRanking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fanbase_rankings"
    __table_args__ = (
        UniqueConstraint("board_type", "period_type", "window_start", "profile_id", name="uq_fanbase_rankings_window_profile"),
        Index("ix_fanbase_rankings_lookup", "board_type", "period_type", "window_start"),
    )

    board_type: Mapped[str] = mapped_column(String(24), nullable=False)
    period_type: Mapped[str] = mapped_column(String(24), nullable=False)
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fan_war_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_type: Mapped[str] = mapped_column(String(24), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    points_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unique_supporters: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    movement: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "CountryCreatorAssignment",
    "FanWarPoint",
    "FanWarProfile",
    "FanbaseRanking",
    "NationsCupEntry",
    "NationsCupFanMetric",
]
