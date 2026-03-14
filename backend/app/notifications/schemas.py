from __future__ import annotations

from typing import Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: str
    user_id: str | None
    topic: str
    template_key: str | None = None
    resource_id: str | None = None
    fixture_id: str | None = None
    competition_id: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: datetime | None = None
    is_read: bool = False


class NotificationPreferenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    allow_wallet: bool
    allow_market: bool
    allow_story: bool
    allow_competition: bool
    allow_social: bool
    allow_broadcasts: bool
    quiet_hours_enabled: bool
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NotificationPreferenceUpdate(BaseModel):
    allow_wallet: bool = True
    allow_market: bool = True
    allow_story: bool = True
    allow_competition: bool = True
    allow_social: bool = True
    allow_broadcasts: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NotificationSubscriptionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subscription_key: str
    subscription_type: str
    label: str
    active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NotificationSubscriptionCreate(BaseModel):
    subscription_key: str
    subscription_type: str = "general"
    label: str
    active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PlatformAnnouncementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    announcement_key: str
    title: str
    body: str
    audience: str
    severity: str
    active: bool
    deliver_as_notification: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PlatformAnnouncementCreate(BaseModel):
    announcement_key: str
    title: str
    body: str
    audience: str = "all"
    severity: str = "info"
    active: bool = True
    deliver_as_notification: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)
