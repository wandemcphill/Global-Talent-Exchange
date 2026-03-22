from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.common.enums.contract_status import ContractStatus
from app.common.enums.injury_severity import InjurySeverity
from app.common.enums.transfer_bid_status import TransferBidStatus
from app.common.enums.transfer_window_status import TransferWindowStatus


class CareerEntryView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    club_name: str
    season_label: str
    squad_role: str | None = None
    appearances: int = Field(ge=0)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    average_rating: int | None = None
    honours_json: list[dict[str, object]] = Field(default_factory=list)
    notes: str | None = None
    start_on: date | None = None
    end_on: date | None = None
    updated_at: datetime


class CareerTotalsView(CommonSchema):
    appearances: int = Field(ge=0)
    starts: int = Field(ge=0)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    clean_sheets: int = Field(ge=0)
    saves: int = Field(ge=0)
    minutes: int = Field(ge=0)


class SeasonProgressionView(CommonSchema):
    season_label: str
    competition_id: str | None = None
    competition_name: str | None = None
    club_id: str | None = None
    club_name: str | None = None
    appearances: int = Field(ge=0)
    starts: int = Field(ge=0)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    clean_sheets: int = Field(ge=0)
    saves: int = Field(ge=0)
    minutes: int = Field(ge=0)
    average_rating: float | None = None


class ContractView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    status: ContractStatus
    currency: str = "FanCoin"
    wage_amount: Decimal
    bonus_terms: str | None = None
    release_clause_amount: Decimal | None = None
    signed_on: date
    starts_on: date
    ends_on: date
    extension_option_until: date | None = None
    updated_at: datetime


class ContractSummaryView(CommonSchema):
    active_contract: ContractView | None = None
    status: ContractStatus | None = None
    ends_on: date | None = None
    days_remaining: int | None = None
    expiring_soon: bool = False


class InjuryCaseView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    severity: InjurySeverity
    injury_type: str
    occurred_on: date
    expected_return_on: date | None = None
    recovered_on: date | None = None
    source_match_id: str | None = None
    recovery_days: int | None = None
    notes: str | None = None
    updated_at: datetime


class InjurySummaryView(CommonSchema):
    active: InjuryCaseView | None = None
    total_cases: int = Field(ge=0)
    last_occurred_on: date | None = None
    unavailable_until: date | None = None


class PlayerLifecycleEventView(CommonSchema):
    id: str
    player_id: str
    club_id: str | None = None
    event_type: str
    event_status: str
    occurred_on: date
    effective_from: date | None = None
    effective_to: date | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    summary: str
    details_json: dict[str, object] = Field(default_factory=dict)
    notes: str | None = None
    resolved_at: datetime | None = None
    updated_at: datetime


class PlayerAvailabilityView(CommonSchema):
    player_id: str
    available: bool
    checked_on: date
    active_injury: InjuryCaseView | None = None
    active_suspension: PlayerLifecycleEventView | None = None
    unavailable_until: date | None = None
    suspended_until: date | None = None
    status_reason: str | None = None


class TransferWindowView(CommonSchema):
    id: str
    territory_code: str
    label: str
    status: TransferWindowStatus
    opens_on: date
    closes_on: date
    updated_at: datetime


class TransferBidView(CommonSchema):
    id: str
    window_id: str
    player_id: str
    selling_club_id: str | None = None
    buying_club_id: str | None = None
    status: TransferBidStatus
    bid_amount: Decimal
    wage_offer_amount: Decimal | None = None
    sell_on_clause_pct: Decimal | None = None
    structured_terms_json: dict[str, object] = Field(default_factory=dict)
    notes: str | None = None
    updated_at: datetime


class TransferSummaryView(CommonSchema):
    total_bids: int = Field(ge=0)
    accepted_bids: int = Field(ge=0)
    completed_bids: int = Field(ge=0)
    last_transfer_on: date | None = None
    last_transfer_bid_id: str | None = None
    last_selling_club_id: str | None = None
    last_buying_club_id: str | None = None
    recent_bids: tuple[TransferBidView, ...] = Field(default_factory=tuple)


class PlayerCareerSummaryView(CommonSchema):
    player_id: str
    player_name: str
    current_club_id: str | None = None
    current_club_name: str | None = None
    current_competition_id: str | None = None
    current_competition_name: str | None = None
    totals: CareerTotalsView
    seasonal_progression: tuple[SeasonProgressionView, ...] = Field(default_factory=tuple)
    injury_summary: InjurySummaryView
    contract_summary: ContractSummaryView | None = None
    transfer_summary: TransferSummaryView
    availability: PlayerAvailabilityView


class AvailabilityBadgeView(CommonSchema):
    status: str
    label: str
    available: bool
    until: date | None = None
    reason: str | None = None


class ContractBadgeView(CommonSchema):
    status: str
    label: str
    club_id: str | None = None
    club_name: str | None = None
    ends_on: date | None = None
    days_remaining: int | None = None


