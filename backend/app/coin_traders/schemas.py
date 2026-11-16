from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.models.coin_trader import (
    CoinAdvertPricingMode,
    CoinAdvertSide,
    CoinAdvertStatus,
    CoinTradeDirection,
    CoinTradeOrderStatus,
    CoinTraderProfileStatus,
    CoinTraderTier,
)
from app.models.wallet import LedgerUnit

CoinTraderStatusLiteral = Literal["applied", "approved", "rejected", "frozen", "suspended"]
CoinTradeDirectionLiteral = Literal["user_buys", "user_sells"]
CoinAdvertSideLiteral = Literal["sell", "buy"]
CoinAdvertStatusLiteral = Literal["draft", "active", "paused", "admin_paused", "closed"]
CoinAdvertPricingModeLiteral = Literal["fixed", "floating"]


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


class CoinTraderAdminLiquidityRequest(CommonSchema):
    coin_unit: LedgerUnit = LedgerUnit.COIN
    amount: Decimal = Field(gt=0)
    reference: str | None = Field(default=None, min_length=3, max_length=120)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)
    fiat_total: Decimal | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=1000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderAdminLiquidityTransferView(CommonSchema):
    trader_profile_id: str
    trader_user_id: str
    flow: Literal["issue", "redeem"]
    coin_unit: LedgerUnit
    amount: Decimal
    reference: str
    transaction_id: str | None = None
    ledger_entry_ids: list[str] = Field(default_factory=list)
    available_balance: Decimal
    liquidity_snapshot: dict[str, Any] = Field(default_factory=dict)


class CoinTraderProfileView(CommonSchema):
    id: str
    user_id: str
    display_name: str
    country_code: str | None = None
    status: CoinTraderProfileStatus | CoinTraderStatusLiteral | str
    tier: CoinTraderTier | str
    verification_level: str = "standard"
    verified_at: datetime | None = None
    verification_provider: str | None = None
    verification_reference: str | None = None
    suspended_at: datetime | None = None
    completion_rate: float
    average_release_minutes: float
    rating: float
    rating_count: int = 0
    completed_orders_count: int = 0
    total_orders_count: int = 0
    last_active_at: datetime | None = None
    is_didit_verified: bool = False
    verification_badge_label: str = "Approved by GTEX"
    is_new_merchant: bool = True
    completed_volume_fiat: Decimal = Decimal("0.0000")
    dispute_score: float = 0.0
    terms: dict[str, Any] = Field(default_factory=dict)
    payment_methods: list[dict[str, Any]] = Field(default_factory=list)
    bank_accounts: list[dict[str, Any]] = Field(default_factory=list)
    liquidity_snapshot: dict[str, Any] = Field(default_factory=dict)
    rates: list[CoinTraderRateView] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderPublicProfileView(CommonSchema):
    """Marketplace-safe projection of a trader profile.

    Intentionally omits bank accounts, KYC provider references, free-form metadata
    (admin notes), the self-declared liquidity snapshot and suspension details.
    Payment details are revealed only to order participants at the proper order stage.
    """

    id: str
    display_name: str
    country_code: str | None = None
    status: CoinTraderProfileStatus | CoinTraderStatusLiteral | str
    tier: CoinTraderTier | str
    verification_level: str = "standard"
    verified_at: datetime | None = None
    is_didit_verified: bool = False
    verification_badge_label: str = "Approved by GTEX"
    is_new_merchant: bool = True
    completion_rate: float
    average_release_minutes: float
    rating: float
    rating_count: int = 0
    completed_orders_count: int = 0
    total_orders_count: int = 0
    last_active_at: datetime | None = None
    completed_volume_fiat: Decimal = Decimal("0.0000")
    dispute_score: float = 0.0
    terms: dict[str, Any] = Field(default_factory=dict)
    payment_methods: list[str] = Field(default_factory=list)
    rates: list[CoinTraderRateView] = Field(default_factory=list)


