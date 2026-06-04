from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.common.schemas.base import CommonSchema

TransferListingStatus = Literal["open", "closed", "sold"]
MarketBidStatus = Literal["pending", "counter", "accepted", "rejected", "withdrawn"]
SquadAvailabilityStatus = Literal["available", "injured", "suspended", "away", "unfit"]
TransferNegotiationStatus = Literal[
    "awaiting_contract_offer",
    "player_delayed",
    "counter_offer",
    "coach_blocked",
    "rejected",
    "collapsed",
    "completed",
]
CoachOpinionStance = Literal["approve", "neutral", "reject"]
AgentResponseCode = Literal["accept", "counter_offer", "stall", "reject"]

MARKET_BID_STATUSES: tuple[MarketBidStatus, ...] = (
    "pending",
    "counter",
    "accepted",
    "rejected",
    "withdrawn",
)
SQUAD_AVAILABILITY_STATUSES: tuple[SquadAvailabilityStatus, ...] = (
    "available",
    "injured",
    "suspended",
    "away",
    "unfit",
)


class TransferMarketPlayerView(CommonSchema):
    id: str
    full_name: str
    normalized_position: str | None = None
    current_club_id: str | None = None
    current_club_name: str | None = None
    current_competition_id: str | None = None


class MarketClubRefDTO(CommonSchema):
    id: str
    name: str | None = None


class MarketPlayerDTO(CommonSchema):
    id: str
    name: str
    age: int | None = Field(default=None, ge=0)
    position: str | None = None
    club: MarketClubRefDTO | None = None
    nationality: str | None = None
    value: Decimal | None = Field(default=None, ge=0)
    availability: SquadAvailabilityStatus = "available"
    contract_end: date | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    listing_id: str | None = None
    listing_status: TransferListingStatus | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    current_highest_bid: Decimal | None = Field(default=None, ge=0)
    bid_count: int = Field(default=0, ge=0)
    checkout_eligible: bool = False
    blocked_reason: str | None = None


class MarketPlayerPageDTO(CommonSchema):
    items: list[MarketPlayerDTO] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    has_next: bool = False
    pagination_mode: Literal["page"] = "page"


class MarketBidEventDTO(CommonSchema):
    id: str
    type: str
    timestamp: datetime
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketBidDTO(CommonSchema):
    id: str
    player_id: str
    listing_id: str | None = None
    from_club: MarketClubRefDTO | None = None
    to_club: MarketClubRefDTO | None = None
    amount: Decimal = Field(ge=0)
    status: MarketBidStatus
    created_at: datetime
    expires_at: datetime | None = None
    events: list[MarketBidEventDTO] = Field(default_factory=list)
    wallet_reservation_status: str | None = None
    wallet_reserved_amount: Decimal | None = Field(default=None, ge=0)
    wallet_reservation_reference: str | None = None


class MarketBasketItemDTO(CommonSchema):
    player_id: str
    added_at: datetime
    checkout_eligible: bool
    blocked_reason: str | None = None
    listing_id: str | None = None
    player: MarketPlayerDTO | None = None


class MarketBasketDTO(CommonSchema):
    items: list[MarketBasketItemDTO] = Field(default_factory=list)
    count: int = Field(ge=0)


class MarketCheckoutReadinessDTO(CommonSchema):
    ready: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    items: list[MarketBasketItemDTO] = Field(default_factory=list)


class MarketCheckoutSubmitRequest(CommonSchema):
    idempotency_key: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class MarketCheckoutSubmissionDTO(CommonSchema):
    ready: bool
    audit_ref: str
    blocked_reasons: list[str] = Field(default_factory=list)
    items: list[MarketBasketItemDTO] = Field(default_factory=list)


class MarketBidWithdrawRequest(CommonSchema):
    reason: str | None = Field(default=None, max_length=500)


class TransferActivityDTO(CommonSchema):
    id: str
    type: str
    from_club: MarketClubRefDTO | None = None
    to_club: MarketClubRefDTO | None = None
    player: MarketPlayerDTO | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    timestamp: datetime
    status: str
    bid_id: str | None = None
    listing_id: str | None = None


