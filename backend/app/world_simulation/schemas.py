from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FootballCultureView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    culture_key: str
    display_name: str
    scope_type: str
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    play_style_summary: str = ""
    supporter_traits_json: list[str] = Field(default_factory=list)
    rivalry_themes_json: list[str] = Field(default_factory=list)
    talent_archetypes_json: list[str] = Field(default_factory=list)
    climate_notes: str = ""
    active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class FootballCultureUpsertRequest(BaseModel):
    display_name: str
    scope_type: str = "archetype"
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    play_style_summary: str = ""
    supporter_traits_json: list[str] = Field(default_factory=list)
    rivalry_themes_json: list[str] = Field(default_factory=list)
    talent_archetypes_json: list[str] = Field(default_factory=list)
    climate_notes: str = ""
    active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubWorldProfileUpsertRequest(BaseModel):
    culture_key: str | None = None
    narrative_phase: str = "establishing_identity"
    supporter_mood: str = "hopeful"
    derby_heat_score: int = Field(default=0, ge=0, le=100)
    global_appeal_score: int = Field(default=0, ge=0, le=100)
    identity_keywords_json: list[str] = Field(default_factory=list)
    transfer_identity_tags_json: list[str] = Field(default_factory=list)
    fan_culture_tags_json: list[str] = Field(default_factory=list)
    world_flags_json: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorldNarrativeUpsertRequest(BaseModel):
    club_id: str | None = None
    competition_id: str | None = None
    arc_type: str
    status: str = "active"
    visibility: str = "public"
    headline: str
    summary: str = ""
    importance_score: int = Field(default=50, ge=0, le=100)
    simulation_horizon: str = "seasonal"
    start_at: datetime | None = None
    end_at: datetime | None = None
    tags_json: list[str] = Field(default_factory=list)
    impact_vectors_json: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WorldNarrativeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    scope_type: str
    club_id: str | None = None
    competition_id: str | None = None
    arc_type: str
    status: str
    visibility: str
    headline: str
    summary: str
    importance_score: int
    simulation_horizon: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    tags_json: list[str] = Field(default_factory=list)
    impact_vectors_json: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SimulationHookView(BaseModel):
    hook_key: str
    title: str
    target_scope: str
    horizon: str
    weight: int
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ClubWorldProfileSnapshotView(BaseModel):
    source: str
    culture_key: str | None = None
    narrative_phase: str
    supporter_mood: str
    derby_heat_score: int
    global_appeal_score: int
    identity_keywords: list[str] = Field(default_factory=list)
    transfer_identity_tags: list[str] = Field(default_factory=list)
    fan_culture_tags: list[str] = Field(default_factory=list)
    world_flags: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None


class ClubWorldContextView(BaseModel):
    club_id: str
    club_name: str
    short_name: str | None = None
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    reputation_score: int = 0
    prestige_tier: str | None = None
    culture: FootballCultureView | None = None
    world_profile: ClubWorldProfileSnapshotView
    active_narratives: list[WorldNarrativeView] = Field(default_factory=list)
    simulation_hooks: list[SimulationHookView] = Field(default_factory=list)


class CompetitionWorldContextView(BaseModel):
    competition_id: str
    name: str
    status: str
    format: str
    stage: str
    participant_count: int = 0
    active_narratives: list[WorldNarrativeView] = Field(default_factory=list)
    simulation_hooks: list[SimulationHookView] = Field(default_factory=list)
