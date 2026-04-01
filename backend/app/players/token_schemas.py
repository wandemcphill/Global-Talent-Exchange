from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlayerShareMarketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    total_shares: int
    circulating_shares: int
    share_price_coin: Decimal
    status: str
    market_issued: bool = True
    revenue_distributed_coin: Decimal
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class PlayerShareMarketIssueRequest(BaseModel):
    total_shares: int = Field(default=1000, ge=1)
    share_price_coin: Decimal = Field(gt=0)
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