class CoinTradeOrderCreateRequest(CommonSchema):
    trader_profile_id: str = Field(min_length=1, max_length=36)
    direction: CoinTradeDirection | CoinTradeDirectionLiteral
    coin_unit: LedgerUnit = LedgerUnit.COIN
    coin_amount: Decimal = Field(gt=0)
    fiat_currency: str = Field(default="NGN", min_length=3, max_length=8)
    payment_method: str | None = Field(default=None, max_length=80)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)
    advert_id: str | None = Field(default=None, min_length=1, max_length=36)
    # The price the customer saw. If the live price differs the order is rejected (stale-quote protection).
    expected_rate_fiat: Decimal | None = Field(default=None, gt=0)
    customer_payout_details: dict[str, Any] | None = None


class CoinTradeProofRequest(CommonSchema):
    proof_reference: str | None = Field(default=None, max_length=255)
    proof_url: str | None = Field(default=None, max_length=2048)
    note: str | None = Field(default=None, max_length=1000)


class CoinTradeMessageCreateRequest(CommonSchema):
    message: str = Field(min_length=1, max_length=1000)


class CoinTradeMessageView(CommonSchema):
    id: str
    order_id: str
    sender_user_id: str
    sender_name: str
    message: str
    created_at: datetime


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
    advert_id: str | None = None
    payment_window_minutes: int | None = None
    quote_expires_at: datetime | None = None
    fee_coin: Decimal = Decimal("0.0000")
    fee_fiat: Decimal = Decimal("0.0000")
    payment_window_expires_at: datetime | None = None
    accepted_at: datetime | None = None
    proof_submitted_at: datetime | None = None
    released_at: datetime | None = None
    cancelled_at: datetime | None = None
    disputed_at: datetime | None = None
    proof: dict[str, Any] = Field(default_factory=dict)
    terms_snapshot: dict[str, Any] = Field(default_factory=dict)
    ledger_refs: dict[str, Any] = Field(default_factory=dict)
    messages: list[CoinTradeMessageView] = Field(default_factory=list)
    counterparty_payment_details: list[dict[str, Any]] = Field(default_factory=list)
    customer_payout_details: dict[str, Any] | None = None
    trader_display_name: str | None = None
    customer_display_name: str | None = None
    my_rating: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CoinTraderAdminDecisionRequest(CommonSchema):
    tier: CoinTraderTier | str = CoinTraderTier.BRONZE
    note: str | None = Field(default=None, max_length=1000)


class CoinTraderAdminRejectRequest(CommonSchema):
    note: str | None = Field(default=None, max_length=1000)


class CoinTradeAdminResolutionRequest(CommonSchema):
    resolution: Literal["release", "refund"]
    note: str | None = Field(default=None, max_length=1000)


class CoinTraderLiquidityQuoteRequest(CommonSchema):
    amount: Decimal = Field(gt=0)
    provider: str = "korapay"
    coin_unit: LedgerUnit = LedgerUnit.COIN
    input_unit: str = "coin"


class CoinTraderLiquidityQuoteView(CommonSchema):
    gross_amount: Decimal
    fee_amount: Decimal
    processor_fee: Decimal
    net_amount: Decimal
    amount_fiat: Decimal
    total_fiat_charged: Decimal
    currency_code: str
    rate_value: Decimal
    unit: LedgerUnit
    provider_key: str


class CoinTraderLiquidityPurchaseRequest(CommonSchema):
    amount: Decimal = Field(gt=0)
    provider: str = "korapay"
    coin_unit: LedgerUnit = LedgerUnit.COIN
    callback_url: str | None = None


class CoinTraderLiquidityPurchaseSessionView(CommonSchema):
    order_reference: str
    checkout_url: str
    provider: str
    unit: LedgerUnit
    amount_coin: Decimal
    amount_fiat: Decimal
    status: str


class CoinTraderAdvertUpsertRequest(CommonSchema):
    coin_unit: LedgerUnit = LedgerUnit.COIN
    fiat_currency: str = Field(default="NGN", min_length=3, max_length=8)
    side: CoinAdvertSide | CoinAdvertSideLiteral
    pricing_mode: CoinAdvertPricingMode | CoinAdvertPricingModeLiteral = CoinAdvertPricingMode.FIXED
    price_fiat: Decimal = Field(gt=0)
    spread_fiat: Decimal = Field(default=Decimal("0.0000"))
    min_coin_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)
    max_coin_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)
    daily_limit_coin: Decimal | None = Field(default=None, gt=0)
    payment_window_minutes: int = Field(default=15, ge=5, le=120)
    payment_methods: list[str] = Field(default_factory=list)
    terms_text: str | None = Field(default=None, max_length=1000)
    status: CoinAdvertStatus | CoinAdvertStatusLiteral = CoinAdvertStatus.ACTIVE


