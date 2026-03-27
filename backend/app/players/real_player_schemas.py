from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.player_match_learning import PlayerMatchEventType


class RealPlayerUniverseListItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    identity_rail: Literal["real_player_universe"]
    canonical_display_name: str | None
    real_player_tier: str | None
    nationality: str | None
    nationality_code: str | None
    position: str | None
    secondary_positions: tuple[str, ...] = ()
    age: int | None
    current_club_name: str | None
    current_league_name: str | None
    competition_level: str | None
    current_value_credits: float | None
    previous_value_credits: float | None
    movement_pct: float | None
    market_interest_score: int | None
    average_rating: float | None
    current_market_reference_value: float | None
    market_reference_currency: str | None
    source_name: str
    source_last_refreshed_at: datetime | None
    is_verified_real_player: bool
    updated_at: datetime


class RealPlayerUniverseListView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[RealPlayerUniverseListItemView]
    limit: int
    offset: int
    total: int


class RealPlayerUniversePageView(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    players: list[RealPlayerUniverseListItemView] = Field(
        validation_alias="items",
    )
    limit: int
    next_cursor: str | None = None
    has_more: bool
    total: int


class RealPlayerUniverseDetailView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    player_name: str
    identity_rail: Literal["real_player_universe"]
    canonical_display_name: str | None
    first_name: str | None
    last_name: str | None
    short_name: str | None
    nationality: str | None
    nationality_code: str | None
    position: str | None
    normalized_position: str | None
    primary_position: str | None
    secondary_positions: tuple[str, ...] = ()
    age: int | None
    date_of_birth: date | None
    dominant_foot: str | None
    height_cm: int | None
    weight_kg: int | None
    current_club_name: str | None
    current_league_name: str | None
    competition_level: str | None
    current_value_credits: float | None
    previous_value_credits: float | None
    movement_pct: float | None
    market_interest_score: int | None
    average_rating: float | None
    current_market_reference_value: float | None
    market_reference_currency: str | None
    appearances: int | None
    minutes_played: int | None
    goals: int | None
    assists: int | None
    clean_sheets: int | None
    injury_status: str | None
    real_player_tier: str | None
    identity_confidence_score: float | None
    source_name: str
    source_player_key: str
    source_last_refreshed_at: datetime | None
    is_verified_real_player: bool
    verification_state: str
    known_aliases: tuple[str, ...] = ()
    normalized_signals: dict[str, Any] = Field(default_factory=dict)
    ingestion_batch_id: str | None
    ingestion_source_version: str | None
    pricing_snapshot_id: str | None
    normalization_profile_version: str | None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    summary_json: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class RealPlayerMatchRangePreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)
    target: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "RealPlayerMatchRangePreference":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min cannot exceed max")
        if self.target is not None and self.min is not None and self.target < self.min:
            raise ValueError("target cannot be lower than min")
        if self.target is not None and self.max is not None and self.target > self.max:
            raise ValueError("target cannot be greater than max")
        return self


class RealPlayerMatchNumericPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "RealPlayerMatchNumericPreference":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min cannot exceed max")
        return self


class RealPlayerMatchBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positions: list[str] = Field(default_factory=list)
    age: RealPlayerMatchRangePreference = Field(default_factory=RealPlayerMatchRangePreference)
    height_cm: RealPlayerMatchRangePreference = Field(default_factory=RealPlayerMatchRangePreference)
    preferred_foot: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    availability: list[Literal["free_agent", "contract"]] = Field(default_factory=list)
    club_level: list[str] = Field(default_factory=list)
    experience_years: RealPlayerMatchNumericPreference = Field(default_factory=RealPlayerMatchNumericPreference)

    @field_validator("positions", "preferred_foot", "countries", "availability", "club_level", mode="before")
    @classmethod
    def coerce_list_fields(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if isinstance(value, (tuple, list, set, frozenset)):
            result: list[Any] = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned:
                        result.append(cleaned)
                    continue
                result.append(item)
            return result
        return [value]


class RealPlayerMatchWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: float = Field(default=0.40, ge=0)
    age: float = Field(default=0.20, ge=0)
    country: float = Field(default=0.10, ge=0)
    height: float = Field(default=0.10, ge=0)
    foot: float = Field(default=0.10, ge=0)
    availability: float = Field(default=0.10, ge=0)

    def normalized(self) -> dict[str, float]:
        raw = {
            "position": float(self.position),
            "age": float(self.age),
            "country": float(self.country),
            "height": float(self.height),
            "foot": float(self.foot),
            "availability": float(self.availability),
        }
        total = sum(raw.values())
        if total <= 0:
            raise ValueError("at least one weight must be greater than zero")
        return {key: value / total for key, value in raw.items()}


class RealPlayerMatchConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strict_position: bool = True
    exclude_injured: bool = False
    min_match_score: float = Field(default=0.55, ge=0, le=1)


class RealPlayerMatchPagination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class RealPlayerMatchSorting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: Literal["score"] = "score"
    order: Literal["desc"] = "desc"


class RealPlayerMatchContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scout_id: str | None = None
    club_id: str | None = None
    use_case: str | None = None


class RealPlayerMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: RealPlayerMatchBrief
    weights: RealPlayerMatchWeights = Field(default_factory=RealPlayerMatchWeights)
    constraints: RealPlayerMatchConstraints = Field(default_factory=RealPlayerMatchConstraints)
    pagination: RealPlayerMatchPagination = Field(default_factory=RealPlayerMatchPagination)
    sorting: RealPlayerMatchSorting = Field(default_factory=RealPlayerMatchSorting)
    context: RealPlayerMatchContext = Field(default_factory=RealPlayerMatchContext)
    debug: bool = False

    @model_validator(mode="before")
    @classmethod
    def upgrade_v1_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "brief" in value:
            return value
        filters = value.get("filters")
        if not isinstance(filters, dict):
            return value
        return {
            "brief": {
                "positions": [filters.get("position")] if filters.get("position") else [],
                "age": {
                    "min": filters.get("min_age"),
                    "max": filters.get("max_age"),
                },
                "height_cm": {
                    "min": filters.get("min_height") or filters.get("min_height_cm"),
                },
                "preferred_foot": [filters.get("preferred_foot") or filters.get("dominant_foot")]
                if (filters.get("preferred_foot") or filters.get("dominant_foot"))
                else [],
                "countries": [filters.get("country") or filters.get("nationality")]
                if (filters.get("country") or filters.get("nationality"))
                else [],
                "availability": [filters.get("availability")] if filters.get("availability") else [],
            },
            "pagination": {
                "limit": value.get("limit", 20),
            },
            "weights": dict(value.get("weights") or {}),
            "debug": bool(value.get("debug", False)),
        }

    @model_validator(mode="after")
    def validate_payload(self) -> "RealPlayerMatchRequest":
        if not self.brief.positions:
            raise ValueError("brief.positions must contain at least one position")
        self.weights.normalized()
        return self


class RealPlayerMatchScoreBreakdownView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: float
    age: float
    country: float
    height: float
    foot: float
    availability: float


class RealPlayerMatchReasonView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    label: str
    impact: str


class RealPlayerMatchFlagsView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_free_agent: bool
    is_exact_position: bool
    is_high_potential: bool


class RealPlayerMatchPlayerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    age: int | None
    position: str | None
    country: str | None
    height_cm: int | None
    preferred_foot: str | None
    club: str | None


class RealPlayerMatchView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    score: float
    score_breakdown: RealPlayerMatchScoreBreakdownView
    reasons: list[RealPlayerMatchReasonView] = Field(default_factory=list)
    flags: RealPlayerMatchFlagsView
    player: RealPlayerMatchPlayerView


class RealPlayerMatchMetaView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_candidates: int
    scored_candidates: int
    returned: int
    next_cursor: str | None = None
    has_more: bool


class RealPlayerMatchDistributionView(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    bucket_90_100: int = Field(validation_alias="90_100", serialization_alias="90_100")
    bucket_80_89: int = Field(validation_alias="80_89", serialization_alias="80_89")
    bucket_70_79: int = Field(validation_alias="70_79", serialization_alias="70_79")
    below_70: int


class RealPlayerMatchSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    average_score: float
    top_score: float
    distribution: RealPlayerMatchDistributionView


class RealPlayerMatchAppliedConfigView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weights: RealPlayerMatchWeights
    constraints: RealPlayerMatchConstraints


class RealPlayerMatchResponseView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    matches: list[RealPlayerMatchView]
    meta: RealPlayerMatchMetaView
    summary: RealPlayerMatchSummaryView
    applied_config: RealPlayerMatchAppliedConfigView
    debug: dict[str, Any] | None = None


class PlayerMatchEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    event: PlayerMatchEventType = Field(validation_alias=AliasChoices("event", "event_type"))
    filters: dict[str, Any] = Field(default_factory=dict)
    match_score: float | None = Field(default=None, ge=0)
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlayerMatchEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    player_id: str
    event: PlayerMatchEventType = Field(validation_alias="event_type")
    weight: int
    filters: dict[str, Any] = Field(default_factory=dict, validation_alias="filters_json")
    match_score: float | None = None
    reasons: list[str] = Field(default_factory=list, validation_alias="reasons_json")
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime


class PlayerMatchWeightView(BaseModel):
    factor: str
    weight: float


class PlayerMatchProfileView(BaseModel):
    total_signal: float
    signal_maturity: float
    event_count: int
    position_preferences: dict[str, float] = Field(default_factory=dict)
    country_preferences: dict[str, float] = Field(default_factory=dict)
    foot_preferences: dict[str, float] = Field(default_factory=dict)
    availability_preferences: dict[str, float] = Field(default_factory=dict)
    average_age: float | None = None
    average_height_cm: float | None = None
    weights: list[PlayerMatchWeightView] = Field(default_factory=list)
