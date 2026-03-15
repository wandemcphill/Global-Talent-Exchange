from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.wallet import LedgerAccountKind, LedgerEntryReason, LedgerSourceTag, LedgerUnit, PaymentProvider, PaymentStatus, PayoutStatus


class WalletAccountBalance(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="WalletAccountBalance",
        json_schema_extra={
            "example": {
                "id": "acct-123",
                "code": "credit_available",
                "label": "Available Credits",
                "unit": "credit",
                "kind": "user",
                "allow_negative": False,
                "is_active": True,
                "balance": "50.0000",
            }
        },
    )

    id: str
    code: str
    label: str
    unit: LedgerUnit
    kind: LedgerAccountKind
    allow_negative: bool
    is_active: bool
    balance: Decimal


class PaymentEventCreate(BaseModel):
    model_config = ConfigDict(
        title="PaymentEventCreate",
        json_schema_extra={
            "example": {
                "provider": "monnify",
                "provider_reference": "monnify-ref-001",
                "amount": "50.0000",
                "pack_code": "starter-50",
            }
        },
    )

    provider: PaymentProvider
    provider_reference: str = Field(min_length=3, max_length=128)
    amount: Decimal
    pack_code: str | None = Field(default=None, max_length=64)

    @field_validator("provider_reference")
    @classmethod
    def normalize_reference(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Provider reference is required.")
        return candidate

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Payment amounts must be positive.")
        return value


class PurchaseOrderSourceScope(str, Enum):
    WALLET = "wallet"
    MARKET = "market"


class PurchaseOrderQuoteRequest(BaseModel):
    amount: Decimal
    input_unit: str = Field(default="fiat")
    provider_key: str = Field(min_length=2, max_length=64)
    unit: LedgerUnit = LedgerUnit.CREDIT
    source_scope: PurchaseOrderSourceScope = PurchaseOrderSourceScope.WALLET

    @field_validator("input_unit")
    @classmethod
    def validate_input_unit(cls, value: str) -> str:
        candidate = value.strip().lower()
        if candidate not in {"fiat", "coin"}:
            raise ValueError("input_unit must be fiat or coin")
        return candidate

    @field_validator("amount")
    @classmethod
    def validate_quote_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Purchase amount must be positive.")
        return value


class PurchaseOrderQuoteView(BaseModel):
    amount_fiat: Decimal
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    currency_code: str
    rate_value: Decimal
    rate_direction: str
    unit: LedgerUnit
    processor_mode: str
    payout_channel: str
    provider_key: str
    source_scope: PurchaseOrderSourceScope


class PurchaseOrderCreateRequest(PurchaseOrderQuoteRequest):
    provider_reference: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=255)


class PurchaseOrderView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    status: str
    provider_key: str
    provider_reference: str | None
    unit: LedgerUnit
    amount_fiat: Decimal
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    currency_code: str
    rate_value: Decimal
    rate_direction: str
    processor_mode: str
    payout_channel: str
    source_scope: PurchaseOrderSourceScope
    ledger_transaction_id: str | None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    settled_at: datetime | None = None
    failed_at: datetime | None = None
    refunded_at: datetime | None = None
    chargeback_at: datetime | None = None
    reversed_at: datetime | None = None
    cancelled_at: datetime | None = None
    expired_at: datetime | None = None


class PurchaseOrderStatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=32)
    notes: str | None = Field(default=None, max_length=255)


class MarketTopupSourceScope(str, Enum):
    MARKET = "market"
    PROMOTION = "promotion"
    LIQUIDITY = "liquidity"


class MarketTopupQuoteRequest(BaseModel):
    amount: Decimal
    fee_bps: int = Field(default=0, ge=0, le=10_000)
    unit: LedgerUnit = LedgerUnit.COIN

    @field_validator("amount")
    @classmethod
    def validate_topup_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Topup amount must be positive.")
        return value


class MarketTopupQuoteView(BaseModel):
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    unit: LedgerUnit


class MarketTopupCreateRequest(MarketTopupQuoteRequest):
    user_id: str = Field(min_length=1)
    source_scope: MarketTopupSourceScope = MarketTopupSourceScope.MARKET
    notes: str | None = Field(default=None, max_length=255)


class MarketTopupStatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=32)
    notes: str | None = Field(default=None, max_length=255)


class MarketTopupView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    status: str
    user_id: str
    unit: LedgerUnit
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    source_scope: MarketTopupSourceScope
    processor_mode: str
    payout_channel: str
    ledger_transaction_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    processed_at: datetime | None = None
    settled_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    reversed_at: datetime | None = None


class WithdrawalRequestCreate(BaseModel):
    model_config = ConfigDict(title="WithdrawalRequestCreate")

    amount: Decimal
    unit: LedgerUnit = LedgerUnit.COIN
    destination_reference: str = Field(min_length=4, max_length=255)
    source_scope: str = Field(default="trade")
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_withdrawal_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        return value

    @field_validator("source_scope")
    @classmethod
    def normalize_scope(cls, value: str) -> str:
        candidate = value.strip().lower()
        if candidate not in {"trade", "competition", "user_hosted_gift", "gtex_competition_gift", "national_reward"}:
            raise ValueError("source_scope must be trade, competition, user_hosted_gift, gtex_competition_gift, or national_reward")
        return candidate


