from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema


class ManagerScoutingProfileView(CommonSchema):
    id: str
    club_id: str
    manager_code: str
    manager_name: str
    persona_code: str
    preferred_system: str | None = None
    youth_bias: float
    market_bias: float
    tactical_bias: float
    star_bias: float
    accuracy_boost_bps: int
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoutingNetworkView(CommonSchema):
    id: str
    club_id: str
    manager_profile_id: str | None = None
    network_name: str
    region_code: str
    region_name: str
    specialty_code: str
    quality_tier: str
    scout_identity: str | None = None
    scout_rating: int
    weekly_cost_coin: int
    report_cadence_days: int
    active: bool
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoutingNetworkAssignmentView(CommonSchema):
    id: str
    network_id: str
    club_id: str
    assignment_name: str
    assignment_scope: str
    territory_code: str | None = None
    focus_position: str | None = None
    age_band_min: int | None = None
    age_band_max: int | None = None
    budget_profile: str | None = None
    starts_on: date
    ends_on: date | None = None
    status: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoutMissionView(CommonSchema):
    id: str
    club_id: str
    network_id: str
    manager_profile_id: str | None = None
    mission_name: str
    mission_type: str
    status: str
    target_position: str | None = None
    target_region: str | None = None
    target_age_min: int | None = None
    target_age_max: int | None = None
    budget_limit_coin: int | None = None
    affordability_tier: str | None = None
    mission_duration_days: int
    talent_type: str
    include_academy: bool
    system_profile: str | None = None
    completed_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoutReportView(CommonSchema):
    id: str
    mission_id: str
    network_id: str
    club_id: str
    regen_profile_id: str | None = None
    academy_candidate_id: str | None = None
    player_id: str | None = None
    recommendation_rank: int
    lifecycle_phase: str
    confidence_bps: int
    fit_score: float
    potential_signal_score: float
    value_signal_score: float
    hidden_gem_signal: bool
    current_ability_estimate: int
    future_potential_estimate: int
    value_hint_coin: int | None = None
    summary_text: str
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class HiddenPotentialEstimateView(CommonSchema):
    id: str
    club_id: str
    network_id: str
    mission_id: str
    scout_report_id: str
    regen_profile_id: str | None = None
    academy_candidate_id: str | None = None
    current_ability_low: int
    current_ability_high: int
    future_potential_low: int
    future_potential_high: int
    scout_confidence_bps: int
    uncertainty_band: int
    lifecycle_phase: str
    revealed_by_persona: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class AcademySupplySignalView(CommonSchema):
    id: str
    club_id: str
    batch_id: str | None = None
    signal_type: str
    candidate_count: int
    standout_count: int
    average_potential_high: float
    visibility_score: float
    signal_status: str
    summary_text: str
    metadata: dict[str, object] = Field(default_factory=dict)


class PlayerLifecycleProfileView(CommonSchema):
    id: str
    player_id: str
    regen_profile_id: str | None = None
    club_id: str | None = None
    phase: str
    phase_source: str
    age_years: int
    lifecycle_age_months: int | None = None
    market_desirability: float
    planning_horizon_months: int
    development_confidence_bps: int
    metadata: dict[str, object] = Field(default_factory=dict)


class TalentDiscoveryBadgeView(CommonSchema):
    id: str
    club_id: str
    regen_profile_id: str
    academy_candidate_id: str | None = None
    badge_code: str
    badge_name: str
    evidence_level: str
    summary_text: str
    awarded_at: datetime
    metadata: dict[str, object] = Field(default_factory=dict)


class CompletedScoutMissionView(CommonSchema):
    mission: ScoutMissionView
    reports: tuple[ScoutReportView, ...] = Field(default_factory=tuple)
    hidden_potential_estimates: tuple[HiddenPotentialEstimateView, ...] = Field(default_factory=tuple)
    academy_supply_signals: tuple[AcademySupplySignalView, ...] = Field(default_factory=tuple)
    awarded_badges: tuple[TalentDiscoveryBadgeView, ...] = Field(default_factory=tuple)


__all__ = [
    "AcademySupplySignalView",
    "CompletedScoutMissionView",
    "HiddenPotentialEstimateView",
    "ManagerScoutingProfileView",
    "PlayerLifecycleProfileView",
    "ScoutMissionView",
    "ScoutReportView",
    "ScoutingNetworkAssignmentView",
    "ScoutingNetworkView",
    "TalentDiscoveryBadgeView",
]