class MarketValueBracketDTO(CommonSchema):
    label: str
    min_value: Decimal | None = Field(default=None, ge=0)
    max_value: Decimal | None = Field(default=None, ge=0)


class MarketFilterMetaDTO(CommonSchema):
    positions: list[str] = Field(default_factory=list)
    nationalities: list[str] = Field(default_factory=list)
    age_range: dict[str, int | None] = Field(default_factory=dict)
    value_brackets: list[MarketValueBracketDTO] = Field(default_factory=list)
    availability_types: list[SquadAvailabilityStatus] = Field(default_factory=list)
    bid_statuses: list[MarketBidStatus] = Field(default_factory=list)
    pagination_mode: Literal["page"] = "page"
    default_page_size: int = Field(default=20, ge=1)
    max_page_size: int = Field(default=100, ge=1)


class MarketBasketAddRequest(CommonSchema):
    player_id: str = Field(min_length=1, max_length=36)


class TransferBidderView(CommonSchema):
    bid_id: str
    club_id: str
    club_name: str | None = None
    amount: Decimal
    timestamp: datetime
    is_highest: bool = False
    wallet_reservation_status: str | None = None
    wallet_reserved_amount: Decimal | None = None
    wallet_reservation_reference: str | None = None


class PlayerDecisionView(CommonSchema):
    interest_level: str
    concerns: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    action: Literal["accept", "reject", "delay"]
    decision_score: float = Field(ge=0, le=100)
    component_scores: dict[str, float] = Field(default_factory=dict)


class CoachOpinionView(CommonSchema):
    stance: CoachOpinionStance
    reason: str
    tactical_fit: float = Field(ge=0, le=100)
    squad_depth_fit: float = Field(ge=0, le=100)
    personality_fit: float = Field(ge=0, le=100)


class AgentNegotiationView(CommonSchema):
    action: AgentResponseCode
    demands: list[str] = Field(default_factory=list)
    clauses: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class TransferNegotiationView(CommonSchema):
    id: str
    listing_id: str
    winning_bid_id: str | None = None
    player_id: str
    selling_club_id: str
    bidder_club_id: str
    status: TransferNegotiationStatus
    wage_offer_amount: Decimal | None = None
    contract_years: int = Field(ge=1, le=5)
    expected_role: str | None = None
    player_decision: PlayerDecisionView | None = None
    coach_opinion: CoachOpinionView | None = None
    agent_negotiation: AgentNegotiationView | None = None
    concerns: list[str] = Field(default_factory=list)
    decision_due_at: datetime | None = None
    resolved_at: datetime | None = None
    lifecycle_transfer_bid_id: str | None = None
    player_contract_id: str | None = None


class TransferListingView(CommonSchema):
    id: str
    window_id: str | None = None
    player_id: str
    selling_club_id: str
    base_price: Decimal
    current_highest_bid: Decimal
    highest_bidder_id: str | None = None
    status: TransferListingStatus
    expires_at: datetime
    time_remaining: int = Field(ge=0)
    player: TransferMarketPlayerView
    current_bid: TransferBidderView | None = None
    bidders: list[TransferBidderView] = Field(default_factory=list)
    watchlist_count: int = Field(default=0, ge=0)
    bid_count: int = Field(default=0, ge=0)
    suggested_price: Decimal
    market_signal: str
    channel: str
    negotiation_id: str | None = None


class TransferMarketStreamEventView(CommonSchema):
    event_id: str
    event_type: str
    created_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class TransferMarketStateView(CommonSchema):
    listing_id: str
    channel: str
    status: TransferListingStatus | str
    event_count: int = Field(default=0, ge=0)
    snapshot: TransferListingView | None = None


