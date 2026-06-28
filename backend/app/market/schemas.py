from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.market.models import (
    ListingStatus,
    ListingType,
    OfferStatus,
    TradeIntentDirection,
    TradeIntentStatus,
)
from app.schemas.avatar import PlayerAvatarView


class ListingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    listing_type: ListingType
    ask_price: int | None = Field(default=None, gt=0)
    desired_asset_ids: tuple[str, ...] = ()
    note: str | None = None

    @field_validator("asset_id", "note")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("desired_asset_ids", mode="before")
    @classmethod
    def normalize_asset_ids(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            candidate = value.strip()
            return (candidate,) if candidate else ()
        return tuple(str(item).strip() for item in value if str(item).strip())


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
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    seller_user_id: str = Field(min_length=1)
    cash_amount: int = Field(default=0, ge=0)
    offered_asset_ids: tuple[str, ...] = ()
    listing_id: str | None = None
    note: str | None = None

    @field_validator("asset_id", "seller_user_id", "listing_id", "note")
    @classmethod
    def normalize_offer_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("offered_asset_ids", mode="before")
    @classmethod
    def normalize_offered_asset_ids(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            candidate = value.strip()
            return (candidate,) if candidate else ()
        return tuple(str(item).strip() for item in value if str(item).strip())


class OfferCounterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cash_amount: int = Field(default=0, ge=0)
    offered_asset_ids: tuple[str, ...] = ()
    note: str | None = None

    @field_validator("note")
    @classmethod
    def normalize_counter_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("offered_asset_ids", mode="before")
    @classmethod
    def normalize_counter_asset_ids(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            candidate = value.strip()
            return (candidate,) if candidate else ()
        return tuple(str(item).strip() for item in value if str(item).strip())


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
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)
    direction: TradeIntentDirection
    price_floor: int | None = Field(default=None, gt=0)
    price_ceiling: int | None = Field(default=None, gt=0)
    offered_asset_ids: tuple[str, ...] = ()
    note: str | None = None

    @field_validator("asset_id", "note")
    @classmethod
    def normalize_trade_intent_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @field_validator("offered_asset_ids", mode="before")
    @classmethod
    def normalize_trade_intent_asset_ids(cls, value: object) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            candidate = value.strip()
            return (candidate,) if candidate else ()
        return tuple(str(item).strip() for item in value if str(item).strip())


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
    secondary_positions: list[str] = Field(default_factory=list)
    nationality: str | None
    nationality_code: str | None
    current_club_id: str | None
    current_club_name: str | None
    current_competition_id: str | None
    current_competition_name: str | None
    current_competition_country_name: str | None = None
    current_division_id: str | None
    current_division_name: str | None
    age: int | None
    height_cm: int | None = None
    preferred_foot: str | None = None
    market_value_eur: float | None = None
    current_value_credits: float | None
    movement_pct: float | None
    trend_score: float | None
    market_interest_score: int | None
    average_rating: float | None
    global_scouting_index: float | None = None
    previous_global_scouting_index: float | None = None
    global_scouting_index_movement_pct: float | None = None
    transfer_listing_id: str | None = None
    transfer_listing_status: str | None = None
    selling_club_id: str | None = None
    availability_label: str = "Available now"
    asking_type: str = "transfer"
    salary_amount: float | None = None
    contract_years_remaining: float | None = None
    buy_clause_amount: float | None = None
    loan_terms: dict[str, Any] = Field(default_factory=dict)
    swap_terms: dict[str, Any] = Field(default_factory=dict)
    availability: dict[str, Any] = Field(default_factory=dict)
    is_tradable: bool
    image_url: str | None
    avatar: PlayerAvatarView


class MarketPlayerListView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[MarketPlayerListItemView]
    limit: int
    offset: int
    has_more: bool
    next_cursor: str | None
    total: int


class MarketBrowseOptionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    count: int
    subtitle: str | None = None
    parent_id: str | None = None
    country_id: str | None = None
    league_id: str | None = None
    division_id: str | None = None


class MarketBrowseCatalogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    countries: list[MarketBrowseOptionView]
    leagues: list[MarketBrowseOptionView]
    divisions: list[MarketBrowseOptionView]
    clubs: list[MarketBrowseOptionView]


class MarketPlayerIdentityView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_name: str
    first_name: str | None
    last_name: str | None
    short_name: str | None
    position: str | None
    normalized_position: str | None
    secondary_positions: list[str] = Field(default_factory=list)
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
    avatar: PlayerAvatarView


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


class MarketPlayerAttributesView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall: int
    potential: int
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int


class MarketPlayerDetailView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    identity: MarketPlayerIdentityView
    market_profile: MarketPlayerMarketProfileView
    value: MarketPlayerValueProfileView
    trend: MarketPlayerTrendProfileView
    attributes: MarketPlayerAttributesView


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
