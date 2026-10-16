from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from app.common.schemas.base import CommonSchema
from app.viral.schemas import ViralClipView


class SponsoredClipTargetAudienceView(CommonSchema):
    formats: list[str] = Field(default_factory=list)
    creators: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


class SponsoredClipCreateRequest(CommonSchema):
    advertiser_id: str = Field(min_length=1, max_length=36)
    clip_id: str = Field(min_length=1, max_length=120)
    budget: Decimal = Field(gt=0)
    bid_cpm: Decimal = Field(gt=0)
    target_audience: SponsoredClipTargetAudienceView = Field(default_factory=SponsoredClipTargetAudienceView)
    start_time: datetime
    end_time: datetime
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_window(self) -> "SponsoredClipCreateRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class SponsoredRevenueAttributionView(CommonSchema):
    creator_share: Decimal
    platform_share: Decimal
    growth_pool_share: Decimal


class SponsoredClipPerformanceView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_id: str
    clip_id: str
    budget: Decimal
    bid_cpm: Decimal
    target_audience: SponsoredClipTargetAudienceView
    impressions_served: int
    clicks: int
    conversions: int
    total_watch_time_seconds: float
    avg_watch_time_seconds: float
    ctr: float
    conversion_rate: float
    spend: Decimal
    revenue_attribution: SponsoredRevenueAttributionView
    max_impressions: int
    remaining_impressions: int
    pacing_state: str
    eligible: bool
    start_time: datetime
    end_time: datetime
    is_active: bool


class SponsoredClipPerformanceSummaryView(CommonSchema):
    ad_count: int
    impressions: int
    clicks: int
    conversions: int
    spend: Decimal
    revenue_attribution: SponsoredRevenueAttributionView


class SponsoredClipPerformanceResponse(CommonSchema):
    ads: list[SponsoredClipPerformanceView] = Field(default_factory=list)
    summary: SponsoredClipPerformanceSummaryView
    generated_at: datetime


class SponsoredFeedTrackingView(CommonSchema):
    tracking_token: str
    impression_event: str = "sponsored_clip.impression"
    click_event: str = "sponsored_clip.click"
    watch_event: str = "sponsored_clip.watch"
    conversion_event: str = "sponsored_clip.conversion"


class SponsoredFeedCampaignView(CommonSchema):
    id: str
    advertiser_id: str
    budget: Decimal
    bid_cpm: Decimal
    target_audience: SponsoredClipTargetAudienceView
    impressions_served: int
    clicks: int
    conversions: int
    remaining_impressions: int
    pacing_state: str
    revenue_attribution: SponsoredRevenueAttributionView
    tracking: SponsoredFeedTrackingView


class SponsoredFeedScoreView(CommonSchema):
    source: Literal["organic", "auction"]
    final_score: float = Field(ge=0.0)
    organic_score: float | None = Field(default=None, ge=0.0)
    ad_score: float | None = Field(default=None, ge=0.0)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_engagement: float | None = Field(default=None, ge=0.0, le=1.0)


class SponsoredFeedItemView(ViralClipView):
    item_type: Literal["organic", "sponsored"]
    slot_index: int = Field(ge=0)
    final_score: float = Field(ge=0.0)
    organic_rank: int | None = Field(default=None, ge=1)
    organic_score: float | None = Field(default=None, ge=0.0)
    ad_score: float | None = Field(default=None, ge=0.0)
    campaign: SponsoredFeedCampaignView | None = None
    score_details: SponsoredFeedScoreView


class SponsoredFeedResponse(CommonSchema):
    items: list[SponsoredFeedItemView] = Field(default_factory=list)
    generated_at: datetime
    session_id: str
    injection_interval: int = Field(ge=5, le=8)
    organic_count: int = Field(default=0, ge=0)
    sponsored_count: int = Field(default=0, ge=0)
    personalization: dict[str, Any] = Field(default_factory=dict)
