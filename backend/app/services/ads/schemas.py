from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class MatchAdPlacementType(StrEnum):
    PRE_ROLL = "pre_roll"
    LIVE_BANNER = "live_banner"
    SPONSORED_HIGHLIGHT = "sponsored_highlight"
    REWARDED_AD = "rewarded_ad"


class MatchAdPlacementView(CommonSchema):
    ad_id: str
    ad_type: MatchAdPlacementType
    placement: str
    brand: str
    message: str
    event_id: str | None = None
    active_from_second: int | None = Field(default=None, ge=0)
    active_until_second: int | None = Field(default=None, ge=0)
    reward_coins: int | None = Field(default=None, ge=0)
    cta_label: str | None = None
    pricing_cpm_usd: float | None = Field(default=None, ge=0.0)
    estimated_value_usd: float | None = Field(default=None, ge=0.0)
    targeting_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MatchViewerMonetizationView(CommonSchema):
    ads_enabled: bool = False
    premium_ad_free: bool = False
    placements: list[MatchAdPlacementView] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "MatchAdPlacementType",
    "MatchAdPlacementView",
    "MatchViewerMonetizationView",
]
