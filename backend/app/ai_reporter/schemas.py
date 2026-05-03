from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AIReporterRunRequest(BaseModel):
    beats: list[str] = Field(default_factory=list)
    limit_per_beat: int = Field(default=3, ge=1, le=10)
    dry_run: bool = False

    @field_validator("beats")
    @classmethod
    def normalize_beats(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item and item.strip()]


class AIReporterStoryView(BaseModel):
    id: str | None = None
    story_type: str
    audience: str = "public"
    title: str
    body: str
    subject_type: str | None = None
    subject_id: str | None = None
    country_code: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    featured: bool = False
    created_at: datetime | None = None


class AIReporterRunResponse(BaseModel):
    reporter_name: str
    ai_provider: str
    cost_tier: str
    generated_count: int
    skipped_duplicate_count: int
    dry_run: bool
    items: list[AIReporterStoryView]

