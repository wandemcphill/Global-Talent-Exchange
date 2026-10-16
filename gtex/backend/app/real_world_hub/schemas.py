from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.real_world_hub import RealityMode
from app.schemas.real_player_ingestion import RealPlayerSeedInput


class RealCompetitionSeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_key: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    country_name: str | None = Field(default=None, max_length=120)
    competition_type: str = Field(default="league", min_length=1, max_length=32)
    gtex_competition_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RealClubSeedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_key: str = Field(min_length=1, max_length=128)
    competition_external_key: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    country_name: str | None = Field(default=None, max_length=120)
    gtex_club_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RealDataProviderUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    api_endpoint: str = Field(min_length=1, max_length=255)
    refresh_interval: int = Field(default=3600, ge=60, le=604800)
    normalization_profile_version: str = Field(default="real_player_v1", min_length=1, max_length=32)
    is_active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RealWorldSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competitions: list[RealCompetitionSeedRequest] = Field(default_factory=list)
    clubs: list[RealClubSeedRequest] = Field(default_factory=list)
    players: list[RealPlayerSeedInput] = Field(default_factory=list)
    use_existing_profiles: bool = False
    as_of: datetime | None = None


class RealityModeSettingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: RealityMode = RealityMode.HYBRID
    enable_real_world_events: bool = False
    enable_soft_injuries: bool = True
    enable_transfer_mirror: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class StatsNormalizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player: RealPlayerSeedInput


class RealDataProviderView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    api_endpoint: str
    refresh_interval: int
    normalization_profile_version: str
    is_active: bool
    last_sync_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RealDataSyncJobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    entities_seen: int
    entities_upserted: int
    entities_failed: int
    error_message: str | None
    summary_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RealPlayerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    external_key: str
    gtex_player_id: str | None
    real_club_id: str | None
    real_competition_id: str | None
    name: str
    nationality: str | None
    position: str | None
    player_origin: str
    real_world_rating: float
    normalized_rating: float
    attributes_json: dict[str, Any]
    injury_status: str | None
    soft_injury_impact: float
    metadata_json: dict[str, Any]
    last_updated: datetime
    created_at: datetime
    updated_at: datetime


class RealityModeSettingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    mode: RealityMode
    enable_real_world_events: bool
    enable_soft_injuries: bool
    enable_transfer_mirror: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class HybridPlayerView(BaseModel):
    player_id: str
    name: str
    player_origin: str
    nationality: str | None = None
    position: str | None = None
    source_provider: str | None = None
    real_world_rating: float | None = None
    normalized_rating: float | None = None
    mode: RealityMode
    eligible: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class StatsNormalizationView(BaseModel):
    source_name: str
    source_player_key: str
    normalization_profile_version: str
    real_world_rating: float
    normalized_rating: float
    attributes_json: dict[str, float]
    injury_status: str | None = None
    soft_injury_impact: float = 0.0


class RealWorldRevenueImpactView(BaseModel):
    federation_share_bps: int
    gross_amount: Decimal
    projected_federation_share: Decimal
    projected_club_distribution: list[dict[str, Any]] = Field(default_factory=list)
