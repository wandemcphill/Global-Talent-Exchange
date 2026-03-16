from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema


class AbilityRangeView(CommonSchema):
    minimum: int
    maximum: int


class RegenOriginView(CommonSchema):
    country_code: str
    region_name: str | None = None
    city_name: str | None = None
    ethnolinguistic_profile: str | None = None
    religion_naming_pattern: str | None = None
    urbanicity: str | None = None


class RegenPersonalityView(CommonSchema):
    temperament: int
    leadership: int
    ambition: int
    loyalty: int
    professionalism: int = 50
    greed: int = 50
    patience: int = 50
    hometown_affinity: int = 50
    trophy_hunger: int = 50
    media_appetite: int = 50
    adaptability: int = 50
    work_rate: int
    flair: int
    resilience: int
    personality_tags: tuple[str, ...] = Field(default_factory=tuple)


class RegenLineageView(CommonSchema):
    relationship_type: str
    related_legend_type: str
    related_legend_ref_id: str
    lineage_country_code: str
    lineage_hometown_code: str | None = None
    is_owner_son: bool = False
    is_retired_regen_lineage: bool = False
    is_real_legend_lineage: bool = False
    is_celebrity_lineage: bool = False
    is_celebrity_licensed: bool = False
    lineage_tier: str = "rare"
    narrative_text: str | None = None
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegenProfileView(CommonSchema):
    id: str
    regen_id: str
    club_id: str
    player_id: str | None = None
    linked_unique_card_id: str
    display_name: str
    age: int
    birth_country_code: str
    birth_region: str | None = None
    birth_city: str | None = None
    primary_position: str
    secondary_positions: tuple[str, ...] = Field(default_factory=tuple)
    current_gsi: int
    current_ability_range: AbilityRangeView
    potential_range: AbilityRangeView
    scout_confidence: str
    generation_source: str
    status: str
    is_special_lineage: bool = False
    generated_at: datetime
    club_quality_score: float
    personality: RegenPersonalityView
    origin: RegenOriginView
    lineage: RegenLineageView | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AcademyCandidateView(CommonSchema):
    id: str
    batch_id: str
    club_id: str
    regen_profile_id: str
    display_name: str
    age: int
    nationality_code: str
    birth_region: str | None = None
    birth_city: str | None = None
    primary_position: str
    secondary_position: str | None = None
    current_ability_range: AbilityRangeView
    potential_range: AbilityRangeView
    scout_confidence: str
    status: str
    hometown_club_affinity: str | None = None
    generated_at: datetime
    decision_deadline_on: date | None = None
    free_agency_status: str = "club_control_window"
    platform_capture_share_pct: int = 70
    previous_club_capture_share_pct: int = 30
    special_training_eligible: bool = False


class AcademyIntakeBatchView(CommonSchema):
    id: str
    club_id: str
    season_label: str
    intake_size: int
    academy_quality_score: float
    generated_at: datetime
    candidates: tuple[AcademyCandidateView, ...] = Field(default_factory=tuple)


class StarterRegenBundleView(CommonSchema):
    club_id: str
    season_label: str
    regens: tuple[RegenProfileView, ...] = Field(default_factory=tuple)


class RegenValueSnapshotView(CommonSchema):
    id: str
    regen_id: str
    current_value_coin: int
    ability_component: int
    potential_component: int
    reputation_component: int
    narrative_component: int
    demand_component: int
    guardrail_multiplier: float
    calculated_at: datetime
    metadata: dict[str, object] = Field(default_factory=dict)


class RegenScoutReportView(CommonSchema):
    id: str
    regen_id: str
    club_id: str | None = None
    scout_identity: str | None = None
    manager_style: str
    system_profile: str | None = None
    current_ability_estimate: int
    future_potential_estimate: int
    scout_confidence_bps: int
    role_fit_score: float
    hidden_gem_score: float
    wonderkid_signal: bool = False
    value_hint_coin: int | None = None
    summary_text: str
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class RegenRecommendationItemView(CommonSchema):
    id: str
    regen_id: str
    club_id: str | None = None
    manager_style: str
    premium_tier: str
    position_need: str | None = None
    system_profile: str | None = None
    budget_coin: int | None = None
    priority_score: float
    role_fit_score: float
    market_value_score: float
    summary_text: str
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class RegenSearchResultView(CommonSchema):
    profile: RegenProfileView
    latest_value: RegenValueSnapshotView | None = None
    transfer_listed: bool = False
    contract_expires_on: date | None = None
    wonderkid: bool = False


class RegenTransferSettlementView(CommonSchema):
    regen_id: str
    gross_amount_coin: int
    fee_amount_coin: int
    seller_net_coin: int
    applied_fee_bps: int
    regen_market_share: float
    guardrail_triggered: bool = False


__all__ = [
    "AbilityRangeView",
    "AcademyCandidateView",
    "AcademyIntakeBatchView",
    "RegenLineageView",
    "RegenOriginView",
    "RegenPersonalityView",
    "RegenProfileView",
    "RegenRecommendationItemView",
    "RegenScoutReportView",
    "RegenSearchResultView",
    "RegenTransferSettlementView",
    "RegenValueSnapshotView",
    "StarterRegenBundleView",
]
