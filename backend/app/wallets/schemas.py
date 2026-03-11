from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.wallet import LedgerAccountKind, LedgerUnit, PaymentProvider, PaymentStatus


class WalletAccountBalance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    label: str
    unit: LedgerUnit
    kind: LedgerAccountKind
    allow_negative: bool
    is_active: bool
    balance: Decimal


class PaymentEventCreate(BaseModel):
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


class PaymentEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
