from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class LiveMatchScoreView(CommonSchema):
    home: int = Field(ge=0)
    away: int = Field(ge=0)


class LiveMatchPossessionEstimateView(CommonSchema):
    home: int = Field(ge=0, le=100)
    away: int = Field(ge=0, le=100)


class LiveMatchStreamEventView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    event_type: str
    team: str | None = None
    player: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LiveMatchSnapshotView(CommonSchema):
    score: LiveMatchScoreView
    possession_estimate: LiveMatchPossessionEstimateView
    current_minute: int = Field(ge=0, le=120)
    momentum_indicator: str
    status: str = "live"
    read_only: bool = True


class LiveMatchStateView(CommonSchema):
    match_id: str
    channel: str
    is_live: bool
    read_only: bool = True
    spectator_count: int = Field(default=0, ge=0)
    event_count: int = Field(default=0, ge=0)
    snapshot: LiveMatchSnapshotView


class SpectatorSessionView(CommonSchema):
    id: str
    match_id: str
    user_id: str
    joined_at: datetime
    read_only: bool = True
    channel: str
    websocket_path: str


class MatchHighlightSummaryView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    type: str
    description: str


class MatchHighlightResponseView(CommonSchema):
    highlights: list[MatchHighlightSummaryView] = Field(default_factory=list)
