from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LegendaryPlayerProfileBase(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128, description="Stable unique legendary profile identifier")
    full_name: str = Field(..., min_length=2, max_length=160, description="Full historical player name")
    country_code: str = Field(..., min_length=2, max_length=8, description="GTEX country alpha code")
    primary_position: str = Field(
        ..., min_length=1, max_length=40, description="Primary football position (e.g., ST, CAM, CB)"
    )
    secondary_positions: list[str] = Field(default_factory=list, description="List of secondary positions")
    preferred_foot: Literal["left", "right", "both"] = Field(default="right", description="Preferred foot")
    historical_height_cm: int = Field(..., ge=120, le=230, description="Historical height in centimeters")
    gtex_height_cm: int | None = Field(
        default=None, ge=119, le=231, description="Generated GTEX height (-1, 0, or +1 cm from historical height)"
    )
    signature_traits: list[str] = Field(default_factory=list, description="Signature football traits")
    signature_role: str | None = Field(default=None, max_length=80, description="Signature tendency / tactical role")
    technical_profile: dict[str, Any] = Field(default_factory=dict, description="Technical attribute profile")
    physical_profile: dict[str, Any] = Field(default_factory=dict, description="Physical attribute profile")
    mental_profile: dict[str, Any] = Field(default_factory=dict, description="Mental / decision tendency profile")
    era: str = Field(..., min_length=2, max_length=64, description="Historical era or period (e.g., 1970s, 1990-1998)")
    legendary_classification: str = Field(
        default="icon", min_length=2, max_length=40, description="Legendary classification (e.g., icon, immortal, hero)"
    )
    is_active: bool = Field(default=True)
    is_searchable: bool = Field(default=True)
    is_tradable: bool = Field(default=True)
    is_rentable: bool = Field(default=True)
    is_national_team_eligible: bool = Field(default=True)
    portrait_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Non-replicative portrait rendering configuration metadata"
    )
    source_notes: str | None = Field(default=None, description="Source / reference research notes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary extension metadata")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        clean = v.strip().lower()
        if not clean:
            raise ValueError("Slug cannot be empty")
        return clean

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("gtex_height_cm")
    @classmethod
    def validate_gtex_height(cls, v: int | None, info: Any) -> int | None:
        if v is None:
            return None
        hist = info.data.get("historical_height_cm")
        if hist is not None and v not in (hist - 1, hist, hist + 1):
            raise ValueError(
                f"gtex_height_cm ({v}) must be within exactly -1, 0, or +1 cm of historical_height_cm ({hist})"
            )
        return v


class LegendaryPlayerProfileCreate(LegendaryPlayerProfileBase):
    pass


class LegendaryPlayerProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    primary_position: str | None = Field(default=None, min_length=1, max_length=40)
    secondary_positions: list[str] | None = None
    preferred_foot: Literal["left", "right", "both"] | None = None
    historical_height_cm: int | None = Field(default=None, ge=120, le=230)
    gtex_height_cm: int | None = Field(default=None, ge=119, le=231)
    signature_traits: list[str] | None = None
    signature_role: str | None = None
    technical_profile: dict[str, Any] | None = None
    physical_profile: dict[str, Any] | None = None
    mental_profile: dict[str, Any] | None = None
    era: str | None = Field(default=None, min_length=2, max_length=64)
    legendary_classification: str | None = Field(default=None, min_length=2, max_length=40)
    is_active: bool | None = None
    is_searchable: bool | None = None
    is_tradable: bool | None = None
    is_rentable: bool | None = None
    is_national_team_eligible: bool | None = None
    portrait_metadata: dict[str, Any] | None = None
    source_notes: str | None = None
    metadata: dict[str, Any] | None = None


from pydantic import ConfigDict


class LegendaryPlayerProfileView(LegendaryPlayerProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    height_offset_cm: int = Field(..., description="Delta between GTEX height and historical height (-1, 0, +1)")


class LegendarySeedImportItem(LegendaryPlayerProfileBase):
    instantiate_gtex_player: bool = Field(
        default=True, description="Whether to instantiate an ordinary GTEX Player row immediately upon seed"
    )


class LegendarySeedImportRequest(BaseModel):
    profiles: list[LegendarySeedImportItem] = Field(..., min_length=1)
    instantiate_all: bool = Field(default=True)


class LegendarySeedImportResult(BaseModel):
    processed_count: int
    created_count: int
    updated_count: int
    instantiated_player_count: int
    profile_ids: list[str]
