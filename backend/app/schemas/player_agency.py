from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.common.schemas.base import CommonSchema


class AgencyReasonView(CommonSchema):
    code: str
    text: str
    weight: float = 0


class PlayerPersonalityView(CommonSchema):
    ambition: int = Field(ge=0, le=100)
    loyalty: int = Field(ge=0, le=100)
    professionalism: int = Field(ge=0, le=100)
    greed: int = Field(ge=0, le=100)
    temperament: int = Field(ge=0, le=100)
    patience: int = Field(ge=0, le=100)
    adaptability: int = Field(ge=0, le=100)
    competitiveness: int = Field(ge=0, le=100)
    ego: int = Field(ge=0, le=100)
    development_focus: int = Field(ge=0, le=100)
    hometown_affinity: int = Field(ge=0, le=100)
    trophy_hunger: int = Field(ge=0, le=100)
    media_appetite: int = Field(ge=0, le=100)
    default_career_target_band: str


class PlayerAgencyStateView(CommonSchema):
    morale: float = Field(ge=0, le=100)
    happiness: float = Field(ge=0, le=100)
    transfer_appetite: float = Field(ge=0, le=100)
    contract_stance: str
    wage_satisfaction: float = Field(ge=0, le=100)
    playing_time_satisfaction: float = Field(ge=0, le=100)
    development_satisfaction: float = Field(ge=0, le=100)
    club_project_belief: float = Field(ge=0, le=100)
    grievance_count: int = Field(ge=0)
    transfer_request_status: str
    preferred_role_band: str
    career_stage: str
    career_target_band: str
    salary_expectation_amount: Decimal
    promise_memory_json: dict[str, object] = Field(default_factory=dict)
    unmet_expectations_json: list[dict[str, object]] = Field(default_factory=list)
    recent_offer_cooldown_until: datetime | None = None
    next_review_at: datetime | None = None


class AgencyDecisionView(CommonSchema):
    decision_code: str
    decision_score: float
    confidence_band: str
    primary_reasons: tuple[AgencyReasonView, ...] = Field(default_factory=tuple)
    secondary_reasons: tuple[AgencyReasonView, ...] = Field(default_factory=tuple)
    persuading_factors: tuple[str, ...] = Field(default_factory=tuple)
    component_scores: dict[str, float] = Field(default_factory=dict)
    next_review_at: datetime | None = None
    cooldown_until: datetime | None = None


class ContractDecisionView(AgencyDecisionView):
    contract_stance: str


class TransferDecisionView(AgencyDecisionView):
    transfer_request_status: str | None = None


class PlayerAgencySnapshotView(CommonSchema):
    player_id: str
    regen_id: str | None = None
    personality: PlayerPersonalityView
    state: PlayerAgencyStateView
    transfer_request_decision: AgencyDecisionView


class ContractDecisionRequest(CommonSchema):
    offering_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    offered_wage_amount: Decimal = Field(ge=0)
    contract_years: int = Field(ge=1, le=5)
    role_promised: str | None = Field(default=None, max_length=40)
    release_clause_amount: Decimal | None = Field(default=None, ge=0)
    bonus_amount: Decimal | None = Field(default=None, ge=0)
    club_stature: float | None = Field(default=None, ge=0, le=100)
    league_quality: float | None = Field(default=None, ge=0, le=100)
    pathway_to_minutes: float | None = Field(default=None, ge=0, le=100)
    development_opportunity: float | None = Field(default=None, ge=0, le=100)
    squad_congestion: float | None = Field(default=None, ge=0, le=100)
    project_attractiveness: float | None = Field(default=None, ge=0, le=100)
    competition_level: float | None = Field(default=None, ge=0, le=100)
    continental_football: bool | None = None
    is_renewal: bool = False
    requested_on: date | None = None


class TransferDecisionRequest(CommonSchema):
    destination_club_id: str = Field(min_length=1, max_length=36)
    offered_wage_amount: Decimal = Field(ge=0)
    contract_years: int = Field(default=3, ge=1, le=5)
    expected_role: str | None = Field(default=None, max_length=40)
    expected_minutes: float | None = Field(default=None, ge=0, le=100)
    club_stature: float | None = Field(default=None, ge=0, le=100)
    league_quality: float | None = Field(default=None, ge=0, le=100)
    competition_level: float | None = Field(default=None, ge=0, le=100)
    squad_congestion: float | None = Field(default=None, ge=0, le=100)
    development_fit: float | None = Field(default=None, ge=0, le=100)
    geography_score: float | None = Field(default=None, ge=0, le=100)
    continental_football: bool | None = None
    transfer_denied_recently: bool | None = None
    requested_on: date | None = None
