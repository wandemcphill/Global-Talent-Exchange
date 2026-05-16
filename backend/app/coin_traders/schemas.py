from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.models.coin_trader import CoinTradeDirection, CoinTradeOrderStatus, CoinTraderProfileStatus, CoinTraderTier
from app.models.wallet import LedgerUnit

CoinTraderStatusLiteral = Literal["applied", "approved", "rejected", "frozen", "suspended"]
CoinTradeDirectionLiteral = Literal["user_buys", "user_sells"]


class CoinTraderProfileCreateRequest(CommonSchema):
    display_name: str = Field(min_length=2, max_length=120)
    country_code: str | None = Field(default=None, max_length=8)
    terms: dict[str, Any] = Field(default_factory=dict)
    payment_methods: list[dict[str, Any]] = Field(default_factory=list)
    bank_accounts: list[dict[str, Any]] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderProfileUpdateRequest(CommonSchema):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    country_code: str | None = Field(default=None, max_length=8)
    terms: dict[str, Any] | None = None
    payment_methods: list[dict[str, Any]] | None = None
    bank_accounts: list[dict[str, Any]] | None = None
    metadata_json: dict[str, Any] | None = None


class CoinTraderRateUpsertRequest(CommonSchema):
    coin_unit: LedgerUnit = LedgerUnit.COIN
    fiat_currency: str = Field(default="NGN", min_length=3, max_length=8)
    buy_rate_fiat: Decimal = Field(ge=0)
    sell_rate_fiat: Decimal = Field(ge=0)
    min_coin_amount: Decimal = Field(default=Decimal("0"), ge=0)
    max_coin_amount: Decimal = Field(default=Decimal("0"), ge=0)
    available_liquidity: Decimal = Field(default=Decimal("0"), ge=0)
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderRateView(CommonSchema):
    id: str
    trader_profile_id: str
    coin_unit: LedgerUnit
    fiat_currency: str
    buy_rate_fiat: Decimal
    sell_rate_fiat: Decimal
    min_coin_amount: Decimal
    max_coin_amount: Decimal
    available_liquidity: Decimal
    is_active: bool
    spread_fiat: Decimal = Decimal("0.0000")
    treasury_deposit_rate_fiat: Decimal | None = None
    treasury_withdrawal_rate_fiat: Decimal | None = None
    min_trader_buy_rate_fiat: Decimal | None = None
    max_trader_buy_rate_fiat: Decimal | None = None
    min_trader_sell_rate_fiat: Decimal | None = None
    max_trader_sell_rate_fiat: Decimal | None = None
    max_trader_spread_fiat: Decimal | None = None
    governance_status: str = "compliant"
    governance_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderProfileView(CommonSchema):
    id: str
    user_id: str
    display_name: str
    country_code: str | None = None
    status: CoinTraderProfileStatus | CoinTraderStatusLiteral | str
    tier: CoinTraderTier | str
    verification_level: str = "standard"
    completion_rate: float
    average_release_minutes: float
    rating: float
    completed_volume_fiat: Decimal = Decimal("0.0000")
    dispute_score: float = 0.0
    terms: dict[str, Any] = Field(default_factory=dict)
    payment_methods: list[dict[str, Any]] = Field(default_factory=list)
    bank_accounts: list[dict[str, Any]] = Field(default_factory=list)
    liquidity_snapshot: dict[str, Any] = Field(default_factory=dict)
    rates: list[CoinTraderRateView] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTradeOrderCreateRequest(CommonSchema):
    trader_profile_id: str = Field(min_length=1, max_length=36)
    direction: CoinTradeDirection | CoinTradeDirectionLiteral
    coin_unit: LedgerUnit = LedgerUnit.COIN
    coin_amount: Decimal = Field(gt=0)
    fiat_currency: str = Field(default="NGN", min_length=3, max_length=8)
    payment_method: str | None = Field(default=None, max_length=80)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class CoinTradeProofRequest(CommonSchema):
    proof_reference: str | None = Field(default=None, max_length=255)
    proof_url: str | None = Field(default=None, max_length=2048)
    note: str | None = Field(default=None, max_length=1000)


class CoinTradeDisputeRequest(CommonSchema):
    reason: str = Field(min_length=3, max_length=500)
    evidence: dict[str, Any] = Field(default_factory=dict)


class CoinTradeOrderView(CommonSchema):
    id: str
    trader_profile_id: str
    user_id: str
    direction: CoinTradeDirection | CoinTradeDirectionLiteral | str
    coin_unit: LedgerUnit
    coin_amount: Decimal
    quoted_rate_fiat: Decimal
    fiat_total: Decimal
    fiat_currency: str
    status: CoinTradeOrderStatus | str
    escrow_owner_user_id: str | None = None
    idempotency_key: str | None = None
    payment_method: str | None = None
    payment_window_expires_at: datetime | None = None
    accepted_at: datetime | None = None
    proof_submitted_at: datetime | None = None
    released_at: datetime | None = None
    cancelled_at: datetime | None = None
    disputed_at: datetime | None = None
    proof: dict[str, Any] = Field(default_factory=dict)
    terms_snapshot: dict[str, Any] = Field(default_factory=dict)
    ledger_refs: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderAdminDecisionRequest(CommonSchema):
    tier: CoinTraderTier | str = CoinTraderTier.BRONZE
    note: str | None = Field(default=None, max_length=1000)


class CoinTraderAdminRejectRequest(CommonSchema):
    note: str | None = Field(default=None, max_length=1000)


class CoinTradeAdminResolutionRequest(CommonSchema):
    resolution: Literal["release", "refund"]
    note: str | None = Field(default=None, max_length=1000)
