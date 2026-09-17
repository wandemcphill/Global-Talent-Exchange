from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LegendaryPlayerProfileBase(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128, description="Stable unique legendary profile identifier")
    full_name: str = Field(..., min_length=1, max_length=160, description="Full historical player name")
    country_code: str = Field(..., min_length=2, max_length=8, description="GTEX country alpha code")
    date_of_birth: date | None = None
    primary_position: str = Field(..., min_length=1, max_length=40)
    secondary_positions: list[str] = Field(default_factory=list)
    preferred_foot: Literal["left", "right", "both"] = "right"
    historical_height_cm: int = Field(..., ge=120, le=230)
    gtex_height_cm: int | None = Field(default=None, ge=119, le=231)
    signature_traits: list[str] = Field(default_factory=list)
    signature_role: str | None = Field(default=None, max_length=80)
    technical_profile: dict[str, Any] = Field(default_factory=dict)
    physical_profile: dict[str, Any] = Field(default_factory=dict)
    mental_profile: dict[str, Any] = Field(default_factory=dict)
    era: str = Field(..., min_length=2, max_length=64)
    legendary_classification: str = Field(default="icon", min_length=2, max_length=40)
    is_active: bool = True
    is_searchable: bool = True
    is_tradable: bool = True
    is_rentable: bool = True
    is_national_team_eligible: bool = True
    portrait_metadata: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    football_evidence: list[dict[str, Any]] = Field(default_factory=list)
    editorial_status: Literal["sourced", "enriched", "editorial_review", "approved", "blocked"] = "sourced"
    rights_status: Literal["unknown", "pending", "approved", "rejected"] = "unknown"
    catalogue_status: Literal["staged", "approved", "imported", "blocked"] = "staged"
    source_notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

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
            raise ValueError("gtex_height_cm must be historical height +/- 1 cm")
        return v


class LegendaryPlayerProfileCreate(LegendaryPlayerProfileBase):
    pass


class LegendaryPlayerProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    date_of_birth: date | None = None
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
    era: str | None = None
    legendary_classification: str | None = None
    is_active: bool | None = None
    is_searchable: bool | None = None
    is_tradable: bool | None = None
    is_rentable: bool | None = None
    is_national_team_eligible: bool | None = None
    portrait_metadata: dict[str, Any] | None = None
    source_evidence: list[dict[str, Any]] | None = None
    football_evidence: list[dict[str, Any]] | None = None
    editorial_status: Literal["sourced", "enriched", "editorial_review", "approved", "blocked"] | None = None
    rights_status: Literal["unknown", "pending", "approved", "rejected"] | None = None
    catalogue_status: Literal["staged", "approved", "imported", "blocked"] | None = None
    source_notes: str | None = None
    metadata: dict[str, Any] | None = None


class LegendaryPlayerProfileView(LegendaryPlayerProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    height_offset_cm: int


class LegendarySeedImportItem(LegendaryPlayerProfileBase):
    instantiate_gtex_player: bool = True


class LegendarySeedImportRequest(BaseModel):
    profiles: list[LegendarySeedImportItem] = Field(..., min_length=1)
    instantiate_all: bool = True


class LegendarySeedImportResult(BaseModel):
    processed_count: int
    created_count: int
    updated_count: int
    instantiated_player_count: int
    profile_ids: list[str]
