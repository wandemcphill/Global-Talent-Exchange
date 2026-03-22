from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrendingPlayerFlagView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    event_id: str
    flag_type: str
    flag_label: str
    trend_score: float
    priority: int
    status: str
    started_at: datetime
    expires_at: datetime | None
    source: str
    metadata_json: dict


class PlayerFormModifierView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    event_id: str
    modifier_type: str
    modifier_label: str
    modifier_score: float
    gameplay_effect_value: float
    market_effect_value: float
    recommendation_effect_value: float
    visible_to_users: bool
    status: str
    started_at: datetime
    expires_at: datetime | None
    source: str
    metadata_json: dict


class PlayerDemandSignalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    event_id: str
    signal_type: str
    signal_label: str
    demand_score: float
    scouting_interest_delta: float
    recommendation_priority_delta: float
    market_buzz_score: float
    status: str
    started_at: datetime
    expires_at: datetime | None
    source: str
    metadata_json: dict


class PlayerRealWorldImpactView(BaseModel):
    player_id: str
    active_flags: list[TrendingPlayerFlagView]
    active_form_modifiers: list[PlayerFormModifierView]
    active_demand_signals: list[PlayerDemandSignalView]
    active_flag_codes: list[str]
    affected_card_ids: list[str]
    recommendation_priority_delta: float
    market_buzz_score: float
    gameplay_effect_total: float
    market_effect_total: float


class RealWorldFootballEventCreateRequest(BaseModel):
    event_type: str = Field(min_length=3)
    player_id: str = Field(min_length=3)
    occurred_at: datetime
    source_type: str = "manual"
    source_label: str = "admin_manual"
    external_event_id: str | None = None
    title: str | None = None
    summary: str | None = None
    severity: float = Field(default=1.0, ge=0.0, le=3.0)
    current_club_id: str | None = None
    competition_id: str | None = None
    requires_admin_review: bool | None = None
    metadata: dict = Field(default_factory=dict)
    raw_payload: dict = Field(default_factory=dict)


class EventFeedIngestionRequestModel(BaseModel):
    source_label: str = Field(min_length=1)
    source_type: str = "import_feed"
    events: list[RealWorldFootballEventCreateRequest] = Field(default_factory=list)


class EventReviewRequest(BaseModel):
    approve: bool
    notes: str | None = None


class EventSeverityOverrideRequest(BaseModel):
    severity: float | None = Field(default=None, ge=0.0, le=3.0)


class EventCategoryToggleRequest(BaseModel):
    event_type: str = Field(min_length=3)
    is_enabled: bool


class EventEffectRuleUpsertRequest(BaseModel):
    event_type: str = Field(min_length=3)
    effect_type: str = Field(min_length=3)
    effect_code: str = Field(min_length=2)
    label: str = Field(min_length=2)
    is_enabled: bool = True
    approval_required: bool = False
    base_magnitude: float = 0.0
    duration_hours: int = Field(default=0, ge=0)
    priority: int = 0
    gameplay_enabled: bool = False
    market_enabled: bool = False
    recommendation_enabled: bool = False
    config: dict = Field(default_factory=dict)


class ExpireEffectsRequest(BaseModel):
    as_of: datetime | None = None


class EventEffectRuleView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    effect_type: str
    effect_code: str
    label: str
    is_enabled: bool
    approval_required: bool
    base_magnitude: float
    duration_hours: int
    priority: int
    gameplay_enabled: bool
    market_enabled: bool
    recommendation_enabled: bool
    config_json: dict
    created_at: datetime
    updated_at: datetime


class RealWorldFootballEventView(BaseModel):
    id: str
    ingestion_job_id: str | None
    player_id: str
    current_club_id: str | None
    competition_id: str | None
    event_type: str
    source_type: str
    source_label: str
    external_event_id: str | None
    approval_status: str
    requires_admin_review: bool
    title: str
    summary: str | None
    severity: float
    effect_severity_override: float | None
    occurred_at: datetime
    approved_by_user_id: str | None
    approved_at: datetime | None
    rejected_by_user_id: str | None
    rejected_at: datetime | None
    review_notes: str | None
    effects_applied_at: datetime | None
    metadata_json: dict
    normalized_payload_json: dict
    story_feed_item_id: str | None
    calendar_event_id: str | None
    affected_card_ids: list[str]
    active_flag_count: int
    active_modifier_count: int
    active_demand_signal_count: int
    created_at: datetime
    updated_at: datetime


class EventIngestionJobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: str
    source_label: str
    status: str
    submitted_by_user_id: str | None
    started_at: datetime
    completed_at: datetime | None
    total_received: int
    processed_count: int
    success_count: int
    failed_count: int
    pending_review_count: int
    error_message: str | None
    summary_json: dict
    created_at: datetime
    updated_at: datetime
