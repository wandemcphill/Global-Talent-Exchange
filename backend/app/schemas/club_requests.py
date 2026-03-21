from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field

from app.common.enums.club_brand_asset_type import ClubBrandAssetType
from app.common.enums.club_identity_visibility import ClubIdentityVisibility
from app.common.enums.jersey_slot_type import JerseySlotType
from app.common.schemas.base import CommonSchema


class ClubCreateRequest(CommonSchema):
    club_name: str = Field(min_length=2, max_length=120)
    short_name: str | None = Field(default=None, max_length=40)
    slug: str = Field(min_length=2, max_length=120)
    crest_asset_ref: str | None = Field(default=None, max_length=255)
    primary_color: str = Field(min_length=3, max_length=16)
    secondary_color: str = Field(min_length=3, max_length=16)
    accent_color: str = Field(min_length=3, max_length=16)
    home_venue_name: str | None = Field(default=None, max_length=120)
    country_code: str | None = Field(default=None, max_length=8)
    region_name: str | None = Field(default=None, max_length=120)
    city_name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    visibility: ClubIdentityVisibility = ClubIdentityVisibility.PUBLIC
    founded_at: date | None = None


class ClubUpdateRequest(CommonSchema):
    club_name: str | None = Field(default=None, min_length=2, max_length=120)
    short_name: str | None = Field(default=None, max_length=40)
    crest_asset_ref: str | None = Field(default=None, max_length=255)
    primary_color: str | None = Field(default=None, min_length=3, max_length=16)
    secondary_color: str | None = Field(default=None, min_length=3, max_length=16)
    accent_color: str | None = Field(default=None, min_length=3, max_length=16)
    home_venue_name: str | None = Field(default=None, max_length=120)
    country_code: str | None = Field(default=None, max_length=8)
    region_name: str | None = Field(default=None, max_length=120)
    city_name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    visibility: ClubIdentityVisibility | None = None
    founded_at: date | None = None


class BrandingAssetUpsertRequest(CommonSchema):
    asset_type: ClubBrandAssetType
    asset_name: str = Field(min_length=2, max_length=120)
    asset_ref: str | None = Field(default=None, max_length=255)
    slot_key: str | None = Field(default=None, max_length=64)
    catalog_item_id: str | None = Field(default=None, max_length=36)
    custom_text: str | None = Field(default=None, max_length=80)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class BrandingUpsertRequest(CommonSchema):
    theme_name: str | None = Field(default=None, max_length=120)
    header_asset_ref: str | None = Field(default=None, max_length=255)
    backdrop_asset_ref: str | None = Field(default=None, max_length=255)
    cabinet_theme_code: str | None = Field(default=None, max_length=64)
    frame_code: str | None = Field(default=None, max_length=64)
    visibility: ClubIdentityVisibility = ClubIdentityVisibility.PUBLIC
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    assets: list[BrandingAssetUpsertRequest] = Field(default_factory=list)


class JerseyCreateRequest(CommonSchema):
    name: str = Field(min_length=2, max_length=80)
    slot_type: JerseySlotType
    base_template_id: str = Field(min_length=2, max_length=64)
    primary_color: str = Field(min_length=3, max_length=16)
    secondary_color: str = Field(min_length=3, max_length=16)
    trim_color: str = Field(min_length=3, max_length=16)
    sleeve_style: str | None = Field(default=None, max_length=32)
    motto_text: str | None = Field(default=None, max_length=80)
    number_style: str | None = Field(default=None, max_length=32)
    crest_placement: str = Field(default="left_chest", min_length=3, max_length=32)
    preview_asset_ref: str | None = Field(default=None, max_length=255)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class JerseyUpdateRequest(CommonSchema):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    base_template_id: str | None = Field(default=None, min_length=2, max_length=64)
    primary_color: str | None = Field(default=None, min_length=3, max_length=16)
    secondary_color: str | None = Field(default=None, min_length=3, max_length=16)
    trim_color: str | None = Field(default=None, min_length=3, max_length=16)
    sleeve_style: str | None = Field(default=None, max_length=32)
    motto_text: str | None = Field(default=None, max_length=80)
    number_style: str | None = Field(default=None, max_length=32)
    crest_placement: str | None = Field(default=None, min_length=3, max_length=32)
    preview_asset_ref: str | None = Field(default=None, max_length=255)
    metadata_json: dict[str, Any] | None = None


class CatalogPurchaseRequest(CommonSchema):
    club_id: str = Field(min_length=1, max_length=36)
    catalog_item_id: str = Field(min_length=1, max_length=36)
    payment_reference: str | None = Field(default=None, max_length=128)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