class TransferWindowEligibilityView(CommonSchema):
    window_id: str | None = None
    window_label: str | None = None
    territory_code: str | None = None
    window_status: TransferWindowStatus | None = None
    window_open: bool = False
    eligible: bool = False
    reason: str | None = None
    last_bid_status: TransferBidStatus | None = None
    outside_window_exempt: bool = False


class RegenTraitSetView(CommonSchema):
    ambition: int = Field(ge=0, le=100)
    loyalty: int = Field(ge=0, le=100)
    professionalism: int = Field(ge=0, le=100)
    greed: int = Field(ge=0, le=100)
    patience: int = Field(ge=0, le=100)
    hometown_affinity: int = Field(ge=0, le=100)
    trophy_hunger: int = Field(ge=0, le=100)
    media_appetite: int = Field(ge=0, le=100)
    temperament: int = Field(ge=0, le=100)
    adaptability: int = Field(ge=0, le=100)


class RegenSpecialTrainingSummaryView(CommonSchema):
    eligible: bool
    projected_ceiling: int = Field(ge=0)
    current_ceiling: int = Field(ge=0)
    major_used_count: int = Field(ge=0)
    minor_used_count: int = Field(ge=0)
    cooldown_until: date | None = None
    club_season_slots_used: int = Field(ge=0)
    club_concurrent_slots_used: int = Field(ge=0)


class RegenBidEvaluationView(CommonSchema):
    bid_id: str
    buying_club_id: str | None = None
    score: float
    preferred: bool = False
    salary_score: float
    contract_length_score: float = 0
    prestige_score: float
    playing_time_score: float
    development_score: float
    hometown_score: float
    trophy_score: float
    manager_fit_score: float = 0
    ambition_alignment_score: float = 0
    reasons: tuple[str, ...] = Field(default_factory=tuple)


class CurrencyBrandingView(CommonSchema):
    currency_code: str
    display_name: str
    icon_key: str
    accent_color: str
    surface_tone: str


class RegenPressureStateView(CommonSchema):
    current_state: str
    ambition_pressure: float
    transfer_desire: float
    salary_expectation_fancoin_per_year: Decimal
    prestige_dissatisfaction: float
    title_frustration: float
    active_transfer_request: bool = False
    refuses_new_contract: bool = False
    end_of_contract_pressure: bool = False
    pressure_score: float = 0
    unresolved_since: date | None = None
    last_big_club_id: str | None = None


class TeamDynamicsEffectView(CommonSchema):
    active: bool = False
    morale_penalty: float = 0
    chemistry_penalty: float = 0
    tactical_cohesion_penalty: float = 0
    performance_penalty: float = 0
    influences_younger_players: bool = False


class CurrencyConversionQuoteView(CommonSchema):
    quote_id: str | None = None
    required_fancoin: Decimal
    current_fancoin_balance: Decimal
    shortfall_fancoin: Decimal
    current_gtex_balance: Decimal
    direct_gtex_equivalent: Decimal
    gtex_required_for_conversion: Decimal
    conversion_premium_bps: int = Field(ge=0)
    can_cover_shortfall: bool = False
    premium_note: str
    fee_currency: CurrencyBrandingView
    salary_currency: CurrencyBrandingView


class RegenContractOfferMarketView(CommonSchema):
    training_fee_gtex_coin: Decimal
    minimum_salary_fancoin_per_year: Decimal
    visible_offer_count: int = Field(ge=0)
    hidden_competing_salary_amounts: bool = True
    fee_currency: CurrencyBrandingView
    salary_currency: CurrencyBrandingView


class RegenContractOfferView(CommonSchema):
    offer_id: str
    regen_id: str
    offering_club_id: str
    training_fee_gtex_coin: Decimal
    minimum_salary_fancoin_per_year: Decimal
    offered_salary_fancoin_per_year: Decimal | None = None
    contract_years: int = Field(ge=1)
    current_offer_count_visible: int = Field(ge=0)
    decision_deadline: datetime
    status: str
    conversion_quote: CurrencyConversionQuoteView | None = None


class RegenLifecycleView(CommonSchema):
    regen_id: str
    status: str
    lifecycle_phase: str
    lifecycle_age_months: int = Field(ge=0)
    contract_currency: str = "FanCoin"
    retirement_pressure: bool = False
    retired: bool = False
    free_agent: bool = False
    free_agent_since: date | None = None
    previous_club_id: str | None = None
    transfer_listed: bool = False
    agency_message: str | None = None
    personality: RegenTraitSetView
    special_training: RegenSpecialTrainingSummaryView
    pressure_state: RegenPressureStateView | None = None
    team_dynamics: TeamDynamicsEffectView | None = None
    free_agent_offer_count: int = Field(default=0, ge=0)
    offer_market: RegenContractOfferMarketView | None = None


class PlayerOverviewView(CommonSchema):
    player_id: str
    player_name: str
    position: str | None = None
    market_value_eur: float | None = None
    overview_generated_on: date
    career_summary: PlayerCareerSummaryView
    availability_badge: AvailabilityBadgeView
    contract_badge: ContractBadgeView | None = None
    transfer_status: TransferWindowEligibilityView
    regen_summary: RegenLifecycleView | None = None
    recent_events: tuple[PlayerLifecycleEventView, ...] = Field(default_factory=tuple)




