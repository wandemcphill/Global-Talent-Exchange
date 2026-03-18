from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from backend.app.football_events_engine.schemas import (
    PlayerDemandSignalView,
    PlayerFormModifierView,
    TrendingPlayerFlagView,
)


class PlayerCardTierView(BaseModel):
    tier_id: str
    code: str
    name: str
    rarity_rank: int
    max_supply: int | None
    supply_multiplier: float
    base_mint_price_credits: float
    color_hex: str | None
    is_active: bool


class PlayerCardView(BaseModel):
    card_id: str
    player_id: str
    tier: PlayerCardTierView | None
    edition_code: str
    display_name: str
    season_label: str | None
    card_variant: str
    supply_total: int
    supply_available: int
    is_active: bool


class PlayerCardEffectView(BaseModel):
    effect_id: str
    player_card_id: str
    effect_type: str
    effect_value: float
    applied_at: datetime | None
    expires_at: datetime | None
    source: str | None
    metadata_json: dict[str, Any]


class PlayerCardFormBuffView(BaseModel):
    buff_id: str
    player_card_id: str
    buff_type: str
    buff_value: float
    started_at: datetime | None
    expires_at: datetime | None
    source: str | None
    metadata_json: dict[str, Any]


class PlayerCardMomentumView(BaseModel):
    momentum_id: str
    player_id: str
    last_trade_price_credits: float | None
    momentum_7d_pct: float
    momentum_30d_pct: float
    trend_direction: str
    metadata_json: dict[str, Any]


class PlayerStatsSnapshotView(BaseModel):
    snapshot_id: str
    player_id: str
    as_of: datetime
    competition_id: str | None
    season_id: str | None
    source_type: str
    stats_json: dict[str, Any]


class PlayerMarketValueSnapshotView(BaseModel):
    snapshot_id: str
    player_id: str
    as_of: datetime
    last_trade_price_credits: float | None
    avg_trade_price_credits: float | None
    volume_24h: int
    listing_floor_price_credits: float | None
    listing_count: int
    high_24h_price_credits: float | None
    low_24h_price_credits: float | None
    metadata_json: dict[str, Any]


class PlayerCardPlayerSummaryView(BaseModel):
    player_id: str
    player_name: str
    position: str | None
    nationality_code: str | None
    current_club_name: str | None
    card_supply_total: int
    latest_value_credits: float | None


class PlayerCardPlayerDetailView(BaseModel):
    player_id: str
    player_name: str
    position: str | None
    nationality_code: str | None
    current_club_name: str | None
    aliases: list[str]
    monikers: list[str]
    cards: list[PlayerCardView]
    effects: list[PlayerCardEffectView]
    form_buffs: list[PlayerCardFormBuffView]
    momentum: PlayerCardMomentumView | None
    latest_stats_snapshot: PlayerStatsSnapshotView | None
    latest_market_snapshot: PlayerMarketValueSnapshotView | None
    real_world_flags: list[TrendingPlayerFlagView] = Field(default_factory=list)
    real_world_form_modifiers: list[PlayerFormModifierView] = Field(default_factory=list)
    demand_signals: list[PlayerDemandSignalView] = Field(default_factory=list)
    recommendation_priority_delta: float = 0.0
    market_buzz_score: float = 0.0


class PlayerCardHoldingView(BaseModel):
    holding_id: str
    player_card_id: str
    player_id: str
    player_name: str
    tier_code: str
    tier_name: str
    edition_code: str
    quantity_total: int
    quantity_reserved: int
    quantity_available: int
    last_acquired_at: datetime | None


class PlayerCardListingView(BaseModel):
    listing_id: str
    player_card_id: str
    player_id: str
    player_name: str
    tier_code: str
    tier_name: str
    edition_code: str
    seller_user_id: str
    quantity: int
    price_per_card_credits: float
    status: str
    created_at: datetime


class PlayerCardLoanListingView(BaseModel):
    loan_listing_id: str
    player_card_id: str
    player_id: str
    player_name: str
    position: str | None
    tier_code: str
    tier_name: str
    edition_code: str
    owner_user_id: str
    total_slots: int
    available_slots: int
    duration_days: int
    loan_fee_credits: float
    currency: str
    status: str
    usage_restrictions_json: dict[str, Any]
    terms_json: dict[str, Any]
    expires_at: datetime | None
    created_at: datetime


class PlayerCardLoanContractView(PlayerCardLoanListingView):
    loan_contract_id: str
    borrower_user_id: str
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    contract_status: str
    usage_snapshot_json: dict[str, Any]


class PlayerCardSaleView(BaseModel):
    sale_id: str
    listing_id: str | None
    player_card_id: str
    seller_user_id: str
    buyer_user_id: str
    quantity: int
    price_per_card_credits: Decimal
    gross_credits: Decimal
    fee_credits: Decimal
    seller_net_credits: Decimal
    status: str
    settlement_reference: str
    created_at: datetime


class PlayerCardWatchlistView(BaseModel):
    id: str
    player_id: str
    player_card_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class StarterSquadRentalPlayerView(BaseModel):
    rental_player_id: str
    player_name: str
    primary_position: str
    secondary_positions: list[str]
    current_gsi: int
    locked_gsi: int
    potential_maximum: int
    status: str
    starter_badge: str
    non_tradable: bool
    ownership_type: str
    squad_scope: str


class StarterSquadRentalView(BaseModel):
    starter_rental_id: str
    user_id: str
    club_id: str | None
    status: str
    rental_fee_credits: float
    currency: str
    term_days: int
    starts_at: datetime
    ends_at: datetime
    first_team_count: int
    academy_count: int
    is_non_tradable: bool
    roster: list[StarterSquadRentalPlayerView]
    academy_roster: list[StarterSquadRentalPlayerView]
    metadata_json: dict[str, Any]
    created_at: datetime


class PlayerCardListingCreateRequest(BaseModel):
    player_card_id: str = Field(min_length=2)
    quantity: int = Field(default=1, ge=1)
    price_per_card_credits: Decimal = Field(gt=0)


class PlayerCardListingBuyRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1)


class PlayerCardLoanListingCreateRequest(BaseModel):
    player_card_id: str = Field(min_length=2)
    total_slots: int = Field(default=1, ge=1, le=25)
    duration_days: int = Field(default=7, ge=1, le=30)
    loan_fee_credits: Decimal = Field(gt=0)
    usage_restrictions_json: dict[str, Any] = Field(default_factory=dict)
    terms_json: dict[str, Any] = Field(default_factory=dict)


class PlayerCardLoanBorrowRequest(BaseModel):
    competition_id: str | None = None
    squad_scope: str | None = None


class PlayerCardWatchlistCreateRequest(BaseModel):
    player_id: str = Field(min_length=2)
    player_card_id: str | None = None
    notes: str | None = None


class StarterSquadRentalCreateRequest(BaseModel):
    club_id: str | None = None
    include_academy: bool = True
    first_team_count: int = Field(default=18, ge=1, le=30)
    academy_count: int = Field(default=18, ge=0, le=30)
    term_days: int = Field(default=7, ge=1, le=30)
    rental_fee_credits: Decimal = Field(default=Decimal("5.0000"), ge=0)
