from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.wallet import LedgerUnit


class PaymentMethodView(BaseModel):
    method_key: str
    display_name: str
    provider_key: str
    method_group: str
    unit: LedgerUnit
    deposits_enabled: bool
    withdrawals_enabled: bool
    is_live: bool
    maintenance_message: str | None


class PaymentQuoteRequest(BaseModel):
    amount: Decimal
    input_unit: str = Field(default="fiat")
    method_key: str | None = None
    provider_key: str | None = None
    unit: LedgerUnit | None = None

    @field_validator("input_unit")
    @classmethod
    def validate_input_unit(cls, value: str) -> str:
        candidate = value.strip().lower()
        if candidate not in {"fiat", "coin"}:
            raise ValueError("input_unit must be fiat or coin")
        return candidate

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be positive.")
        return value


class PaymentQuoteView(BaseModel):
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
    source_scope: str


class PaymentOrderCreateRequest(PaymentQuoteRequest):
    provider_reference: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=255)


class PaymentOrderView(BaseModel):
    order_id: str
    reference: str
    status: str
    provider_key: str
    unit: LedgerUnit
    gross_amount: Decimal
    net_amount: Decimal
    currency_code: str
    metadata: dict[str, Any]
