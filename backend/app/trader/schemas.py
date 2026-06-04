from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.market_topup import MarketTopupStatus
from app.models.trader import TraderExperience, TraderOrderSide, TraderOrderStatus, TraderP2PStatus
from app.models.wallet import LedgerUnit


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
    liquidity_snapshot_json: dict
    completion_rate: Decimal
    average_release_seconds: Decimal
    rating_score: Decimal
    metrics_updated_at: datetime | None
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
    audit_ref: str | None = None


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
    audit_ref: str | None = None


class TraderWatchlistCreateRequest(BaseModel):
    market_id: str


class TraderWatchlistView(BaseModel):
    id: str
    market: TraderMarketView


class TraderProcurementQuoteRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    fee_bps: int = Field(default=0, ge=0, le=10_000)
    unit: LedgerUnit = LedgerUnit.COIN


class TraderProcurementQuoteView(BaseModel):
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    unit: LedgerUnit
    source_scope: str = "liquidity"


class TraderProcurementCreateRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    fee_bps: int = Field(default=0, ge=0, le=10_000)
    unit: LedgerUnit = LedgerUnit.COIN
    notes: str | None = Field(default=None, max_length=255)


class TraderProcurementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    reference: str
    status: MarketTopupStatus
    unit: LedgerUnit
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    source_scope: str
    metadata_json: dict
    created_at: datetime
    updated_at: datetime
    audit_ref: str | None = None


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


class TraderBalanceView(BaseModel):
    available: Decimal
    reserved: Decimal
    total: Decimal
    currency: LedgerUnit = LedgerUnit.COIN
    last_synced_at: datetime | None = None


class TraderActivityView(BaseModel):
    id: str
    label: str
    status: str | None = None
    audit_ref: str | None = None
    created_at: datetime | None = None


class TraderDashboardView(BaseModel):
    balance: TraderBalanceView
    active_orders: int
    pending_settlements: int
    open_disputes: int
    recent_activity: list[TraderActivityView] = Field(default_factory=list)


class TraderOrderBookLevelView(BaseModel):
    price: Decimal
    quantity: Decimal


class TraderOrderBookView(BaseModel):
    market_id: str
    bids: list[TraderOrderBookLevelView] = Field(default_factory=list)
    asks: list[TraderOrderBookLevelView] = Field(default_factory=list)
    synced_at: datetime
    status: str


class TraderQuoteRequest(BaseModel):
    market_id: str
    side: TraderOrderSide
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="coin", min_length=2, max_length=12)


class TraderQuoteView(BaseModel):
    id: str
    price: Decimal
    amount: Decimal
    currency: str
    valid_until: datetime
    locked_until: datetime
    lock_seconds_remaining: int
    audit_ref: str


class TraderDisputeCreateRequest(BaseModel):
    order_id: str
    reason: str = Field(min_length=3, max_length=500)


class TraderDisputeEventView(BaseModel):
    id: str
    event: str
    actor_id: str | None = None
    audit_ref: str | None = None
    created_at: datetime | None = None


class TraderDisputeView(BaseModel):
    id: str
    order_id: str
    reason: str
    status: str
    filed_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution: str | None = None
    audit_trail: list[TraderDisputeEventView] = Field(default_factory=list)
    audit_ref: str | None = None


class TraderSettlementView(BaseModel):
    id: str
    order_id: str
    amount: Decimal
    currency: str
    status: str
    method: str | None = None
    initiated_at: datetime | None = None
    confirmed_at: datetime | None = None
    eta: str | None = None
    receipt_ref: str | None = None
    proof_url: str | None = None
    audit_ref: str | None = None


class TraderDepositRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="coin", min_length=2, max_length=12)
    method: str = Field(pattern="^(korapay|manual)$")
    proof_attachment_id: str | None = None


class TraderDepositResultView(BaseModel):
    id: str
    status: str
    checkout_url: str | None = None
    audit_ref: str | None = None


class TraderWithdrawalRequest(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="coin", min_length=2, max_length=12)
    method: str = Field(pattern="^(korapay|manual)$")
    destination_ref: str = Field(min_length=3, max_length=120)


class TraderWithdrawalResultView(BaseModel):
    id: str
    status: str
    audit_ref: str | None = None


class TotpSetupView(BaseModel):
    secret: str
    issuer: str = "GTEX"
    account_label: str


class TotpVerifyRequest(BaseModel):
    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(min_length=6, max_length=12)


class TraderSecurityView(BaseModel):
    two_factor_enabled: bool
    backup_codes: list[str] = Field(default_factory=list)
