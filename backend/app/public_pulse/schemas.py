from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LiveWorldPulseView(BaseModel):
    clubs_on_gtex: int = Field(ge=0)
    users_online: int = Field(ge=0)
    players_online: int = Field(ge=0)
    users_online_window_seconds: int = Field(ge=60)
    visitors_today: int = Field(ge=0, default=0)
    page_views_today: int = Field(ge=0, default=0)
    registered_users: int = Field(ge=0, default=0)
    generated_at: datetime
    labels: dict[str, str] = Field(default_factory=dict)


class PublicTrafficHeartbeatCreate(BaseModel):
    visitor_id: UUID
    path: str = Field(default="/", min_length=1, max_length=200)
    page_view: bool = True


class PublicTrafficHeartbeatView(BaseModel):
    accepted: bool = True
    recorded_page_view: bool = False
    heartbeat_interval_seconds: int = Field(ge=10)
