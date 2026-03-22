from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class RegenProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_profiles"
    __table_args__ = (
        UniqueConstraint("regen_id", name="uq_regen_profiles_regen_id"),
        UniqueConstraint("player_id", name="uq_regen_profiles_player_id"),
        UniqueConstraint("linked_unique_card_id", name="uq_regen_profiles_linked_unique_card_id"),
        Index("ix_regen_profiles_generated_for_club_id", "generated_for_club_id"),
        Index("ix_regen_profiles_generation_source", "generation_source"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    linked_unique_card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("player_cards.id", ondelete="RESTRICT"),
        nullable=False,
    )
    generated_for_club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    birth_country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    birth_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_positions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    current_gsi: Mapped[int] = mapped_column(Integer, nullable=False)
    current_ability_range_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    potential_range_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    scout_confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_source: Mapped[str] = mapped_column(String(32), nullable=False)
    is_special_lineage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    club_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenPersonalityProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_personality_profiles"
    __table_args__ = (
        UniqueConstraint("regen_profile_id", name="uq_regen_personality_profiles_regen_profile_id"),
    )

    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    temperament: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    leadership: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    ambition: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    loyalty: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    work_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    flair: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    resilience: Mapped[int] = mapped_column(Integer, nullable=False, default=50, server_default="50")
    personality_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RegenOriginMetadata(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_origin_metadata"
    __table_args__ = (
        UniqueConstraint("regen_profile_id", name="uq_regen_origin_metadata_regen_profile_id"),
    )

    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    region_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hometown_club_affinity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ethnolinguistic_profile: Mapped[str | None] = mapped_column(String(80), nullable=True)
    religion_naming_pattern: Mapped[str | None] = mapped_column(String(80), nullable=True)
    urbanicity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenGenerationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_generation_events"
    __table_args__ = (
        Index("ix_regen_generation_events_regen_profile_id", "regen_profile_id"),
        Index("ix_regen_generation_events_club_id", "club_id"),
        Index("ix_regen_generation_events_season_label", "season_label"),
    )

    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    generation_source: Mapped[str] = mapped_column(String(32), nullable=False)
    season_label: Mapped[str] = mapped_column(String(32), nullable=False)
    event_status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated", server_default="generated")
    probability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_roll: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class AcademyIntakeBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_intake_batches"
    __table_args__ = (
        UniqueConstraint("club_id", "season_label", name="uq_academy_intake_batches_club_season"),
        Index("ix_academy_intake_batches_club_id", "club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_label: Mapped[str] = mapped_column(String(32), nullable=False)
    intake_size: Mapped[int] = mapped_column(Integer, nullable=False)
    academy_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated", server_default="generated")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class AcademyCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_candidates"
    __table_args__ = (
        UniqueConstraint("regen_profile_id", name="uq_academy_candidates_regen_profile_id"),
        Index("ix_academy_candidates_batch_id", "batch_id"),
        Index("ix_academy_candidates_club_id", "club_id"),
    )

    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("academy_intake_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    nationality_code: Mapped[str] = mapped_column(String(8), nullable=False)
    birth_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_position: Mapped[str] = mapped_column(String(40), nullable=False)
    secondary_position: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_ability_range_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    potential_range_json: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    scout_confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="academy_candidate", server_default="academy_candidate")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenVisualProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_visual_profiles"
    __table_args__ = (
        UniqueConstraint("regen_profile_id", name="uq_regen_visual_profiles_regen_profile_id"),
    )

    regen_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    portrait_seed: Mapped[str] = mapped_column(String(64), nullable=False)
    skin_tone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hair_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accessory_profile_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    kit_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenValueSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "regen_value_snapshots"
    __table_args__ = (
        Index("ix_regen_value_snapshots_regen_id", "regen_id"),
        Index("ix_regen_value_snapshots_calculated_at", "calculated_at"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_value_coin: Mapped[int] = mapped_column(Integer, nullable=False)
    ability_component: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    potential_component: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reputation_component: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    narrative_component: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    demand_component: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    guardrail_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RegenMarketActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_market_activity"
    __table_args__ = (
        Index("ix_regen_market_activity_regen_id", "regen_id"),
        Index("ix_regen_market_activity_activity_type", "activity_type"),
        Index("ix_regen_market_activity_occurred_at", "occurred_at"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    activity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="competition", server_default="competition")
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    value_delta_coin: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    stat_line_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    narrative_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenScoutReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "regen_scout_reports"
    __table_args__ = (
        Index("ix_regen_scout_reports_regen_id", "regen_id"),
        Index("ix_regen_scout_reports_club_id", "club_id"),
        Index("ix_regen_scout_reports_manager_style", "manager_style"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    scout_identity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    manager_style: Mapped[str] = mapped_column(String(48), nullable=False)
    system_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_ability_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    future_potential_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    scout_confidence_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    role_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    hidden_gem_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    wonderkid_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    value_hint_coin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RegenRecommendationItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "regen_recommendation_items"
    __table_args__ = (
        Index("ix_regen_recommendation_items_regen_id", "regen_id"),
        Index("ix_regen_recommendation_items_club_id", "club_id"),
        Index("ix_regen_recommendation_items_priority_score", "priority_score"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    manager_style: Mapped[str] = mapped_column(String(48), nullable=False)
    premium_tier: Mapped[str] = mapped_column(String(24), nullable=False, default="standard", server_default="standard")
    position_need: Mapped[str | None] = mapped_column(String(32), nullable=True)
    system_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    budget_coin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    role_fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    market_value_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class RegenDemandSignal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "regen_demand_signals"
    __table_args__ = (
        Index("ix_regen_demand_signals_regen_id", "regen_id"),
        Index("ix_regen_demand_signals_signal_type", "signal_type"),
        Index("ix_regen_demand_signals_occurred_at", "occurred_at"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="market", server_default="market")
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    supporting_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    signal_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenOnboardingFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_onboarding_flags"
    __table_args__ = (
        UniqueConstraint("regen_id", name="uq_regen_onboarding_flags_regen_id"),
        Index("ix_regen_onboarding_flags_club_id", "club_id"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    onboarding_type: Mapped[str] = mapped_column(String(32), nullable=False, default="starter_bundle", server_default="starter_bundle")
    squad_bucket: Mapped[str] = mapped_column(String(32), nullable=False, default="first_team", server_default="first_team")
    squad_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_non_tradable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    replacement_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenTransferFeeRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_transfer_fee_rules"
    __table_args__ = (
        UniqueConstraint("rule_key", name="uq_regen_transfer_fee_rules_rule_key"),
    )

    rule_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fee_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    min_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    max_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    regen_share_soft_cap: Mapped[float] = mapped_column(Float, nullable=False, default=0.20, server_default="0.20")
    elite_regen_share_cap: Mapped[float] = mapped_column(Float, nullable=False, default=0.08, server_default="0.08")
    demand_cooling_floor: Mapped[float] = mapped_column(Float, nullable=False, default=0.55, server_default="0.55")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    policy_source: Mapped[str] = mapped_column(String(32), nullable=False, default="system_default", server_default="system_default")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenLineageProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_lineage_profiles"
    __table_args__ = (
        UniqueConstraint("regen_id", name="uq_regen_lineage_profiles_regen_id"),
        Index("ix_regen_lineage_profiles_relationship_type", "relationship_type"),
        Index("ix_regen_lineage_profiles_related_legend_type", "related_legend_type"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    related_legend_type: Mapped[str] = mapped_column(String(64), nullable=False)
    related_legend_ref_id: Mapped[str] = mapped_column(String(64), nullable=False)
    lineage_country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    lineage_hometown_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_owner_son: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_retired_regen_lineage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_real_legend_lineage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_celebrity_lineage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_celebrity_licensed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    lineage_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="rare", server_default="rare")
    narrative_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenRelationshipTag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_relationship_tags"
    __table_args__ = (
        Index("ix_regen_relationship_tags_regen_id", "regen_id"),
        Index("ix_regen_relationship_tags_tag", "tag"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_text: Mapped[str | None] = mapped_column(String(180), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenAward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_awards"
    __table_args__ = (
        Index("ix_regen_awards_regen_id", "regen_id"),
        Index("ix_regen_awards_award_code", "award_code"),
        Index("ix_regen_awards_awarded_at", "awarded_at"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    award_code: Mapped[str] = mapped_column(String(80), nullable=False)
    award_name: Mapped[str] = mapped_column(String(180), nullable=False)
    award_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    season_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_scope: Mapped[str] = mapped_column(String(48), nullable=False, default="gtex", server_default="gtex")
    impact_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenDiscoveryBadge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_discovery_badges"
    __table_args__ = (
        UniqueConstraint("regen_id", "club_id", "badge_code", name="uq_regen_discovery_badges_regen_club_code"),
        Index("ix_regen_discovery_badges_regen_id", "regen_id"),
        Index("ix_regen_discovery_badges_badge_code", "badge_code"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    badge_code: Mapped[str] = mapped_column(String(80), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(180), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenTwinsGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_twins_group"
    __table_args__ = (
        Index("ix_regen_twins_group_key", "twins_group_key"),
        Index("ix_regen_twins_group_regen_id", "regen_id"),
    )

    twins_group_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    season_label: Mapped[str] = mapped_column(String(32), nullable=False)
    visual_seed: Mapped[str] = mapped_column(String(64), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenLegacyRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_legacy_records"
    __table_args__ = (
        UniqueConstraint("regen_id", name="uq_regen_legacy_records_regen_id"),
        Index("ix_regen_legacy_records_player_id", "player_id"),
        Index("ix_regen_legacy_records_is_legend", "is_legend"),
    )

    regen_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    retired_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    appearances_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    goals_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    assists_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    awards_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    seasons_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    legacy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    legacy_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="standard", server_default="standard")
    is_legend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    narrative_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenUnsettlingEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_unsettling_events"
    __table_args__ = (
        Index("ix_regen_unsettling_events_regen_id", "regen_id"),
        Index("ix_regen_unsettling_events_approaching_club_id", "approaching_club_id"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    current_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    approaching_club_id: Mapped[str] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False)
    previous_state: Mapped[str] = mapped_column(String(48), nullable=False, default="content", server_default="content")
    resulting_state: Mapped[str] = mapped_column(String(48), nullable=False, default="content", server_default="content")
    effect_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    resisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenTransferPressureState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_transfer_pressure_states"
    __table_args__ = (
        UniqueConstraint("regen_id", name="uq_regen_transfer_pressure_states_regen_id"),
        Index("ix_regen_transfer_pressure_states_current_state", "current_state"),
        Index("ix_regen_transfer_pressure_states_current_club_id", "current_club_id"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    current_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    current_state: Mapped[str] = mapped_column(String(48), nullable=False, default="content", server_default="content")
    ambition_pressure: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    transfer_desire: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    prestige_dissatisfaction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    title_frustration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    pressure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    salary_expectation_fancoin_per_year: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    active_transfer_request: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    refuses_new_contract: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    end_of_contract_pressure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    unresolved_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_big_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    last_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenBigClubApproach(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_big_club_approaches"
    __table_args__ = (
        Index("ix_regen_big_club_approaches_regen_id", "regen_id"),
        Index("ix_regen_big_club_approaches_approaching_club_id", "approaching_club_id"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    current_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    approaching_club_id: Mapped[str] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False)
    prestige_gap_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    trophy_gap_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    resistance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    contract_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    effect_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    resisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    resulting_state: Mapped[str] = mapped_column(String(48), nullable=False, default="content", server_default="content")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenTeamDynamicsEffect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_team_dynamics_effects"
    __table_args__ = (
        Index("ix_regen_team_dynamics_effects_regen_id", "regen_id"),
        Index("ix_regen_team_dynamics_effects_club_id", "club_id"),
        Index("ix_regen_team_dynamics_effects_active", "active"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    triggered_state: Mapped[str] = mapped_column(String(48), nullable=False, default="content", server_default="content")
    morale_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    chemistry_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    tactical_cohesion_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    performance_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    influences_younger_players: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    unresolved_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenContractOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_contract_offers"
    __table_args__ = (
        Index("ix_regen_contract_offers_regen_id", "regen_id"),
        Index("ix_regen_contract_offers_offering_club_id", "offering_club_id"),
        Index("ix_regen_contract_offers_status", "status"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    transfer_bid_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("transfer_bids.id", ondelete="SET NULL"), nullable=True)
    offering_club_id: Mapped[str] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=False)
    training_fee_gtex_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    minimum_salary_fancoin_per_year: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    offered_salary_fancoin_per_year: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    contract_years: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    current_offer_count_visible: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    decision_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted", server_default="submitted")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class RegenOfferVisibilityState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regen_offer_visibility_state"
    __table_args__ = (
        UniqueConstraint("regen_id", name="uq_regen_offer_visibility_state_regen_id"),
        Index("ix_regen_offer_visibility_state_offer_count", "visible_offer_count"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    training_fee_gtex_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    minimum_salary_fancoin_per_year: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    visible_offer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_offer_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class CurrencyConversionQuote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "currency_conversion_quotes"
    __table_args__ = (
        Index("ix_currency_conversion_quotes_regen_id", "regen_id"),
        Index("ix_currency_conversion_quotes_owner_user_id", "owner_user_id"),
    )

    regen_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="SET NULL"), nullable=True)
    offering_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_unit: Mapped[str] = mapped_column(String(24), nullable=False, default="coin", server_default="coin")
    target_unit: Mapped[str] = mapped_column(String(24), nullable=False, default="credit", server_default="credit")
    required_target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    available_target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    shortfall_target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    available_source_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    direct_source_equivalent: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    source_amount_required: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    premium_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    can_cover_shortfall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    expires_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TransferHeadlineMediaRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_headline_media_records"
    __table_args__ = (
        Index("ix_transfer_headline_media_records_regen_id", "regen_id"),
        Index("ix_transfer_headline_media_records_buying_club_id", "buying_club_id"),
        Index("ix_transfer_headline_media_records_tier", "announcement_tier"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    buying_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    selling_club_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("club_profiles.id", ondelete="SET NULL"), nullable=True)
    related_entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    related_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    headline_category: Mapped[str] = mapped_column(String(64), nullable=False)
    announcement_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="feed_card", server_default="feed_card")
    estimated_transfer_fee_eur: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    estimated_salary_package_eur: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    estimated_total_value_eur: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    transfer_fee_gtex_coin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    salary_package_fancoin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0")
    headline_text: Mapped[str] = mapped_column(Text, nullable=False)
    detail_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class MajorTransferAnnouncement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "major_transfer_announcements"
    __table_args__ = (
        Index("ix_major_transfer_announcements_regen_id", "regen_id"),
        Index("ix_major_transfer_announcements_tier", "announcement_tier"),
    )

    regen_id: Mapped[str] = mapped_column(String(36), ForeignKey("regen_profiles.id", ondelete="CASCADE"), nullable=False)
    headline_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_headline_media_records.id", ondelete="CASCADE"), nullable=False)
    story_feed_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("story_feed_items.id", ondelete="SET NULL"), nullable=True)
    platform_announcement_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("platform_announcements.id", ondelete="SET NULL"), nullable=True)
    announcement_category: Mapped[str] = mapped_column(String(64), nullable=False)
    announcement_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="feed_card", server_default="feed_card")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published", server_default="published")
    surfaces_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "AcademyCandidate",
    "AcademyIntakeBatch",
    "CurrencyConversionQuote",
    "MajorTransferAnnouncement",
    "RegenDemandSignal",
    "RegenGenerationEvent",
    "RegenBigClubApproach",
    "RegenLineageProfile",
    "RegenMarketActivity",
    "RegenContractOffer",
    "RegenAward",
    "RegenDiscoveryBadge",
    "RegenLegacyRecord",
    "RegenOnboardingFlag",
    "RegenOfferVisibilityState",
    "RegenOriginMetadata",
    "RegenPersonalityProfile",
    "RegenProfile",
    "RegenRelationshipTag",
    "RegenRecommendationItem",
    "RegenScoutReport",
    "RegenTeamDynamicsEffect",
    "RegenTransferFeeRule",
    "RegenTransferPressureState",
    "RegenTwinsGroup",
    "RegenUnsettlingEvent",
    "RegenValueSnapshot",
    "RegenVisualProfile",
    "TransferHeadlineMediaRecord",
]
