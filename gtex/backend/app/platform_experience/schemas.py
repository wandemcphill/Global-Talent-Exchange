from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.broadcast_network.schemas import BroadcastChannelView, BroadcastProgramSlotView
from app.common.schemas.base import CommonSchema


PlatformModeLiteral = Literal["mobile", "web", "tv"]


class PlatformWatchHistoryEntryView(CommonSchema):
    watched_at: datetime
    mode: PlatformModeLiteral
    device_id: str
    device_name: str | None = None
    match_id: str | None = None
    channel_id: str | None = None
    title: str | None = None
    resume_position_seconds: float = Field(default=0.0, ge=0.0)
    commentary_cursor: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformSyncStateView(CommonSchema):
    source_device_id: str | None = None
    source_device_name: str | None = None
    resume_match_id: str | None = None
    resume_channel_id: str | None = None
    resume_position_seconds: float = Field(default=0.0, ge=0.0)
    commentary_cursor: int = Field(default=0, ge=0)
    watch_history: list[PlatformWatchHistoryEntryView] = Field(default_factory=list)
    last_synced_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformModeView(CommonSchema):
    mode: PlatformModeLiteral
    device_id: str | None = None
    device_name: str | None = None
    available_modes: list[PlatformModeLiteral] = Field(default_factory=lambda: ["mobile", "web", "tv"])
    features: dict[str, bool] = Field(default_factory=dict)
    sync_state: PlatformSyncStateView
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformSwitchRequest(CommonSchema):
    mode: PlatformModeLiteral
    device_id: str
    device_name: str | None = None
    current_match_id: str | None = None
    current_channel_id: str | None = None
    resume_position_seconds: float = Field(default=0.0, ge=0.0)
    commentary_cursor: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformHighlightReelView(CommonSchema):
    reel_id: str
    title: str
    channel_id: str
    match_id: str | None = None
    replay_route: str | None = None
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformBroadcastGuideView(CommonSchema):
    what_is_live_now: BroadcastProgramSlotView | None = None
    featured_channel: BroadcastChannelView | None = None
    channels: list[BroadcastChannelView] = Field(default_factory=list)
    highlight_reels: list[PlatformHighlightReelView] = Field(default_factory=list)
    auto_switch_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "PlatformBroadcastGuideView",
    "PlatformHighlightReelView",
    "PlatformModeLiteral",
    "PlatformModeView",
    "PlatformSwitchRequest",
    "PlatformSyncStateView",
    "PlatformWatchHistoryEntryView",
]
