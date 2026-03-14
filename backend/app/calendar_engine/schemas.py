from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CalendarSeasonCreateRequest(BaseModel):
    season_key: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=3, max_length=160)
    starts_on: date
    ends_on: date
    status: str = Field(default="draft", max_length=32)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CalendarSeasonView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    season_key: str
    title: str
    starts_on: date
    ends_on: date
    status: str
    metadata_json: dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: datetime


class CalendarEventCreateRequest(BaseModel):
    season_id: str | None = None
    event_key: str = Field(min_length=3, max_length=120)
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    source_type: str = Field(default="manual", max_length=48)
    source_id: str | None = Field(default=None, max_length=36)
    family: str = Field(default="general", max_length=48)
    age_band: str = Field(default="senior", max_length=16)
    starts_on: date
    ends_on: date
    exclusive_windows: bool = False
    pause_other_gtx_competitions: bool = False
    visibility: str = Field(default="public", max_length=32)
    status: str = Field(default="scheduled", max_length=32)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CalendarEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    season_id: str | None
    event_key: str
    title: str
    description: str | None
    source_type: str
    source_id: str | None
    family: str
    age_band: str
    starts_on: date
    ends_on: date
    exclusive_windows: bool
    pause_other_gtx_competitions: bool
    visibility: str
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CompetitionLifecycleRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str | None
    source_type: str
    source_id: str
    source_title: str
    competition_format: str
    status: str
    stage: str
    generated_rounds: int
    generated_matches: int
    scheduled_dates_json: list[str]
    summary_text: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class HostedCompetitionLaunchRequest(BaseModel):
    starts_on: date | None = None
    override_title: str | None = Field(default=None, max_length=200)
    preferred_family: str = Field(default="hosted", max_length=48)


class NationalCompetitionLaunchRequest(BaseModel):
    starts_on: date | None = None
    override_title: str | None = Field(default=None, max_length=200)
    exclusive_windows: bool | None = None
    pause_other_gtx_competitions: bool | None = None


class PauseStatusView(BaseModel):
    as_of: date
    blocked_competition_families: list[str]
    active_event_keys: list[str]
    summary: str


class CalendarDashboardView(BaseModel):
    seasons: list[CalendarSeasonView]
    active_events: list[CalendarEventView]
    active_pause_status: PauseStatusView
    recent_lifecycle_runs: list[CompetitionLifecycleRunView]
