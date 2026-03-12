from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema
from backend.app.common.enums.contract_status import ContractStatus
from backend.app.common.enums.injury_severity import InjurySeverity
from backend.app.common.enums.transfer_bid_status import TransferBidStatus
from backend.app.common.enums.transfer_window_status import TransferWindowStatus


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
