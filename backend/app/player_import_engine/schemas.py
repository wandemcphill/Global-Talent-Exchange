from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerImportRowRequest(BaseModel):
    external_source_id: str | None = None
    full_name: str = Field(min_length=2)
    position: str = Field(min_length=1)
    nationality_code: str = Field(min_length=2, max_length=12)
    age: int | None = Field(default=None, ge=13, le=45)
    club_id: str | None = None
    market_value_eur: float | None = Field(default=None, ge=0)


class PlayerImportJobCreateRequest(BaseModel):
    source_type: str = Field(min_length=2)
    source_label: str = Field(min_length=2)
    commit: bool = True
    rows: list[PlayerImportRowRequest] = Field(default_factory=list, min_length=1, max_length=500)


class PlayerCardSupplyRowRequest(BaseModel):
    player_id: str | None = None
    player_name: str | None = None
    tier_code: str = Field(min_length=2, max_length=32)
    quantity: int = Field(default=1, ge=1)
    edition_code: str = Field(default="base", min_length=2, max_length=64)
    season_label: str | None = None
    owner_user_id: str | None = None
    batch_key: str | None = None
    source_reference: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class PlayerCardSupplyJobCreateRequest(BaseModel):
    source_label: str = Field(min_length=2)
    commit: bool = True
    rows: list[PlayerCardSupplyRowRequest] = Field(default_factory=list, min_length=1, max_length=2000)


class YouthGenerationRequest(BaseModel):
    club_id: str | None = None
    count: int = Field(default=12, ge=1, le=100)
    nationality_code: str = Field(default='NG', min_length=2, max_length=12)
    region_label: str = Field(default='Local Academy', min_length=2, max_length=120)


class PlayerImportItemView(BaseModel):
    id: str
    row_number: int
    external_source_id: str | None
    player_name: str | None
    normalized_position: str | None
    nationality_code: str | None
    age: int | None
    status: str
    validation_errors_json: list[str]
    payload_json: dict[str, object]
    linked_player_id: str | None


class PlayerImportJobView(BaseModel):
    id: str
    created_by_user_id: str | None
    source_type: str
    source_label: str
    status: str
    total_items: int
    valid_items: int
    imported_items: int
    failed_items: int
    notes: str | None
    metadata_json: dict[str, object]
    items: list[PlayerImportItemView] = []


class YouthProspectView(BaseModel):
    id: str
    club_id: str
    display_name: str
    age: int
    nationality_code: str
    region_label: str
    primary_position: str
    secondary_position: str | None
    rating_band: str
    development_traits_json: list[str]
    pathway_stage: str
    scouting_source: str
    follow_priority: int


class YouthGenerationResponse(BaseModel):
    job: PlayerImportJobView
    generated_prospects: list[YouthProspectView]
    summary: str
