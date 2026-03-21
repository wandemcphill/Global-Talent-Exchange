from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.market.models import (
    ListingStatus,
    ListingType,
    OfferStatus,
    TradeIntentDirection,
    TradeIntentStatus,
)


class ListingCreate(BaseModel):
    asset_id: str = Field(min_length=1)
    listing_type: ListingType
    ask_price: int | None = Field(default=None, gt=0)
    desired_asset_ids: tuple[str, ...] = ()
    note: str | None = None


class ListingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    listing_id: str
    asset_id: str
    seller_user_id: str
    listing_type: ListingType
    ask_price: int | None
    desired_asset_ids: tuple[str, ...]
    note: str | None
    status: ListingStatus
    created_at: datetime
    updated_at: datetime


class OfferCreate(BaseModel):
    asset_id: str = Field(min_length=1)
    seller_user_id: str = Field(min_length=1)
    cash_amount: int = Field(default=0, ge=0)
    offered_asset_ids: tuple[str, ...] = ()
    listing_id: str | None = None
    note: str | None = None


class OfferCounterCreate(BaseModel):
    cash_amount: int = Field(default=0, ge=0)
    offered_asset_ids: tuple[str, ...] = ()
    note: str | None = None


class OfferView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    offer_id: str
    asset_id: str
    listing_id: str | None
    seller_user_id: str
    buyer_user_id: str
    proposer_user_id: str
    recipient_user_id: str
    cash_amount: int
    offered_asset_ids: tuple[str, ...]
    note: str | None
    status: OfferStatus
    parent_offer_id: str | None
    created_at: datetime
    updated_at: datetime


class TradeIntentCreate(BaseModel):
    asset_id: str = Field(min_length=1)
    direction: TradeIntentDirection
    price_floor: int | None = Field(default=None, gt=0)
    price_ceiling: int | None = Field(default=None, gt=0)
    offered_asset_ids: tuple[str, ...] = ()
    note: str | None = None


class TradeIntentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    intent_id: str
    user_id: str
    asset_id: str
    direction: TradeIntentDirection
    price_floor: int | None
    price_ceiling: int | None
    offered_asset_ids: tuple[str, ...]
    note: str | None
    status: TradeIntentStatus
    created_at: datetime
    updated_at: datetime


class MarketSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    open_listing_id: str | None
    open_listing_type: str | None
    seller_user_id: str | None
    ask_price: int | None
    pending_offer_count: int
    best_offer_price: int | None
    active_trade_intent_count: int
    last_activity_at: datetime
    updated_at: datetime


class MarketPlayerListItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    position: str | None
    nationality: str | None
    current_club_name: str | None
    age: int | None
    current_value_credits: float | None
    movement_pct: float | None
    trend_score: float | None
    market_interest_score: int | None
    average_rating: float | None


class MarketPlayerListView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[MarketPlayerListItemView]
    limit: int
    offset: int
    total: int


class MarketPlayerIdentityView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_name: str
    first_name: str | None
    last_name: str | None
    short_name: str | None
    position: str | None
    normalized_position: str | None
    nationality: str | None
    nationality_code: str | None
    age: int | None
    date_of_birth: date | None
    preferred_foot: str | None
    shirt_number: int | None
    height_cm: int | None
    weight_kg: int | None
    current_club_id: str | None
    current_club_name: str | None
    current_competition_id: str | None
    current_competition_name: str | None
    image_url: str | None


class MarketPlayerMarketProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_tradable: bool
    market_value_eur: float | None
    supply_tier: dict[str, Any] | None
    liquidity_band: dict[str, Any] | None
    holder_count: int | None
    top_holder_share_pct: float | None
    top_3_holder_share_pct: float | None
    snapshot_market_price_credits: float | None
    quoted_market_price_credits: float | None
    trusted_trade_price_credits: float | None
    trade_trust_score: float | None


class MarketPlayerValueProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    last_snapshot_id: str | None
    last_snapshot_at: datetime | None
    current_value_credits: float | None
    previous_value_credits: float | None
    movement_pct: float | None
    football_truth_value_credits: float | None
    market_signal_value_credits: float | None
    published_card_value_credits: float | None


class MarketPlayerTrendProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trend_score: float | None
    market_interest_score: int | None
    average_rating: float | None
    global_scouting_index: float | None
    previous_global_scouting_index: float | None
    global_scouting_index_movement_pct: float | None
    drivers: tuple[str, ...]
    active_real_world_flags: tuple[str, ...] = ()
    recommendation_priority_delta: float = 0.0
    market_buzz_score: float = 0.0
    temporary_form_boost: float = 0.0


class MarketPlayerDetailView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    identity: MarketPlayerIdentityView
    market_profile: MarketPlayerMarketProfileView
    value: MarketPlayerValueProfileView
    trend: MarketPlayerTrendProfileView


class MarketPlayerHistoryPointView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    as_of: datetime
    current_value_credits: float
    previous_value_credits: float
    movement_pct: float
    football_truth_value_credits: float
    market_signal_value_credits: float
    published_card_value_credits: float | None
    trend_score: float | None
    global_scouting_index: float | None
    previous_global_scouting_index: float | None
    global_scouting_index_movement_pct: float | None
    drivers: tuple[str, ...]


class MarketPlayerHistoryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    history: list[MarketPlayerHistoryPointView]
