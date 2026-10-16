from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.live_matches.schemas import SpectatorSessionView


class BroadcastProgramSlotView(CommonSchema):
    slot_id: str
    channel_id: str
    match_id: str | None = None
    title: str
    subtitle: str = ""
    program_type: str = "live_match"
    start_at: datetime
    end_at: datetime
    score: float = Field(default=0.0, ge=0.0)
    is_live: bool = False
    watch_route: str | None = None
    replay_route: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BroadcastChannelView(CommonSchema):
    channel_id: str
    name: str
    channel_type: str
    description: str = ""
    is_live: bool = False
    auto_switch_enabled: bool = True
    viewer_count: int = Field(default=0, ge=0)
    featured_match_id: str | None = None
    current_program: BroadcastProgramSlotView | None = None
    upcoming_programs: list[BroadcastProgramSlotView] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BroadcastDirectorFocusView(CommonSchema):
    match_id: str
    score: float = Field(default=0.0, ge=0.0)
    viewer_count: int = Field(default=0, ge=0)
    goals: int = Field(default=0, ge=0)
    match_stage: float = Field(default=0.0, ge=0.0)
    rivalry: float = Field(default=0.0, ge=0.0, le=1.0)
    upset_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    recent_moment_velocity: float = Field(default=0.0, ge=0.0)
    momentum: str = "balanced"
    focus_target: str = "midfield"
    focus_reason: str = "match_state"
    metadata: dict[str, Any] = Field(default_factory=dict)


class BroadcastAudioStemFrameView(CommonSchema):
    frame_id: str
    channel_id: str | None = None
    match_id: str
    stem_type: str
    source_event_id: str | None = None
    sequence_id: int | None = Field(default=None, ge=1)
    presentation_second: int = Field(ge=0)
    offset_ms: int = Field(default=0, ge=0)
    intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    cue_text: str | None = None
    speaker_role: str | None = None
    voice_profile: str | None = None
    voice_id: str | None = None
    accent: str | None = None
    speech_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    interrupt_priority: int = Field(default=0, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BroadcastAudioManifestView(CommonSchema):
    channel_id: str | None = None
    match_id: str | None = None
    stems: list[str] = Field(default_factory=lambda: ["commentary", "crowd", "stadium_fx"])
    primary_voice_profile: str | None = None
    secondary_voice_profile: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BroadcastWatchRewardView(CommonSchema):
    session_id: str
    channel_id: str
    watched_seconds: float = Field(default=0.0, ge=0.0)
    switch_count: int = Field(default=0, ge=0)
    rewarded: bool = False
    xp_awarded: int = Field(default=0, ge=0)
    reward_value_coin: Decimal = Decimal("0.0000")
    finalized_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelSessionView(CommonSchema):
    session_id: str
    channel: BroadcastChannelView
    current_program: BroadcastProgramSlotView | None = None
    upcoming_programs: list[BroadcastProgramSlotView] = Field(default_factory=list)
    director_focus: BroadcastDirectorFocusView | None = None
    match_session: SpectatorSessionView | None = None
    fallback_replay_route: str | None = None
    websocket_path: str
    audio_stem_websocket_path: str | None = None
    watch_reward: BroadcastWatchRewardView
    joined_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class BroadcastHomeView(CommonSchema):
    channels: list[BroadcastChannelView] = Field(default_factory=list)
    featured_channel: BroadcastChannelView | None = None
    match_of_the_moment: BroadcastProgramSlotView | None = None
    highest_engagement_match: BroadcastDirectorFocusView | None = None
    generated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "BroadcastAudioManifestView",
    "BroadcastAudioStemFrameView",
    "BroadcastChannelView",
    "BroadcastDirectorFocusView",
    "BroadcastHomeView",
    "BroadcastProgramSlotView",
    "BroadcastWatchRewardView",
    "ChannelSessionView",
]
