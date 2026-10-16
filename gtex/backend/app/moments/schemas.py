from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class MomentClipView(CommonSchema):
    job_id: str | None = None
    queue_name: str | None = None
    storage_key: str | None = None
    cdn_path: str | None = None
    render_status: str = "queued"


class MomentBoostView(CommonSchema):
    initial_score: float = Field(ge=0.0)
    priority_boost: float = Field(ge=0.0)
    hot_window_multiplier: float = Field(ge=1.0)
    final_score: float = Field(ge=0.0)
    reasons: list[str] = Field(default_factory=list)


class MomentDestinationView(CommonSchema):
    viral_engine: str = "queued"
    trending_feed: str = "pushed"
    websocket_broadcast: str = "broadcast"


class LiveMomentView(CommonSchema):
    moment_id: str
    match_id: str
    source_event_id: str
    event_type: str
    source_event_type: str
    detected_events: list[str] = Field(default_factory=list)
    minute: int = Field(ge=0, le=120)
    clock: str | None = None
    team_id: str | None = None
    team: str | None = None
    player_id: str | None = None
    player: str | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    scoreline: str
    distribution_multiplier: float = Field(ge=1.0)
    clip: MomentClipView
    boost: MomentBoostView
    destinations: MomentDestinationView
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveMomentsResponse(CommonSchema):
    moments: list[LiveMomentView] = Field(default_factory=list)
    generated_at: datetime
    total: int = Field(ge=0)


__all__ = [
    "LiveMomentView",
    "LiveMomentsResponse",
    "MomentBoostView",
    "MomentClipView",
    "MomentDestinationView",
]
