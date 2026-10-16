from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.common.schemas.base import CommonSchema

TransferListingStatus = Literal[
    "draft",
    "open",
    "countered",
    "accepted",
    "negotiated",
    "closed",
    "sold",
    "rejected",
    "cancelled",
    "expired",
]
TransferHubListingType = Literal[
    "transfer",
    "loan",
    "swap",
    "swap_plus_cash",
    "loan_to_buy",
    "temporary_rental",
    "open_offer",
    "private_negotiation",
]
TransferHubAssetType = Literal["real_player", "regen", "academy_player"]
TransferHubVisibility = Literal["public", "private", "shortlist", "invite_only"]
TransferHubOfferStatus = Literal["draft", "open", "countered", "accepted", "rejected", "cancelled", "expired"]
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


class TransferMarketPlayerView(CommonSchema):
    id: str
    full_name: str
    normalized_position: str | None = None
    current_club_id: str | None = None
    current_club_name: str | None = None
    current_competition_id: str | None = None
    nationality_id: str | None = None
    market_value: Decimal | None = None
    is_real_player: bool = False


class TransferBidderView(CommonSchema):
    bid_id: str
    club_id: str
    club_name: str | None = None
    amount: Decimal
    timestamp: datetime
    is_highest: bool = False


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
    listing_type: TransferHubListingType = "transfer"
    asset_type: TransferHubAssetType = "real_player"
    visibility: TransferHubVisibility = "public"
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
    salary_amount: Decimal | None = None
    contract_years_remaining: Decimal | None = None
    buy_clause_amount: Decimal | None = None
    loan_terms: dict[str, Any] = Field(default_factory=dict)
    swap_terms: dict[str, Any] = Field(default_factory=dict)
    availability: dict[str, Any] = Field(default_factory=dict)


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
    listing_type: TransferHubListingType = "transfer"
    asset_type: TransferHubAssetType = "real_player"
    visibility: TransferHubVisibility = "public"
    salary_amount: Decimal | None = Field(default=None, ge=0)
    contract_years_remaining: Decimal | None = Field(default=None, ge=0, le=15)
    buy_clause_amount: Decimal | None = Field(default=None, ge=0)
    loan_terms: dict[str, Any] = Field(default_factory=dict)
    swap_terms: dict[str, Any] = Field(default_factory=dict)
    availability: dict[str, Any] = Field(default_factory=dict)


class TransferHubOfferCreateRequest(CommonSchema):
    bidder_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    offer_type: TransferHubListingType = "transfer"
    cash_amount: Decimal = Field(default=Decimal("0"), ge=0)
    offered_player_ids: list[str] = Field(default_factory=list)
    loan_terms: dict[str, Any] = Field(default_factory=dict)
    swap_terms: dict[str, Any] = Field(default_factory=dict)
    conditional_terms: dict[str, Any] = Field(default_factory=dict)
    sell_on_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    message: str | None = Field(default=None, max_length=1000)
    expires_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class TransferHubOfferCounterRequest(CommonSchema):
    cash_amount: Decimal | None = Field(default=None, ge=0)
    offered_player_ids: list[str] | None = None
    loan_terms: dict[str, Any] | None = None
    swap_terms: dict[str, Any] | None = None
    conditional_terms: dict[str, Any] | None = None
    sell_on_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    message: str | None = Field(default=None, max_length=1000)


class TransferHubOfferView(CommonSchema):
    id: str
    listing_id: str
    offer_type: TransferHubListingType | str
    seller_club_id: str
    bidder_club_id: str
    cash_amount: Decimal
    offered_player_ids: list[str] = Field(default_factory=list)
    loan_terms: dict[str, Any] = Field(default_factory=dict)
    swap_terms: dict[str, Any] = Field(default_factory=dict)
    conditional_terms: dict[str, Any] = Field(default_factory=dict)
    sell_on_percentage: Decimal | None = None
    status: TransferHubOfferStatus | str
    idempotency_key: str | None = None
    message: str | None = None
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TransferRequestCreateRequest(CommonSchema):
    current_club_id: str | None = Field(default=None, min_length=1, max_length=36)
    preferred_leagues: list[str] = Field(default_factory=list)
    preferred_clubs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TransferRequestView(CommonSchema):
    id: str
    player_id: str
    current_club_id: str | None = None
    requested_by_user_id: str | None = None
    status: str
    preferred_leagues: list[str] = Field(default_factory=list)
    preferred_clubs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    resolved_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


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
