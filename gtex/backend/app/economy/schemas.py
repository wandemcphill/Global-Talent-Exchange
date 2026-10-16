from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class GiftCatalogItemView(BaseModel):
    id: str
    key: str
    display_name: str
    tier: str
    fancoin_price: Decimal
    animation_key: str | None = None
    sound_key: str | None = None
    description: str | None = None
    active: bool
    updated_at: datetime


class GiftCatalogItemUpsertRequest(BaseModel):
    key: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=160)
    tier: str = Field(default="standard", min_length=2, max_length=32)
    fancoin_price: Decimal = Field(default=Decimal("0.0000"), ge=0)
    animation_key: str | None = Field(default=None, max_length=64)
    sound_key: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=2000)
    active: bool = True


class ServicePricingRuleView(BaseModel):
    id: str
    service_key: str
    title: str
    description: str | None = None
    price_coin: Decimal
    price_fancoin_equivalent: Decimal
    active: bool
    updated_at: datetime


class ServicePricingRuleUpsertRequest(BaseModel):
    service_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    price_coin: Decimal = Field(default=Decimal("0.0000"), ge=0)
    price_fancoin_equivalent: Decimal = Field(default=Decimal("0.0000"), ge=0)
    active: bool = True


class RevenueShareRuleView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_key: str
    scope: str
    title: str
    description: str | None = None
    platform_share_bps: int
    creator_share_bps: int
    recipient_share_bps: int | None = None
    burn_bps: int
    priority: int
    active: bool
    updated_at: datetime


class RevenueShareRuleUpsertRequest(BaseModel):
    rule_key: str = Field(min_length=2, max_length=64)
    scope: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    platform_share_bps: int = Field(default=0, ge=0, le=10_000)
    creator_share_bps: int = Field(default=0, ge=0, le=10_000)
    recipient_share_bps: int | None = Field(default=None, ge=0, le=10_000)
    burn_bps: int = Field(default=0, ge=0, le=10_000)
    priority: int = Field(default=10, ge=0, le=1000)
    active: bool = True


class GiftComboRuleView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_key: str
    title: str
    description: str | None = None
    min_combo_count: int
    window_seconds: int
    bonus_bps: int
    priority: int
    active: bool
    updated_at: datetime


class GiftComboRuleUpsertRequest(BaseModel):
    rule_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    min_combo_count: int = Field(default=2, ge=2, le=50)
    window_seconds: int = Field(default=120, ge=10, le=3600)
    bonus_bps: int = Field(default=0, ge=0, le=10_000)
    priority: int = Field(default=10, ge=0, le=1000)
    active: bool = True


class EconomyBurnEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    source_type: str
    source_id: str | None
    amount: Decimal
    unit: str
    reason: str
    ledger_transaction_id: str | None
    metadata_json: dict[str, object]
    created_at: datetime
