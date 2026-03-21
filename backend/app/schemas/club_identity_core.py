from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.common.enums.club_brand_asset_type import ClubBrandAssetType
from app.common.enums.club_identity_visibility import ClubIdentityVisibility
from app.common.schemas.base import CommonSchema


class _ClubOrmSchema(CommonSchema):
    model_config = ConfigDict(from_attributes=True)


class ClubProfileCore(_ClubOrmSchema):
    id: str
    owner_user_id: str
    club_name: str
    short_name: str | None = None
    slug: str
    crest_asset_ref: str | None = None
    primary_color: str
    secondary_color: str
    accent_color: str
    home_venue_name: str | None = None
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    description: str | None = None
    visibility: ClubIdentityVisibility
    founded_at: date | None = None
    created_at: datetime
    updated_at: datetime


class ClubBrandingAssetCore(_ClubOrmSchema):
    id: str
    club_id: str
    asset_type: ClubBrandAssetType
    asset_name: str
    asset_ref: str | None = None
    catalog_item_id: str | None = None
    slot_key: str | None = None
    is_active: bool
    moderation_status: str
    moderation_reason: str | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubIdentityThemeCore(_ClubOrmSchema):
    id: str
    club_id: str
    name: str
    header_asset_ref: str | None = None
    backdrop_asset_ref: str | None = None
    cabinet_theme_code: str | None = None
    frame_code: str | None = None
    visibility: ClubIdentityVisibility
    is_active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubShowcaseSnapshotCore(_ClubOrmSchema):
    id: str
    club_id: str
    snapshot_key: str
    reputation_score: int
    dynasty_score: int
    featured_trophy_id: str | None = None
    theme_name: str | None = None
    showcase_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
