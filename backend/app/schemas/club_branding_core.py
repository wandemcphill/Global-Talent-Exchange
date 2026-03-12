from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from backend.app.common.enums.club_cosmetic_purchase_type import ClubCosmeticPurchaseType
from backend.app.common.enums.jersey_slot_type import JerseySlotType
from backend.app.common.schemas.base import CommonSchema


class _ClubOrmSchema(CommonSchema):
    model_config = ConfigDict(from_attributes=True)


class ClubJerseyDesignCore(_ClubOrmSchema):
    id: str
    club_id: str
    name: str
    slot_type: JerseySlotType
    base_template_id: str
    primary_color: str
    secondary_color: str
    trim_color: str
    sleeve_style: str | None = None
    motto_text: str | None = None
    number_style: str | None = None
    crest_placement: str
    preview_asset_ref: str | None = None
    is_active: bool
    moderation_status: str
    moderation_reason: str | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubCosmeticCatalogItemCore(_ClubOrmSchema):
    id: str
    sku: str
    purchase_type: ClubCosmeticPurchaseType
    asset_type: str | None = None
    name: str
    description: str
    price_minor: int
    currency_code: str
    service_fee_minor: int
    is_active: bool
    moderation_required: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubCosmeticPurchaseCore(_ClubOrmSchema):
    id: str
    purchase_ref: str
    club_id: str
    buyer_user_id: str
    catalog_item_id: str
    purchase_type: ClubCosmeticPurchaseType
    amount_minor: int
    currency_code: str
    status: str
    review_status: str
    review_notes: str | None = None
    payment_reference: str | None = None
    fraud_flagged: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
