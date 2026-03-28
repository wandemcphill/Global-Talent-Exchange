from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.match_engine.schemas import (
    MatchCommentaryCueView,
    MatchCrowdStateView,
    MatchExperienceLayerView,
    MatchSpectatorSyncView,
)


class LiveMatchScoreView(CommonSchema):
    home: int = Field(ge=0)
    away: int = Field(ge=0)


class LiveMatchWinProbabilityView(CommonSchema):
    home: float = Field(ge=0.0, le=1.0)
    draw: float = Field(ge=0.0, le=1.0)
    away: float = Field(ge=0.0, le=1.0)


class LiveMatchMarketPulseView(CommonSchema):
    home_line: float = Field(gt=0.0)
    draw_line: float = Field(gt=0.0)
    away_line: float = Field(gt=0.0)
    volatility: float = Field(ge=0.0, le=1.0)
    tension: str


class LiveMatchPossessionEstimateView(CommonSchema):
    home: int = Field(ge=0, le=100)
    away: int = Field(ge=0, le=100)


class LiveMatchRenderPointView(CommonSchema):
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)


class LiveMatchStreamEventView(CommonSchema):
    match_id: str | None = None
    event_id: str | None = None
    tick: int | None = Field(default=None, ge=0)
    minute: int = Field(ge=0, le=120)
    event_type: str
    team_id: str | None = None
    team: str | None = None
    player_id: str | None = None
    player: str | None = None
    secondary_player_id: str | None = None
    position: LiveMatchRenderPointView | None = None
    target_position: LiveMatchRenderPointView | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    experience: MatchExperienceLayerView | None = None


class LiveMatchSnapshotView(CommonSchema):
    score: LiveMatchScoreView
    possession_estimate: LiveMatchPossessionEstimateView
    current_minute: int = Field(ge=0, le=120)
    momentum_indicator: str
    win_probability: LiveMatchWinProbabilityView | None = None
    market_pulse: LiveMatchMarketPulseView | None = None
    dramatic_event: bool = False
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
    crowd_state: MatchCrowdStateView | None = None
    spectator_sync: MatchSpectatorSyncView | None = None


class SpectatorSessionView(CommonSchema):
    id: str
    match_id: str
    user_id: str
    joined_at: datetime
    read_only: bool = True
    channel: str
    websocket_path: str
    commentary_websocket_path: str | None = None
    access_source: str | None = None
    rights_owner_id: str | None = None
    viewing_fee_coin: Decimal = Decimal("0.0000")
    premium_features: dict[str, bool] = Field(default_factory=dict)
    sponsored_overlays: list[dict[str, Any]] = Field(default_factory=list)
    stadium_ads: list[dict[str, Any]] = Field(default_factory=list)
    sync_strategy: str = "deterministic_playback"
    watch_party_enabled: bool = True
    reactions_enabled: bool = True


class LiveCommentaryStreamEventView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    event_type: str
    line: str
    team: str | None = None
    player: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    cue: MatchCommentaryCueView | None = None


class MatchHighlightSummaryView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    type: str
    description: str


class MatchHighlightResponseView(CommonSchema):
    highlights: list[MatchHighlightSummaryView] = Field(default_factory=list)


class MatchHighlightShareItemView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    type: str
    description: str
    share_title: str
    share_caption: str


class MatchHighlightSharePackageView(CommonSchema):
    match_id: str
    fingerprint: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    recommended_aspect_ratios: list[str] = Field(default_factory=list)
    export_route: str
    items: list[MatchHighlightShareItemView] = Field(default_factory=list)