class PlayerDecisionProfileView(CommonSchema):
    id: str
    player_id: str
    preferred_leagues_json: list[str] = Field(default_factory=list)
    preferred_play_style: str | None = None
    wage_expectation_amount: Decimal
    ambition_level: int = Field(ge=0, le=100)
    happiness: float = Field(ge=0, le=100)
    loyalty: float = Field(ge=0, le=100)
    ambition: float = Field(ge=0, le=100)
    frustration: float = Field(ge=0, le=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoachProfileView(CommonSchema):
    id: str
    club_id: str
    personality_json: dict[str, Any] = Field(default_factory=dict)
    tactical_philosophy: str
    authority_level: float = Field(ge=0, le=100)
    transfer_preference: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoachDemandView(CommonSchema):
    id: str
    coach_profile_id: str | None = None
    club_id: str
    need: str
    urgency: Literal["low", "medium", "high"]
    active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubTeamDynamicsView(CommonSchema):
    id: str
    club_id: str
    leaders_json: list[str] = Field(default_factory=list)
    cliques_json: list[dict[str, Any]] = Field(default_factory=list)
    morale_groups_json: list[dict[str, Any]] = Field(default_factory=list)
    chemistry_risk: float = Field(ge=0, le=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class MarketWatchlistEntryView(CommonSchema):
    id: str
    club_id: str
    player_id: str
    source: str
    discovery_score: float = Field(ge=0, le=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TransferMarketJobRunView(CommonSchema):
    closed_auctions: int = Field(default=0, ge=0)
    completed_transfers: int = Field(default=0, ge=0)
    rejected_negotiations: int = Field(default=0, ge=0)
    collapsed_negotiations: int = Field(default=0, ge=0)


class TransferListingCreateRequest(CommonSchema):
    player_id: str = Field(min_length=1, max_length=36)
    selling_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    base_price: Decimal = Field(ge=0)
    expires_at: datetime
    window_id: str | None = Field(default=None, min_length=1, max_length=36)
    reserve_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class TransferBidPlaceRequest(CommonSchema):
    bidder_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    amount: Decimal = Field(gt=0)
    activity_context: str | None = Field(default=None, max_length=120)


class ContractOfferRequest(CommonSchema):
    bidder_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    wage_offer_amount: Decimal = Field(ge=0)
    contract_years: int = Field(default=3, ge=1, le=5)
    expected_role: str | None = Field(default=None, max_length=40)
    bonus_terms: str | None = Field(default=None, max_length=255)
    release_clause_amount: Decimal | None = Field(default=None, ge=0)
    clauses_json: dict[str, Any] = Field(default_factory=dict)
    contract_starts_on: date | None = None
    notes: str | None = Field(default=None, max_length=500)


class PlayerDecisionProfileUpsertRequest(CommonSchema):
    preferred_leagues_json: list[str] = Field(default_factory=list)
    preferred_play_style: str | None = Field(default=None, max_length=64)
    wage_expectation_amount: Decimal = Field(default=Decimal("0"), ge=0)
    ambition_level: int = Field(default=50, ge=0, le=100)
    happiness: float = Field(default=50, ge=0, le=100)
    loyalty: float = Field(default=50, ge=0, le=100)
    ambition: float = Field(default=50, ge=0, le=100)
    frustration: float = Field(default=0, ge=0, le=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoachProfileUpsertRequest(CommonSchema):
    personality_json: dict[str, Any] = Field(default_factory=dict)
    tactical_philosophy: str = Field(default="balanced", max_length=64)
    authority_level: float = Field(default=50, ge=0, le=100)
    transfer_preference: str = Field(default="balanced", max_length=64)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoachDemandCreateRequest(CommonSchema):
    need: str = Field(min_length=1, max_length=80)
    urgency: Literal["low", "medium", "high"] = "medium"
    active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TeamDynamicsUpsertRequest(CommonSchema):
    leaders_json: list[str] = Field(default_factory=list)
    cliques_json: list[dict[str, Any]] = Field(default_factory=list)
    morale_groups_json: list[dict[str, Any]] = Field(default_factory=list)
    chemistry_risk: float = Field(default=0, ge=0, le=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WatchlistEntryCreateRequest(CommonSchema):
    club_id: str | None = Field(default=None, min_length=1, max_length=36)
    player_id: str = Field(min_length=1, max_length=36)
    source: str = Field(default="scouting", max_length=32)
    discovery_score: float = Field(default=50, ge=0, le=100)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TransferMarketJobRunRequest(CommonSchema):
    reference_at: datetime | None = None


class TransferMarketReservationReleaseRequest(CommonSchema):
    reason: str = Field(min_length=3, max_length=240)
    reference_at: datetime | None = None
