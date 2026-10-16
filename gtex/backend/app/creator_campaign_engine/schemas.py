from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreatorCampaignCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    vanity_code: str | None = Field(default=None, max_length=32)
    linked_competition_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CreatorCampaignUpdateRequest(BaseModel):
    linked_competition_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None
    metadata_json: dict[str, Any] | None = None


class CreatorCampaignView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_profile_id: str
    name: str
    share_code_id: str | None
    linked_competition_id: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CreatorCampaignMetricSnapshotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    snapshot_date: date
    clicks: int
    attributed_signups: int
    verified_signups: int
    qualified_joins: int
    gifts_generated: int
    gift_volume_minor: int
    rewards_generated: int
    reward_volume_minor: int
    competition_entries: int
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CreatorCampaignMetricsView(BaseModel):
    campaign_id: str
    campaign_name: str
    share_code: str | None
    attributed_signups: int
    verified_signups: int
    qualified_joins: int
    gifts_generated: int
    gift_volume_minor: int
    rewards_generated: int
    reward_volume_minor: int
    competition_entries: int
    conversion_rate: float
    efficiency_score: float
    timeline_points: list[CreatorCampaignMetricSnapshotView]
    insights: list[str]


class CampaignSnapshotRequest(BaseModel):
    snapshot_date: date | None = None
