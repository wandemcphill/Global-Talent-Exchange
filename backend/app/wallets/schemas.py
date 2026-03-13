from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.wallet import LedgerAccountKind, LedgerEntryReason, LedgerUnit, PaymentProvider, PaymentStatus, PayoutStatus


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


class WithdrawalRequestCreate(BaseModel):
    model_config = ConfigDict(title="WithdrawalRequestCreate")

    amount: Decimal
    unit: LedgerUnit = LedgerUnit.CREDIT
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
        if candidate not in {"trade", "competition"}:
            raise ValueError("source_scope must be trade or competition")
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
    insights: list[WalletAdaptiveInsightView] = Field(default_factory=list)
