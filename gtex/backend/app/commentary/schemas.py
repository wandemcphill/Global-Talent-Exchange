from __future__ import annotations

from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class CommentatorProfileView(CommonSchema):
    id: str
    name: str
    style: str
    tone_intensity: float = Field(ge=0.0, le=1.0)
    summary: str | None = None
    catchphrases: list[str] = Field(default_factory=list)
    bias_rules: dict[str, Any] = Field(default_factory=dict)
    voice_config: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_active: bool = True


class CommentarySelectionRequest(CommonSchema):
    match_id: str | None = None
    primary_profile_id: str
    secondary_profile_id: str | None = None
    dual_mode: bool = False
    voice_enabled: bool = True
    language: str = "en"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CommentarySelectionView(CommonSchema):
    selection_key: str
    match_id: str | None = None
    primary_profile: CommentatorProfileView
    secondary_profile: CommentatorProfileView | None = None
    dual_mode: bool = False
    voice_enabled: bool = True
    language: str = "en"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CommentaryAudioPacketView(CommonSchema):
    key: str
    provider: str
    model_id: str
    output_format: str
    codec: str
    sample_rate_hz: int = Field(ge=1)
    channels: int = Field(ge=1)
    voice_id: str
    chunk_size: int = Field(ge=1)
    chunks_base64: list[str] = Field(default_factory=list)


class CommentaryVariantView(CommonSchema):
    profile_id: str
    profile_name: str
    style: str
    line: str
    tone: str
    commentator: str
    intensity: float = Field(ge=0.0, le=1.0)
    audio_channel: str
    voice_config: dict[str, Any] = Field(default_factory=dict)
    audio: CommentaryAudioPacketView | None = None


class CommentaryStreamEventView(CommonSchema):
    match_id: str
    event_id: str | None = None
    minute: int = Field(ge=0, le=120)
    event_type: str
    line: str
    base_line: str
    team: str | None = None
    player: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    cue: dict[str, Any] | None = None
    primary: CommentaryVariantView
    secondary: CommentaryVariantView | None = None


class CommentaryStreamResponse(CommonSchema):
    match_id: str
    status: str
    cursor: int = Field(ge=0)
    selection: CommentarySelectionView
    events: list[CommentaryStreamEventView] = Field(default_factory=list)