class PlayerLifecycleSnapshotView(CommonSchema):
    player_id: str
    player_name: str
    position: str | None = None
    market_value_eur: float | None = None
    snapshot_generated_on: date
    career_summary: PlayerCareerSummaryView
    availability_badge: AvailabilityBadgeView
    contract_badge: ContractBadgeView | None = None
    transfer_status: TransferWindowEligibilityView
    regen_summary: RegenLifecycleView | None = None
    recent_events: tuple[PlayerLifecycleEventView, ...] = Field(default_factory=tuple)


class InjuryCreateRequest(CommonSchema):
    severity: InjurySeverity = InjurySeverity.MINOR
    injury_type: str = Field(min_length=1, max_length=80)
    occurred_on: date | None = None
    expected_return_on: date | None = None
    recovery_days: int | None = Field(default=None, ge=1)
    club_id: str | None = Field(default=None, min_length=1, max_length=36)
    source_match_id: str | None = Field(default=None, min_length=1, max_length=36)
    notes: str | None = Field(default=None, max_length=500)


class InjuryRecoveryRequest(CommonSchema):
    recovered_on: date | None = None
    notes: str | None = Field(default=None, max_length=500)


class ContractCreateRequest(CommonSchema):
    club_id: str | None = Field(default=None, min_length=1, max_length=36)
    status: ContractStatus | None = None
    wage_amount: Decimal = Field(ge=0)
    bonus_terms: str | None = Field(default=None, max_length=255)
    release_clause_amount: Decimal | None = Field(default=None, ge=0)
    signed_on: date | None = None
    starts_on: date
    ends_on: date
    extension_option_until: date | None = None


class ContractRenewRequest(CommonSchema):
    new_ends_on: date
    wage_amount: Decimal | None = Field(default=None, ge=0)
    bonus_terms: str | None = Field(default=None, max_length=255)
    release_clause_amount: Decimal | None = Field(default=None, ge=0)
    extension_option_until: date | None = None


class TransferBidCreateRequest(CommonSchema):
    player_id: str = Field(min_length=1, max_length=36)
    selling_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    buying_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    bid_amount: Decimal = Field(ge=0)
    wage_offer_amount: Decimal | None = Field(default=None, ge=0)
    contract_years: int | None = Field(default=None, ge=1, le=5)
    sell_on_clause_pct: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=500)
    allow_outside_window: bool = False
    exemption_reason: str | None = Field(default=None, max_length=200)


class TransferBidAcceptRequest(CommonSchema):
    contract_ends_on: date
    contract_starts_on: date | None = None
    wage_amount: Decimal | None = Field(default=None, ge=0)
    bonus_terms: str | None = Field(default=None, max_length=255)
    release_clause_amount: Decimal | None = Field(default=None, ge=0)
    signed_on: date | None = None
    extension_option_until: date | None = None


class TransferBidRejectRequest(CommonSchema):
    reason: str | None = Field(default=None, max_length=200)


class RegenTransferListingRequest(CommonSchema):
    listed: bool = True
    reason: str | None = Field(default=None, max_length=240)


class BigClubApproachRequest(CommonSchema):
    approaching_club_id: str = Field(min_length=1, max_length=36)
    notes: str | None = Field(default=None, max_length=240)


class RegenPressureResolutionRequest(CommonSchema):
    resolution_type: Literal[
        "trophy_win",
        "title_challenge",
        "salary_improved",
        "club_ambition",
        "relationship_improved",
        "sale_refused",
        "issues_ignored",
    ]
    salary_raise_pct: float = Field(default=0, ge=0, le=200)
    ambition_signal: float = Field(default=0, ge=0, le=100)
    relationship_boost: float = Field(default=0, ge=0, le=100)
    trophy_credit: float = Field(default=0, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=240)


class RegenSpecialTrainingRequest(CommonSchema):
    package_type: Literal["minor", "major"]
    club_id: str | None = Field(default=None, min_length=1, max_length=36)
    notes: str | None = Field(default=None, max_length=240)


class RegenContractOfferQuoteRequest(CommonSchema):
    offering_club_id: str = Field(min_length=1, max_length=36)
    offered_salary_fancoin_per_year: Decimal = Field(ge=0)
    contract_years: int = Field(ge=1, le=5)


class TransferHeadlineView(CommonSchema):
    category: str
    announcement_tier: str
    headline: str
    detail_text: str
    estimated_transfer_fee_eur: int = Field(ge=0)
    estimated_salary_package_eur: int = Field(ge=0)
    estimated_total_value_eur: int = Field(ge=0)
    transfer_fee_gtex_coin: Decimal
    salary_package_fancoin: Decimal
    fee_currency: CurrencyBrandingView
    salary_currency: CurrencyBrandingView


class RegenBidResolutionView(CommonSchema):
    accepted_bid: TransferBidView
    evaluations: tuple[RegenBidEvaluationView, ...] = Field(default_factory=tuple)
    headline: TransferHeadlineView | None = None