class CoinTraderAdvertStatusUpdateRequest(CommonSchema):
    status: Literal["draft", "active", "paused", "closed"]


class CoinTraderAdvertView(CommonSchema):
    id: str
    trader_profile_id: str
    coin_unit: LedgerUnit
    fiat_currency: str
    side: str
    pricing_mode: str
    price_fiat: Decimal
    effective_price_fiat: Decimal
    spread_fiat: Decimal = Decimal("0.0000")
    reference_rate_fiat: Decimal | None = None
    price_deviation_pct: float | None = None
    min_coin_amount: Decimal
    max_coin_amount: Decimal
    min_fiat_amount: Decimal
    max_fiat_amount: Decimal
    available_coin: Decimal
    daily_limit_coin: Decimal | None = None
    daily_remaining_coin: Decimal | None = None
    payment_window_minutes: int
    payment_methods: list[str] = Field(default_factory=list)
    terms_text: str | None = None
    status: str
    admin_paused_reason: str | None = None
    governance_status: str = "compliant"
    governance_reasons: list[str] = Field(default_factory=list)
    updated_at: datetime


class CoinTraderMarketplaceOfferView(CommonSchema):
    advert_id: str
    trader_profile_id: str
    trader_display_name: str
    country_code: str | None = None
    trader_tier: str
    is_approved: bool
    is_didit_verified: bool
    verification_badge_label: str
    verified_at: datetime | None = None
    is_new_merchant: bool
    completed_orders_count: int
    total_orders_count: int
    completion_rate: float
    average_release_minutes: float
    rating: float
    rating_count: int
    dispute_score: float
    last_active_at: datetime | None = None
    coin_unit: LedgerUnit
    fiat_currency: str
    side: str
    pricing_mode: str
    price_fiat: Decimal
    reference_rate_fiat: Decimal | None = None
    price_deviation_pct: float | None = None
    savings_vs_direct_pct: float | None = None
    min_coin_amount: Decimal
    max_coin_amount: Decimal
    min_fiat_amount: Decimal
    max_fiat_amount: Decimal
    available_coin: Decimal
    daily_remaining_coin: Decimal | None = None
    payment_window_minutes: int
    payment_methods: list[str] = Field(default_factory=list)
    terms_text: str | None = None
    platform_fee_fiat: Decimal = Decimal("0.0000")
    updated_at: datetime


class CoinTraderMarketReferenceUnitView(CommonSchema):
    coin_unit: LedgerUnit
    name: str
    code: str
    direct_buy_rate_fiat: Decimal
    direct_sell_rate_fiat: Decimal | None = None
    trader_wholesale_rate_fiat: Decimal | None = None
    min_p2p_buy_fiat: Decimal
    min_trader_buy_rate_fiat: Decimal | None = None
    max_trader_buy_rate_fiat: Decimal | None = None
    min_trader_sell_rate_fiat: Decimal | None = None
    max_trader_sell_rate_fiat: Decimal | None = None
    max_trader_spread_fiat: Decimal | None = None
    platform_fee_fiat: Decimal = Decimal("0.0000")


class CoinTraderMarketReferenceView(CommonSchema):
    fiat_currency: str = "NGN"
    updated_at: datetime
    assets: list[CoinTraderMarketReferenceUnitView] = Field(default_factory=list)


class CoinTraderMarketplaceResponse(CommonSchema):
    coin_unit: LedgerUnit
    side: str
    fiat_currency: str = "NGN"
    total: int
    offers: list[CoinTraderMarketplaceOfferView] = Field(default_factory=list)
    market_reference: CoinTraderMarketReferenceUnitView


class CoinTradeOrderQuoteRequest(CommonSchema):
    advert_id: str = Field(min_length=1, max_length=36)
    coin_amount: Decimal | None = Field(default=None, gt=0)
    fiat_amount: Decimal | None = Field(default=None, gt=0)


