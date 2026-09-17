from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


EditorialStatus = Literal["sourced", "enriched", "editorial_review", "approved", "blocked"]
RightsStatus = Literal["unknown", "pending", "approved", "rejected"]
CatalogueStatus = Literal["staged", "approved", "imported", "blocked"]


class Evidence(BaseModel):
    provider: str = Field(min_length=2)
    uri: str = Field(min_length=8)
    retrieved_at: datetime | None = None
    claim_types: list[str] = Field(default_factory=list)


class CatalogueRecord(BaseModel):
    source_id: str = Field(min_length=2, max_length=128)
    full_name: str = Field(min_length=1, max_length=160)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    date_of_birth: date | None = None
    historical_height_cm: int | None = Field(default=None, ge=120, le=230)
    position_candidates: list[str] = Field(default_factory=list)
    primary_position: str | None = None
    preferred_foot: Literal["left", "right", "both"] | None = None
    era: str | None = None
    signature_traits: list[str] = Field(default_factory=list)
    signature_role: str | None = None
    technical_profile: dict[str, Any] = Field(default_factory=dict)
    physical_profile: dict[str, Any] = Field(default_factory=dict)
    mental_profile: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[Evidence] = Field(default_factory=list)
    football_evidence: list[Evidence] = Field(default_factory=list)
    portrait_metadata: dict[str, Any] = Field(default_factory=dict)
    editorial_status: EditorialStatus = "sourced"
    rights_status: RightsStatus = "unknown"
    catalogue_status: CatalogueStatus = "staged"
    blocking_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class CatalogueBundle(BaseModel):
    schema_version: str = "legendary-catalogue-v1"
    generated_at: datetime
    source: str
    target_count: int = Field(default=2000, ge=1)
    records: list[CatalogueRecord]


class ReleaseGateResult(BaseModel):
    target_count: int = Field(default=2000, ge=1)
    eligible_count: int
    blocked_count: int
    duplicate_count: int
    ready: bool
    errors: list[str] = Field(default_factory=list)
