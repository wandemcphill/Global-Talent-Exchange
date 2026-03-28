from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AdminFinanceDailyStatView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    gtex_minted: Decimal
    gtex_burned: Decimal
    fan_minted: Decimal
    fan_burned: Decimal
    revenue_naira: Decimal
    marketplace_fee_amount: Decimal
    match_spend_amount: Decimal
    tournament_pool_amount: Decimal
    gtex_supply: Decimal
    fan_supply: Decimal
    metadata_json: dict[str, object] = Field(default_factory=dict)


class AdminFinanceLargeTransactionView(BaseModel):
    transaction_id: str
    reference: str | None = None
    account_code: str
    unit: str
    amount: Decimal
    reason: str
    source_tag: str
    created_at: datetime


class AdminFinanceAlertView(BaseModel):
    level: str
    title: str
    message: str
    metric_key: str
    created_at: datetime | None = None


class AdminFinancePlayerTrendView(BaseModel):
    player_id: str
    trend_direction: str
    momentum_7d_pct: Decimal
    momentum_30d_pct: Decimal
    last_trade_price_credits: Decimal | None = None


class AdminFinanceTournamentPoolView(BaseModel):
    competition_id: str
    pool_type: str
    currency: str
    amount: Decimal
    status: str


class AdminFinanceCashRailView(BaseModel):
    payment_methods: list[str]
    deposit_mode: str
    withdrawal_mode: str
    currency_code: str
    min_withdrawal: Decimal
    max_withdrawal: Decimal
    pending_purchase_orders: int
    pending_withdrawals: int
    pending_kyc: int
    automatic_deposits_enabled: bool
    automatic_withdrawals_enabled: bool


class AdminFinanceProjectionSummaryView(BaseModel):
    days: int
    ending_gtex_supply: Decimal
    ending_fan_supply: Decimal
    gtex_burn_mint_ratio: Decimal | None = None
    fan_burn_mint_ratio: Decimal | None = None
    inflation_risk: str
    recommendations: list[str] = Field(default_factory=list)


class AdminFinanceControlTowerView(BaseModel):
    generated_at: datetime
    gtex_supply: Decimal
    fan_supply: Decimal
    daily_revenue_naira: Decimal
    marketplace_fee_amount: Decimal
    fan_coin_burned_today: Decimal
    gtex_minted_today: Decimal
    gtex_burned_today: Decimal
    fan_minted_today: Decimal
    fan_burned_today: Decimal
    gtex_burn_mint_ratio: Decimal | None = None
    fan_burn_mint_ratio: Decimal | None = None
    inflation_risk: str
    liquidity_status: str
    user_spend_trend: str
    avg_spend_per_match: Decimal
    pending_purchase_orders: int
    pending_withdrawals: int
    pending_kyc: int
    history: list[AdminFinanceDailyStatView]
    top_transactions: list[AdminFinanceLargeTransactionView]
    alerts: list[AdminFinanceAlertView]
    player_price_trends: list[AdminFinancePlayerTrendView]
    tournament_pool_sizes: list[AdminFinanceTournamentPoolView]
    cash_rails: AdminFinanceCashRailView
    projection: AdminFinanceProjectionSummaryView | None = None
    manual_price_override_count: int = 0
    frozen_account_count: int = 0
    banned_account_count: int = 0
    match_kill_switch_count: int = 0
    economy_governor_mode: str | None = None


class AdminEconomySimulationConfig(BaseModel):
    daily_active_users: int = Field(default=100_000, ge=1)
    avg_matches_per_user: Decimal = Field(default=Decimal("5.0000"), ge=0)
    fan_spend_per_match: Decimal = Field(default=Decimal("10.0000"), ge=0)
    fan_mint_per_match: Decimal = Field(default=Decimal("0.0000"), ge=0)
    gtex_purchase_rate: Decimal = Field(default=Decimal("0.0200"), ge=0, le=1)
    gtex_purchase_amount: Decimal = Field(default=Decimal("1.0000"), ge=0)
    tournament_entry_gtex: Decimal = Field(default=Decimal("2.0000"), ge=0)
    tournament_participation_rate: Decimal = Field(default=Decimal("0.1200"), ge=0, le=1)
    gtex_reward_payout_per_match: Decimal = Field(default=Decimal("0.0000"), ge=0)


class AdminEconomySimulationPointView(BaseModel):
    day: int
    gtex_supply: Decimal
    fan_supply: Decimal
    gtex_minted: Decimal
    gtex_burned: Decimal
    fan_minted: Decimal
    fan_burned: Decimal
    gtex_burn_mint_ratio: Decimal | None = None
    fan_burn_mint_ratio: Decimal | None = None
    inflation_risk: str


class AdminEconomySimulationResultView(BaseModel):
    days: int
    starting_gtex_supply: Decimal
    starting_fan_supply: Decimal
    summary: AdminFinanceProjectionSummaryView
    projections: list[AdminEconomySimulationPointView]


class AdminFinanceWebhookResultView(BaseModel):
    status: str
    provider: str
    purchase_order_id: str | None = None
    withdrawal_id: str | None = None
    order_status: str | None = None
    reference: str | None = None
    signature_verified: bool = False


class ManualPriceOverrideUpsertRequest(BaseModel):
    asset_type: str = Field(min_length=2, max_length=64)
    asset_id: str = Field(min_length=1, max_length=128)
    override_price: Decimal = Field(ge=Decimal("0.0000"))
    currency: str = Field(default="coin", min_length=2, max_length=16)
    reason: str | None = Field(default=None, max_length=255)


class ManualPriceOverrideView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_type: str
    asset_id: str
    override_price: Decimal
    currency: str
    reason: str | None = None
    updated_by_user_id: str | None = None
    updated_at: datetime


class AccountControlUpsertRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    freeze_login: bool = False
    freeze_wallet: bool = False
    freeze_matches: bool = False
    freeze_social: bool = False
    ban_account: bool = False
    reason: str | None = Field(default=None, max_length=255)


class AccountControlView(BaseModel):
    user_id: str
    freeze_login: bool
    freeze_wallet: bool
    freeze_matches: bool
    freeze_social: bool
    ban_account: bool = False
    reason: str | None = None
    updated_by_user_id: str | None = None
    updated_at: datetime


class MatchKillSwitchUpsertRequest(BaseModel):
    match_id: str = Field(min_length=1, max_length=64)
    enabled: bool = True
    reason: str | None = Field(default=None, max_length=255)


class MatchKillSwitchView(BaseModel):
    match_id: str
    enabled: bool
    reason: str | None = None
    updated_by_user_id: str | None = None
    updated_at: datetime | None = None


class DuplicateDepositCandidateView(BaseModel):
    provider_key: str
    provider_reference: str
    occurrence_count: int
    order_ids: list[str] = Field(default_factory=list)


class WalletProtectionSummaryView(BaseModel):
    generated_at: datetime
    frozen_wallet_account_count: int
    banned_account_count: int
    pending_purchase_orders: int
    pending_withdrawals: int
    payment_signature_verification_enabled: bool
    duplicate_deposit_candidates: list[DuplicateDepositCandidateView] = Field(default_factory=list)
