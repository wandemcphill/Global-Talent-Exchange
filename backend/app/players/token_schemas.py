from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PlayerShareMarketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    total_shares: int
    circulating_shares: int
    share_price_coin: Decimal
    liquidity_coin: Decimal = Decimal("0.0000")
    status: str
    market_issued: bool = True
    revenue_distributed_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class PlayerShareMarketIssueRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_shares: int = Field(default=1000, ge=1)
    share_price_coin: Decimal = Field(
        gt=0,
        validation_alias=AliasChoices("share_price_coin", "price"),
    )
    liquidity_coin: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("liquidity_coin", "liquidity"),
    )
    status: str = Field(default="active", min_length=2, max_length=24)


class PlayerSharePurchaseRequest(BaseModel):
    share_count: int = Field(ge=1)


class PlayerShareHoldingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    player_id: str
    share_count: int
    average_cost_coin: Decimal
    dividends_earned_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class PlayerSharePurchaseView(BaseModel):
    market: PlayerShareMarketView
    holding: PlayerShareHoldingView
    transaction_id: str
    gross_amount_coin: Decimal


class PlayerShareSaleRequest(BaseModel):
    share_count: int = Field(ge=1)


class PlayerShareSaleView(BaseModel):
    market: PlayerShareMarketView
    holding: PlayerShareHoldingView
    transaction_id: str
    gross_amount_coin: Decimal


class PlayerShareTradeRequest(BaseModel):
    player_id: str = Field(min_length=1)
    share_count: int = Field(ge=1)


class PlayerSharePerformanceRequest(BaseModel):
    multiplier: Decimal = Field(gt=0)
    reason: str | None = Field(default=None, max_length=255)


class PlayerShareDividendRequest(BaseModel):
    gross_amount_coin: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class PlayerShareDividendView(BaseModel):
    market: PlayerShareMarketView
    transaction_id: str
    gross_amount_coin: Decimal


class PlayerShareEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    user_id: str | None = None
    actor_user_id: str | None = None
    event_type: str
    share_delta: int
    price_per_share_coin: Decimal
    gross_amount_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime


class PlayerShareMarketListItemView(BaseModel):
    player_id: str
    player_name: str
    position: str | None = None
    nationality: str | None = None
    current_club_name: str | None = None
    age: int | None = None
    share_price_coin: Decimal
    liquidity_coin: Decimal
    total_shares: int
    circulating_shares: int
    status: str
    market_issued: bool = True
    metadata_json: dict[str, object] = {}
    created_at: datetime
    updated_at: datetime


class PlayerShareMarketListView(BaseModel):
    items: list[PlayerShareMarketListItemView]
    limit: int
    offset: int
    total: int