class WithdrawalRequestView(BaseModel):
    model_config = ConfigDict(title="WithdrawalRequestView")

    payout_request_id: str
    amount: Decimal
    fee_amount: Decimal
    total_debit: Decimal
    unit: LedgerUnit
    status: PayoutStatus
    source_scope: str
    destination_reference: str
    processing_mode: str = "manual_bank_transfer"
    payout_channel: str = "bank_transfer"
    notes: str | None = None
    requested_at: datetime
    updated_at: datetime


class PaymentEventView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="PaymentEventView",
        json_schema_extra={
            "example": {
                "id": "pay-123",
                "provider": "monnify",
                "provider_reference": "monnify-ref-001",
                "pack_code": "starter-50",
                "amount": "50.0000",
                "unit": "credit",
                "status": "pending",
                "created_at": "2026-03-11T12:00:00Z",
                "verified_at": None,
                "processed_at": None,
                "ledger_transaction_id": None,
            }
        },
    )

    id: str
    provider: PaymentProvider
    provider_reference: str
    pack_code: str | None
    amount: Decimal
    unit: LedgerUnit
    status: PaymentStatus
    created_at: datetime
    verified_at: datetime | None
    processed_at: datetime | None
    ledger_transaction_id: str | None


class WalletSummaryView(BaseModel):
    model_config = ConfigDict(
        title="WalletSummaryView",
        json_schema_extra={
            "example": {
                "available_balance": "50.0000",
                "reserved_balance": "50.0000",
                "total_balance": "100.0000",
                "currency": "credit",
            }
        },
    )

    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    currency: LedgerUnit


class WalletLedgerEntryView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="WalletLedgerEntryView",
        json_schema_extra={
            "example": {
                "id": "entry-123",
                "transaction_id": "txn-123",
                "account_id": "acct-123",
                "amount": "-50.0000",
                "unit": "credit",
                "reason": "withdrawal_hold",
                "source_tag": "market_topup",
                "reference": "ord-123",
                "external_reference": None,
                "description": "Reserved credits for open order",
                "created_at": "2026-03-11T12:00:00Z",
            }
        },
    )

    id: str
    transaction_id: str
    account_id: str
    amount: Decimal
    unit: LedgerUnit
    reason: LedgerEntryReason
    source_tag: LedgerSourceTag
    reference: str | None
    external_reference: str | None
    description: str | None
    created_at: datetime


class WalletLedgerPageView(BaseModel):
    model_config = ConfigDict(
        title="WalletLedgerPageView",
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "total": 2,
                "items": [
                    {
                        "id": "entry-123",
                        "transaction_id": "txn-123",
                        "account_id": "acct-123",
                        "amount": "-50.0000",
                        "unit": "credit",
                        "reason": "withdrawal_hold",
                        "reference": "ord-123",
                        "external_reference": None,
                        "description": "Reserved credits for open order",
                        "created_at": "2026-03-11T12:00:00Z",
                    }
                ],
            }
        },
    )

    page: int
    page_size: int
    total: int
    items: list[WalletLedgerEntryView]


class PortfolioHoldingView(BaseModel):
    model_config = ConfigDict(
        title="WalletPortfolioHoldingView",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "quantity": "2.0000",
                "average_cost": "10.0000",
                "current_price": "12.0000",
                "market_value": "24.0000",
                "unrealized_pl": "4.0000",
                "unrealized_pl_percent": "20.0000",
            }
        },
    )

    player_id: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal
    unrealized_pl_percent: Decimal


class PortfolioSnapshotView(BaseModel):
    model_config = ConfigDict(
        title="PortfolioSnapshotView",
        json_schema_extra={
            "example": {
                "user_id": "user-123",
                "currency": "credit",
                "available_balance": "80.0000",
                "reserved_balance": "20.0000",
                "total_balance": "100.0000",
                "holdings": [
                    {
                        "player_id": "player-123",
                        "quantity": "2.0000",
                        "average_cost": "10.0000",
                        "current_price": "12.0000",
                        "market_value": "24.0000",
                        "unrealized_pl": "4.0000",
                        "unrealized_pl_percent": "20.0000",
                    }
                ],
            }
        },
    )

    user_id: str
    currency: LedgerUnit
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    holdings: list[PortfolioHoldingView]


class WalletAdaptiveInsightView(BaseModel):
    label: str
    value: str
    tone: str = "info"


class WalletAdaptiveOverviewView(BaseModel):
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    currency: LedgerUnit
    withdrawable_balance: Decimal
    competition_reward_balance: Decimal = Decimal("0.0000")
    competition_reward_withdrawable_balance: Decimal = Decimal("0.0000")
    pending_withdrawals: int = 0
    payment_provider_status: dict[str, str] = Field(default_factory=dict)
    processor_mode: str = "manual_bank_transfer"
    deposits_via_bank_transfer: bool = True
    payouts_via_bank_transfer: bool = True
    egame_withdrawals_enabled: bool = False
    trade_withdrawals_enabled: bool = True
    country_code: str = "GLOBAL"
    insights: list[WalletAdaptiveInsightView] = Field(default_factory=list)


class WalletOverviewView(BaseModel):
    available_balance: Decimal
    pending_deposits: Decimal
    pending_withdrawals: Decimal
    total_inflow: Decimal
    total_outflow: Decimal
    withdrawable_now: Decimal
    currency: LedgerUnit
