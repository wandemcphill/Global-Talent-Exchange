from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StoryFeedPublishRequest(BaseModel):
    story_type: str = Field(min_length=2, max_length=48)
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=4000)
    audience: str = Field(default="public", max_length=32)
    subject_type: str | None = Field(default=None, max_length=48)
    subject_id: str | None = Field(default=None, max_length=64)
    country_code: str | None = Field(default=None, max_length=8)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    featured: bool = False
    scheduled_for: datetime | None = None


class StoryFeedScheduleRequest(BaseModel):
    scheduled_for: datetime


class StoryFeedRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class StoryFeedItemResponse(BaseModel):
    id: str
    story_type: str
    audience: str
    title: str
    body: str
    subject_type: str | None
    subject_id: str | None
    country_code: str | None
    metadata_json: dict[str, Any]
    featured: bool
    moderation_status: str
    scheduled_for: datetime | None
    created_at: datetime
    updated_at: datetime


class StoryDigestResponse(BaseModel):
    top_stories: list[StoryFeedItemResponse]
    country_spotlight: list[StoryFeedItemResponse]
    feature_stories: list[StoryFeedItemResponse]