class CoinTradeOrderQuoteView(CommonSchema):
    advert_id: str
    trader_profile_id: str
    trader_display_name: str
    direction: str
    coin_unit: LedgerUnit
    fiat_currency: str
    quoted_rate_fiat: Decimal
    coin_amount: Decimal
    fiat_total: Decimal
    fee_coin: Decimal = Decimal("0.0000")
    fee_fiat: Decimal = Decimal("0.0000")
    net_receive_label: str
    min_coin_amount: Decimal
    max_coin_amount: Decimal
    min_fiat_amount: Decimal
    max_fiat_amount: Decimal
    available_coin: Decimal
    payment_window_minutes: int
    quote_expires_at: datetime
    reference_rate_fiat: Decimal | None = None
    price_deviation_pct: float | None = None
    price_warning: str | None = None
    escrow_protection_note: str
    payment_methods: list[str] = Field(default_factory=list)
    terms_text: str | None = None


class CoinTradeRatingCreateRequest(CommonSchema):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class CoinTradeRatingView(CommonSchema):
    id: str
    order_id: str
    trader_profile_id: str
    user_id: str
    score: int
    comment: str | None = None
    created_at: datetime


class CoinTraderWalletBalancesView(CommonSchema):
    coin_available: Decimal
    coin_reserved: Decimal
    credit_available: Decimal
    credit_reserved: Decimal


class CoinTraderDashboardOrderCountsView(CommonSchema):
    new_orders: int = 0
    awaiting_payment: int = 0
    payment_submitted: int = 0
    completed: int = 0
    cancelled: int = 0
    expired: int = 0
    disputed: int = 0


class CoinTraderDashboardPerformanceView(CommonSchema):
    total_volume_fiat: Decimal
    completed_orders: int
    total_orders: int
    completion_rate: float
    average_release_minutes: float
    rating: float
    rating_count: int
    dispute_score: float
    realised_profit_fiat: Decimal | None = None
    realised_profit_note: str


class CoinTraderDashboardView(CommonSchema):
    profile: CoinTraderProfileView
    balances: CoinTraderWalletBalancesView
    order_counts: CoinTraderDashboardOrderCountsView
    performance: CoinTraderDashboardPerformanceView
    adverts: list[CoinTraderAdvertView] = Field(default_factory=list)


class CoinTraderAdminAdvertPauseRequest(CommonSchema):
    reason: str = Field(min_length=3, max_length=500)


class CoinTraderAdminConfigUpdateRequest(CommonSchema):
    deposit_rate_value: Decimal | None = Field(default=None, gt=0)
    withdrawal_rate_value: Decimal | None = Field(default=None, gt=0)
    fan_coin_deposit_rate_value: Decimal | None = Field(default=None, gt=0)
    trader_fan_coin_purchase_rate_value: Decimal | None = Field(default=None, gt=0)
    min_trader_buy_rate_fiat: Decimal | None = Field(default=None, gt=0)
    max_trader_buy_rate_fiat: Decimal | None = Field(default=None, gt=0)
    min_trader_sell_rate_fiat: Decimal | None = Field(default=None, gt=0)
    max_trader_sell_rate_fiat: Decimal | None = Field(default=None, gt=0)
    max_trader_spread_fiat: Decimal | None = Field(default=None, ge=0)
    max_buy_above_withdrawal_fiat: Decimal | None = Field(default=None, ge=0)
    max_sell_below_deposit_fiat: Decimal | None = Field(default=None, ge=0)


class CoinTraderAdminAuditLogView(CommonSchema):
    id: str
    actor_user_id: str | None = None
    action_key: str
    resource_type: str
    resource_id: str | None = None
    outcome: str
    detail: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CoinTraderAdminOverviewView(CommonSchema):
    total_traders: int
    approved_traders: int
    didit_verified_traders: int
    suspended_or_frozen_traders: int
    active_adverts: int
    total_orders: int
    active_escrow_orders: int
    disputed_orders: int
    completed_volume_fiat: Decimal
    total_escrowed_coin: Decimal
    total_escrowed_credit: Decimal
    recent_governance_blocks: int
