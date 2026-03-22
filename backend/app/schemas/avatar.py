from __future__ import annotations

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
