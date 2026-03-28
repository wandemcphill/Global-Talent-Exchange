from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class BroadcastCommentatorView(CommonSchema):
    name: str
    role: str
    style: str


class BroadcastPlayerSpotlightView(CommonSchema):
    player_id: str | None = None
    player_name: str
    team_id: str | None = None
    team_name: str | None = None
    rating: float | None = Field(default=None, ge=0.0, le=10.0)
    headline: str
    identity_fit_score: float | None = Field(default=None, ge=0.0, le=100.0)


class BroadcastScoreboardView(CommonSchema):
    home_team_name: str
    away_team_name: str
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    minute: int = Field(ge=0, le=120)
    status: str


class BroadcastOverlayView(CommonSchema):
    scoreboard: BroadcastScoreboardView
    team_names: dict[str, str] = Field(default_factory=dict)
    possession_indicator: dict[str, Any] = Field(default_factory=dict)
    player_highlight_card: BroadcastPlayerSpotlightView | None = None
    stadium_ads: list[dict[str, Any]] = Field(default_factory=list)
    sponsored_overlays: list[dict[str, Any]] = Field(default_factory=list)
    advanced_stats_enabled: bool = False


class DualCommentaryLineView(CommonSchema):
    event_id: str
    minute: int = Field(ge=0, le=120)
    event_type: str
    play_by_play: str
    analyst: str


class BroadcastHalftimeSegmentView(CommonSchema):
    key_stats: list[str] = Field(default_factory=list)
    tactical_insights: list[str] = Field(default_factory=list)
    standout_players: list[BroadcastPlayerSpotlightView] = Field(default_factory=list)


class BroadcastFulltimeWrapView(CommonSchema):
    summary_narrative: str
    key_moments_recap: list[str] = Field(default_factory=list)
    player_of_the_match: BroadcastPlayerSpotlightView | None = None


class BroadcastSessionView(CommonSchema):
    match_id: str
    commentators: list[BroadcastCommentatorView] = Field(default_factory=list)
    overlay_state: BroadcastOverlayView
    headline_intro: str | None = None
    dual_commentary: list[DualCommentaryLineView] = Field(default_factory=list)
    halftime_analysis: BroadcastHalftimeSegmentView | None = None
    fulltime_wrap: BroadcastFulltimeWrapView | None = None
    rights_owner_id: str | None = None
    premium_features: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime | None = None


class FanEventView(CommonSchema):
    event_type: str
    title: str
    description: str
    intensity: int = Field(default=1, ge=1, le=5)


class FanReactionView(CommonSchema):
    club_id: str
    club_name: str
    sentiment: str
    expectation_level: str
    morale_delta: float
    manager_reputation_delta: float
    fan_count_delta: int
    pressure_score: float = Field(ge=0.0, le=100.0)
    events: list[FanEventView] = Field(default_factory=list)


class FanBaseView(CommonSchema):
    club_id: str
    fan_count: int = Field(ge=0)
    loyalty_score: float = Field(ge=0.0, le=100.0)
    expectation_level: str
    sentiment: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClubIdentityView(CommonSchema):
    club_id: str
    philosophy: str
    culture_score: float = Field(ge=0.0, le=100.0)
    tactical_consistency: float = Field(ge=0.0, le=100.0)
    brand_strength: float = Field(ge=0.0, le=100.0)
    chemistry_bonus: float = 0.0
    player_development_bonus: float = 0.0
    average_identity_fit: float = Field(default=0.0, ge=0.0, le=100.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaEventView(CommonSchema):
    id: str | None = None
    type: str
    content: str
    impact: dict[str, Any] = Field(default_factory=dict)
    match_id: str | None = None
    club_id: str | None = None
    created_at: datetime | None = None


class FootballUniverseNotificationView(CommonSchema):
    notification_type: str
    title: str
    message: str
    severity: str = "info"
    club_id: str | None = None
    match_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MediaFeedView(CommonSchema):
    items: list[MediaEventView] = Field(default_factory=list)


__all__ = [
    "BroadcastCommentatorView",
    "BroadcastFulltimeWrapView",
    "BroadcastHalftimeSegmentView",
    "BroadcastOverlayView",
    "BroadcastPlayerSpotlightView",
    "BroadcastScoreboardView",
    "BroadcastSessionView",
    "ClubIdentityView",
    "DualCommentaryLineView",
    "FanBaseView",
    "FanEventView",
    "FanReactionView",
    "FootballUniverseNotificationView",
    "MediaEventView",
    "MediaFeedView",
]
