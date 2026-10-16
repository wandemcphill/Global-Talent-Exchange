from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.trader import TraderExperience, TraderOrderSide, TraderOrderStatus, TraderP2PStatus


class TraderProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    trading_alias: str
    preferred_currency: str
    trading_experience: TraderExperience
    interests_json: list[str]
    wallet_label: str
    status: str
    created_at: datetime
    updated_at: datetime


class TraderMarketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    display_name: str
    asset_type: str
    price: Decimal
    daily_change_percent: Decimal
    market_cap: Decimal
    volume_24h: Decimal
    liquidity_score: int
    updated_at: datetime


class TraderOrderCreateRequest(BaseModel):
    market_id: str
    side: TraderOrderSide
    quantity: Decimal = Field(gt=Decimal("0"))
    limit_price: Decimal | None = Field(default=None, gt=Decimal("0"))


class TraderOrderView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    market_id: str
    side: TraderOrderSide
    status: TraderOrderStatus
    quantity: Decimal
    limit_price: Decimal | None
    created_at: datetime
    updated_at: datetime


class TraderP2POfferCreateRequest(BaseModel):
    market_id: str
    side: TraderOrderSide
    quantity: Decimal = Field(gt=Decimal("0"))
    unit_price: Decimal = Field(gt=Decimal("0"))
    preferred_currency: str = Field(min_length=2, max_length=12)


class TraderP2POfferView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    market_id: str
    side: TraderOrderSide
    status: TraderP2PStatus
    quantity: Decimal
    unit_price: Decimal
    preferred_currency: str
    created_at: datetime
    updated_at: datetime


class TraderWatchlistCreateRequest(BaseModel):
    market_id: str


class TraderWatchlistView(BaseModel):
    id: str
    market: TraderMarketView


class TraderOverviewView(BaseModel):
    profile: TraderProfileView
    portfolio_value: Decimal
    gtex_coin_price: Decimal
    daily_pl: Decimal
    wallet_balance: Decimal
    market_cap: Decimal
    trading_volume: Decimal
    trending: list[TraderMarketView]
    top_gainers: list[TraderMarketView]
    top_losers: list[TraderMarketView]
    most_traded_fan_coins: list[TraderMarketView]
    liquidity_activity: list[TraderMarketView]


class TotpSetupView(BaseModel):
    secret: str
    issuer: str = "GTEX"
    account_label: str


class TotpVerifyRequest(BaseModel):
    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(min_length=6, max_length=12)
    recovery_phrase_hash: str = Field(min_length=16, max_length=255)
    security_pin_hash: str = Field(min_length=16, max_length=255)


class TraderSecurityEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    metadata_json: dict[str, object]
    created_at: datetime


class TraderSecurityView(BaseModel):
    two_factor_enabled: bool
    backup_code_count: int
    recent_events: list[TraderSecurityEventView] = Field(default_factory=list)


class TotpVerifyView(TraderSecurityView):
    backup_codes: list[str] = Field(default_factory=list)
