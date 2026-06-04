from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

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


class PaymentQueueActionRequest(BaseModel):
    admin_notes: str | None = Field(default=None, max_length=1000)
    reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=1000)


class PaymentQueueTabView(BaseModel):
    key: str
    label: str
    total: int
    action_state: str = "enabled"


class PaymentQueueSectionView(BaseModel):
    key: str
    label: str
    item_type: str
    statuses: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    action_state: str = "enabled"
    blocked_reason: str | None = None


class PaymentQueueView(BaseModel):
    generated_at: datetime
    tabs: list[PaymentQueueTabView]
    sections: dict[str, PaymentQueueSectionView]
    pending: PaymentQueueSectionView
    approved: PaymentQueueSectionView
    rejected: PaymentQueueSectionView
    bids: PaymentQueueSectionView


class PaymentQueueActionResultView(BaseModel):
    action: str
    item_type: str
    action_state: str
    business_state_changed: bool | None = None
    wallet_state_changed: bool | None = None
    audit_reference: str | None = None
    audit: dict[str, Any] | None = None
    notes: dict[str, Any] | None = None
    item: dict[str, Any] | None = None
    blocked_reason: str | None = None


class AdminLockAcquireRequest(BaseModel):
    ttl_seconds: int = Field(default=600, ge=30, le=3600)


class AdminLockStateView(BaseModel):
    state: str
    action_state: str
    resource_type: str
    resource_id: str
    locked_by_user_id: str | None = None
    locked_by_email: str | None = None
    locked_at: datetime | None = None
    expires_at: datetime | None = None
    blocked_reason: str | None = None
    audit_reference: str | None = None


class AdminExportRequest(BaseModel):
    export_type: str = Field(min_length=2, max_length=64)
    format: str = Field(default="csv", min_length=3, max_length=8)
    filters: dict[str, Any] = Field(default_factory=dict)


class AdminExportStatusView(BaseModel):
    export_id: str
    status: str
    export_type: str
    format: str
    filters: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None
    blocked_reason: str | None = None
    audit_reference: str | None = None
    requested_audit_reference: str | None = None
    audit: dict[str, Any] | None = None
    artifact: dict[str, Any] | None = None


class AdminBulkActionRequest(BaseModel):
    item_type: str = Field(min_length=2, max_length=64)
    action: str = Field(min_length=2, max_length=64)
    item_ids: list[str] = Field(min_length=1, max_length=200)
    admin_notes: str = Field(min_length=1, max_length=1000)


class AdminBulkActionStatusView(BaseModel):
    bulk_action_id: str
    status: str
    item_type: str
    action: str
    item_ids: list[str] = Field(default_factory=list)
    queued_count: int
    blocked_count: int = 0
    requested_at: datetime
    completed_at: datetime | None = None
    audit_reference: str | None = None
    audit: dict[str, Any] | None = None
    blocked_reason: str | None = None


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


class WalletTransactionLockView(BaseModel):
    user_id: str
    operation: str
    reason: str | None = None
    updated_by_user_id: str | None = None
    updated_at: datetime
    expires_at: datetime


class WalletProtectionSummaryView(BaseModel):
    generated_at: datetime
    frozen_wallet_account_count: int
    banned_account_count: int
    pending_purchase_orders: int
    pending_withdrawals: int
    active_wallet_transaction_lock_count: int = 0
    payment_signature_verification_enabled: bool
    active_wallet_transaction_locks: list[WalletTransactionLockView] = Field(default_factory=list)
    duplicate_deposit_candidates: list[DuplicateDepositCandidateView] = Field(default_factory=list)


class ReconciliationIssueView(BaseModel):
    issue_type: str
    resource_id: str
    reference: str | None = None
    detail: str


class PaymentReconciliationSummaryView(BaseModel):
    generated_at: datetime
    pending_payment_events: int
    settled_purchase_orders_missing_ledger: int
    settled_payment_events_missing_ledger: int
    confirmed_deposits_missing_ledger: int
    duplicate_provider_references: int
    issues: list[ReconciliationIssueView] = Field(default_factory=list)
