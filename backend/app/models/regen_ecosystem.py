from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class YouthAcademy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "youth_academies"
    __table_args__ = (
        UniqueConstraint("club_user_id", name="uq_youth_academies_club_user_id"),
        Index("ix_youth_academies_club_id", "club_id"),
    )

    club_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    scouting_regions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=6, server_default="6")
    upgrade_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=100_000, server_default="100000")


class Scout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_scouts"
    __table_args__ = (
        Index("ix_regen_scouts_club_user_id", "club_user_id"),
        Index("ix_regen_scouts_club_id", "club_id"),
        Index("ix_regen_scouts_region", "region"),
    )

    club_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    region: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    specialty: Mapped[str] = mapped_column(String(48), nullable=False, default="youth", server_default="youth")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenAttributeProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_attribute_profiles"
    __table_args__ = (
        UniqueConstraint("regen_profile_id", name="uq_regen_attribute_profiles_regen_profile_id"),
        UniqueConstraint("player_id", name="uq_regen_attribute_profiles_player_id"),
        Index("ix_regen_attribute_profiles_rarity_tier", "rarity_tier"),
        Index("ix_regen_attribute_profiles_market_value_coin", "market_value_coin"),
    )

    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    visible_stats_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    hidden_stats_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    personality_state_json: Mapped[dict[str, int | float | str | bool]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    injury_risk: Mapped[float] = mapped_column(Float, nullable=False, default=20.0, server_default="20.0")
    injury_history_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    rarity_tier: Mapped[str] = mapped_column(String(24), nullable=False, default="common", server_default="common")
    uniqueness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    badge_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    market_value_coin: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_potential_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenBloodlineLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_bloodline_links"
    __table_args__ = (
        UniqueConstraint("regen_profile_id", name="uq_regen_bloodline_links_regen_profile_id"),
        Index("ix_regen_bloodline_links_parent_legacy_id", "parent_legacy_id"),
    )

    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_legacy_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_legacy_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    lineage_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CareerEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "career_events"
    __table_args__ = (
        Index("ix_career_events_player_id", "player_id"),
        Index("ix_career_events_regen_profile_id", "regen_profile_id"),
        Index("ix_career_events_type", "type"),
        Index("ix_career_events_occurred_on", "occurred_on"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    impact_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_agents"
    __table_args__ = (Index("ix_regen_agents_name", "name"),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    negotiation_skill: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    player_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenAwardVote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_award_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "player_id", "award_id", "season_id", name="uq_regen_award_votes_scope"),
        Index("ix_regen_award_votes_award_id", "award_id"),
        Index("ix_regen_award_votes_player_id", "player_id"),
        Index("ix_regen_award_votes_season_id", "season_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
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
    voted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class NationalRegenSeed(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_regen_seeds"
    __table_args__ = (
        UniqueConstraint("seed_key", name="uq_national_regen_seeds_seed_key"),
        Index("ix_national_regen_seeds_country_code", "country_code"),
        Index("ix_national_regen_seeds_age_band", "age_band"),
        Index("ix_national_regen_seeds_seed_type", "seed_type"),
        Index("ix_national_regen_seeds_rarity_tier", "rarity_tier"),
        Index("ix_national_regen_seeds_status", "status"),
        Index(
            "ix_national_regen_seeds_country_age_band_position_status",
            "country_code",
            "age_band",
            "primary_position",
            "status",
        ),
    )

    seed_key: Mapped[str] = mapped_column(String(96), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    age_band: Mapped[str] = mapped_column(String(16), nullable=False, default="senior", server_default="senior")
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    confederation_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    seed_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default="preseeded_national_pool", server_default="preseeded_national_pool"
    )
    generation_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    current_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    potential_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    growth_curve: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, server_default="0.5")
    personality_seed_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    rarity_tier: Mapped[str] = mapped_column(String(24), nullable=False, default="common", server_default="common")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="available", server_default="available")
    preseed_batch: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="system_start",
        server_default="system_start",
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "Agent",
    "CareerEvent",
    "NationalRegenSeed",
    "RegenAttributeProfile",
    "RegenAwardVote",
    "RegenBloodlineLink",
    "Scout",
    "YouthAcademy",
]
