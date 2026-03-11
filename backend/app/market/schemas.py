from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.market.models import (
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
