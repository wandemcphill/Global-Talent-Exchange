from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ManagerScoutingProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_scouting_profiles"
    __table_args__ = (
        UniqueConstraint("club_id", "manager_code", name="uq_manager_scouting_profiles_club_manager"),
        Index("ix_manager_scouting_profiles_club_id", "club_id"),
        Index("ix_manager_scouting_profiles_persona_code", "persona_code"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_code: Mapped[str] = mapped_column(String(64), nullable=False)
    manager_name: Mapped[str] = mapped_column(String(160), nullable=False)
    persona_code: Mapped[str] = mapped_column(String(48), nullable=False, default="balanced", server_default="balanced")
    preferred_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    youth_bias: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    market_bias: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    tactical_bias: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    star_bias: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    accuracy_boost_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class ScoutingNetwork(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scouting_networks"
    __table_args__ = (
        UniqueConstraint("club_id", "network_name", name="uq_scouting_networks_club_name"),
        Index("ix_scouting_networks_club_id", "club_id"),
        Index("ix_scouting_networks_region_code", "region_code"),
        Index("ix_scouting_networks_specialty_code", "specialty_code"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("manager_scouting_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    network_name: Mapped[str] = mapped_column(String(160), nullable=False)
    region_code: Mapped[str] = mapped_column(String(64), nullable=False)
    region_name: Mapped[str] = mapped_column(String(160), nullable=False)
    specialty_code: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="standard", server_default="standard")
    scout_identity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scout_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=55, server_default="55")
    weekly_cost_coin: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    report_cadence_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class ScoutingNetworkAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scouting_network_assignments"
    __table_args__ = (
        Index("ix_scouting_network_assignments_network_id", "network_id"),
        Index("ix_scouting_network_assignments_club_id", "club_id"),
        Index("ix_scouting_network_assignments_status", "status"),
    )

    network_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scouting_networks.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_name: Mapped[str] = mapped_column(String(160), nullable=False)
    assignment_scope: Mapped[str] = mapped_column(String(48), nullable=False, default="region", server_default="region")
    territory_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    focus_position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age_band_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_band_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_profile: Mapped[str | None] = mapped_column(String(48), nullable=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class ScoutMission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scout_missions"
    __table_args__ = (
        Index("ix_scout_missions_club_id", "club_id"),
        Index("ix_scout_missions_network_id", "network_id"),
        Index("ix_scout_missions_status", "status"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    network_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scouting_networks.id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("manager_scouting_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    mission_name: Mapped[str] = mapped_column(String(180), nullable=False)
    mission_type: Mapped[str] = mapped_column(String(48), nullable=False, default="standard_assignment", server_default="standard_assignment")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled", server_default="scheduled")
    target_position: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_limit_coin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    affordability_tier: Mapped[str | None] = mapped_column(String(48), nullable=True)
    mission_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=21, server_default="21")
    talent_type: Mapped[str] = mapped_column(String(48), nullable=False, default="balanced", server_default="balanced")
    include_academy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    system_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class ScoutReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "scout_reports"
    __table_args__ = (
        Index("ix_scout_reports_mission_id", "mission_id"),
        Index("ix_scout_reports_network_id", "network_id"),
        Index("ix_scout_reports_regen_profile_id", "regen_profile_id"),
        Index("ix_scout_reports_club_id", "club_id"),
    )

    mission_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scout_missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    network_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scouting_networks.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    academy_candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("academy_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("ingestion_players.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    lifecycle_phase: Mapped[str] = mapped_column(String(48), nullable=False)
    confidence_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    fit_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    potential_signal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    value_signal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    hidden_gem_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    current_ability_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    future_potential_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    value_hint_coin: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class HiddenPotentialEstimate(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "hidden_potential_estimates"
    __table_args__ = (
        UniqueConstraint("scout_report_id", name="uq_hidden_potential_estimates_report_id"),
        Index("ix_hidden_potential_estimates_regen_profile_id", "regen_profile_id"),
        Index("ix_hidden_potential_estimates_club_id", "club_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    network_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scouting_networks.id", ondelete="CASCADE"),
        nullable=False,
    )
    mission_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scout_missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    scout_report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scout_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    regen_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("regen_profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    academy_candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("academy_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_ability_low: Mapped[int] = mapped_column(Integer, nullable=False)
    current_ability_high: Mapped[int] = mapped_column(Integer, nullable=False)
    future_potential_low: Mapped[int] = mapped_column(Integer, nullable=False)
    future_potential_high: Mapped[int] = mapped_column(Integer, nullable=False)
    scout_confidence_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    uncertainty_band: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_phase: Mapped[str] = mapped_column(String(48), nullable=False)
    revealed_by_persona: Mapped[str] = mapped_column(String(48), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AcademySupplySignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academy_supply_signals"
    __table_args__ = (
        UniqueConstraint("club_id", "batch_id", "signal_type", name="uq_academy_supply_signals_club_batch_type"),
        Index("ix_academy_supply_signals_club_id", "club_id"),
        Index("ix_academy_supply_signals_batch_id", "batch_id"),
    )

    club_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("academy_intake_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_type: Mapped[str] = mapped_column(String(48), nullable=False, default="academy_pipeline", server_default="academy_pipeline")
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    standout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    average_potential_high: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    visibility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    signal_status: Mapped[str] = mapped_column(String(32), nullable=False, default="visible", server_default="visible")
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerLifecycleProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_lifecycle_profiles"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_lifecycle_profiles_player_id"),
        Index("ix_player_lifecycle_profiles_club_id", "club_id"),
        Index("ix_player_lifecycle_profiles_phase", "phase"),
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
    club_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    phase: Mapped[str] = mapped_column(String(48), nullable=False)
    phase_source: Mapped[str] = mapped_column(String(48), nullable=False, default="age_curve", server_default="age_curve")
    age_years: Mapped[int] = mapped_column(Integer, nullable=False)
    lifecycle_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_desirability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    planning_horizon_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12, server_default="12")
    development_confidence_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=5000, server_default="5000")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class TalentDiscoveryBadge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "talent_discovery_badges"
    __table_args__ = (
        UniqueConstraint("club_id", "regen_profile_id", "badge_code", name="uq_talent_discovery_badges_club_regen_code"),
        Index("ix_talent_discovery_badges_club_id", "club_id"),
        Index("ix_talent_discovery_badges_regen_profile_id", "regen_profile_id"),
        Index("ix_talent_discovery_badges_badge_code", "badge_code"),
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
    academy_candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("academy_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    badge_code: Mapped[str] = mapped_column(String(80), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(180), nullable=False)
    evidence_level: Mapped[str] = mapped_column(String(48), nullable=False, default="emerging", server_default="emerging")
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "AcademySupplySignal",
    "HiddenPotentialEstimate",
    "ManagerScoutingProfile",
    "PlayerLifecycleProfile",
    "ScoutMission",
    "ScoutReport",
    "ScoutingNetwork",
    "ScoutingNetworkAssignment",
    "TalentDiscoveryBadge",
]
