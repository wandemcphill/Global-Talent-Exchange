from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FxRateView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    currency: str
    rate_to_naira: Decimal
    is_active: bool
    updated_at: datetime


class FxRateUpsertRequest(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    rate_to_naira: Decimal = Field(gt=0)


class RegionalPricingRuleView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    region_code: str
    label: str
    price_multiplier: Decimal
    withdrawal_limit_multiplier: Decimal
    kyc_tier_label: str
    tax_tracking_required: bool
    compliance_note: str | None = None
    updated_at: datetime


class RegionalPricingRuleUpsertRequest(BaseModel):
    region_code: str = Field(min_length=2, max_length=16)
    label: str = Field(min_length=2, max_length=64)
    price_multiplier: Decimal = Field(gt=0)
    withdrawal_limit_multiplier: Decimal = Field(gt=0)
    kyc_tier_label: str = Field(min_length=2, max_length=32)
    tax_tracking_required: bool = False
    compliance_note: str | None = Field(default=None, max_length=255)


class FxQuoteView(BaseModel):
    gtex_amount: Decimal
    currency: str
    region_code: str
    rate_to_naira: Decimal
    base_gtex_naira_price: Decimal
    naira_value: Decimal
    base_quote: Decimal
    price_multiplier: Decimal
    final_quote: Decimal
    kyc_tier_label: str | None = None
    withdrawal_limit_multiplier: Decimal | None = None
    tax_tracking_required: bool
    compliance_note: str | None = None
