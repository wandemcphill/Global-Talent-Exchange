from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlayerAvatarView(BaseModel):
    avatar_version: int = Field(default=1, ge=1)
    version: str = Field(default="fm_v1")
    seed_token: str = Field(min_length=1)
    dna_seed: int = Field(ge=0)
    skin_tone: int = Field(ge=0, le=5)
    hair_style: int = Field(ge=0, le=8)
    hair_color: int = Field(ge=0, le=5)
    face_shape: int = Field(ge=0, le=4)
    eyebrow_style: int = Field(ge=0, le=3)
    eye_type: int = Field(ge=0, le=3)
    nose_type: int = Field(ge=0, le=3)
    mouth_type: int = Field(ge=0, le=3)
    beard_style: int = Field(ge=0, le=5)
    has_accessory: bool = False
    accessory_type: int = Field(ge=0, le=3)
    jersey_style: int = Field(ge=0, le=3)
    accent_tone: int = Field(ge=0, le=5)


class PlayerFaceView(BaseModel):
    player_id: str = Field(min_length=1)
    avatar_seed: str = Field(min_length=8)
    facial_features: dict[str, Any] = Field(default_factory=dict)
    hairstyle: str | None = None
    skin_tone: str | None = None
    accessories: list[str] = Field(default_factory=list)
    generated_at: datetime
    nationality: str | None = None
    region_preset: str | None = None
    age_stage: str = Field(min_length=3)
    rarity: str = Field(default="standard", min_length=3)
    visual_effects: list[str] = Field(default_factory=list)


class PlayerAvatarRenderView(BaseModel):
    player_id: str = Field(min_length=1)
    render_format: Literal["json", "svg", "static", "model"] = "json"
    face: PlayerFaceView
    legacy_avatar: PlayerAvatarView
    layered_svg: str | None = None
    static_image_data_uri: str | None = None
    model_manifest: dict[str, Any] | None = None
    capabilities: list[str] = Field(
        default_factory=lambda: ["static_image", "layered_svg", "future_3d_model"]
    )
