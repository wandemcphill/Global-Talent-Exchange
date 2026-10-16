"""Request/response contracts for the Talent Exchange API.

Search filters are validated *here* as well as in the service. The API layer is
where an unbounded query becomes an expensive one, so every list filter has a
length ceiling, every text filter has a length floor and ceiling, and the page
window is capped so no caller can ask the database to skip a million rows.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.talent.constants import (
    COMPARE_MAX_TALENTS,
    POSITION_CODE_SET,
    PREFERRED_FOOT_VALUES,
    SEARCH_DEFAULT_PAGE_SIZE,
    SEARCH_MAX_FILTER_VALUES,
    SEARCH_MAX_PAGE_SIZE,
    SEARCH_MAX_RESULT_WINDOW,
    SEARCH_MAX_TEXT_LENGTH,
    SEARCH_MIN_TEXT_LENGTH,
    TACTICAL_ROLE_SET,
    AvailabilityStatus,
    ModerationAction,
    ModerationState,
    ShortlistEntryStatus,
    VerificationDecision,
    VerificationTier,
    VisibilityState,
)


def _upper_unique(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    return sorted({value.strip().upper() for value in values if value and value.strip()})


def _lower_unique(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    return sorted({value.strip().lower() for value in values if value and value.strip()})


class TalentSearchRequest(BaseModel):
    """Bounded discovery query.

    Defaults are deliberately narrow: an empty request returns the first page
    of published talent ranked by composite score, not the whole table.
    """

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(
        default=None,
        min_length=SEARCH_MIN_TEXT_LENGTH,
        max_length=SEARCH_MAX_TEXT_LENGTH,
        description="Name prefix/substring match. Bounded in length to keep the scan cheap.",
    )
    positions: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    preferred_positions: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    tactical_roles: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    preferred_foot: Literal["left", "right", "both"] | None = None
    min_age: int | None = Field(default=None, ge=14, le=60)
    max_age: int | None = Field(default=None, ge=14, le=60)
    nationality_codes: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    location_country_codes: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    location_region: str | None = Field(default=None, max_length=120)
    availability: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    min_verification_tier: VerificationTier | None = None
    min_composite_score: float | None = Field(default=None, ge=0.0, le=100.0)
    max_composite_score: float | None = Field(default=None, ge=0.0, le=100.0)
    min_form_score: float | None = Field(default=None, ge=0.0, le=100.0)
    min_competition_level_score: float | None = Field(default=None, ge=0.0, le=100.0)
    min_experience_years: float | None = Field(default=None, ge=0.0, le=30.0)
    min_ranking_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    min_sample_size: int | None = Field(default=None, ge=0, le=1000)
    required_signals: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    featured_only: bool = False
    sort: Literal[
        "ranking",
        "form",
        "age_asc",
        "age_desc",
        "competition_level",
        "recently_updated",
        "name",
    ] = "ranking"
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=SEARCH_DEFAULT_PAGE_SIZE, ge=1, le=SEARCH_MAX_PAGE_SIZE)

    @field_validator("positions", "preferred_positions", mode="after")
    @classmethod
    def _validate_positions(cls, value: list[str] | None) -> list[str] | None:
        codes = _upper_unique(value)
        if codes is None:
            return None
        unknown = [code for code in codes if code not in POSITION_CODE_SET]
        if unknown:
            raise ValueError(f"Unknown position code(s): {', '.join(unknown)}")
        return codes

    @field_validator("tactical_roles", mode="after")
    @classmethod
    def _validate_roles(cls, value: list[str] | None) -> list[str] | None:
        roles = _lower_unique(value)
        if roles is None:
            return None
        unknown = [role for role in roles if role not in TACTICAL_ROLE_SET]
        if unknown:
            raise ValueError(f"Unknown tactical role(s): {', '.join(unknown)}")
        return roles

    @field_validator("availability", mode="after")
    @classmethod
    def _validate_availability(cls, value: list[str] | None) -> list[str] | None:
        statuses = _lower_unique(value)
        if statuses is None:
            return None
        allowed = {member.value for member in AvailabilityStatus}
        unknown = [status for status in statuses if status not in allowed]
        if unknown:
            raise ValueError(f"Unknown availability status(es): {', '.join(unknown)}")
        return statuses

    @field_validator("nationality_codes", "location_country_codes", mode="after")
    @classmethod
    def _validate_country_codes(cls, value: list[str] | None) -> list[str] | None:
        codes = _upper_unique(value)
        if codes is None:
            return None
        if any(len(code) > 8 for code in codes):
            raise ValueError("Country codes must be 8 characters or fewer.")
        return codes

    @field_validator("required_signals", mode="after")
    @classmethod
    def _validate_signals(cls, value: list[str] | None) -> list[str] | None:
        return _lower_unique(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "TalentSearchRequest":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age cannot exceed max_age.")
        if (
            self.min_composite_score is not None
            and self.max_composite_score is not None
            and self.min_composite_score > self.max_composite_score
        ):
            raise ValueError("min_composite_score cannot exceed max_composite_score.")
        if self.page * self.per_page > SEARCH_MAX_RESULT_WINDOW:
            raise ValueError(
                "Result window exceeded: page * per_page must not exceed "
                f"{SEARCH_MAX_RESULT_WINDOW}. Narrow the filters instead of paging deeper."
            )
        return self


class TalentSearchPagination(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class TalentSearchResponse(BaseModel):
    items: list[dict[str, Any]]
    pagination: TalentSearchPagination
    sort: str
    viewer_scope: str
    applied_filters: dict[str, Any]


class TalentProfileResponse(BaseModel):
    profile: dict[str, Any]


class TalentRankingResponse(BaseModel):
    player_id: str
    as_of: str
    config_version: str
    composite_score: float
    base_score: float
    adjustments_total: float
    confidence: float
    sample_size: int
    components: list[dict[str, Any]]
    adjustments: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    inputs_digest: str


class TalentSignalsResponse(BaseModel):
    player_id: str
    as_of: str | None
    config_version: str
    signals: list[dict[str, Any]]


class TalentCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_ids: list[str] = Field(min_length=2, max_length=COMPARE_MAX_TALENTS)

    @field_validator("player_ids", mode="after")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(set(cleaned)) < 2:
            raise ValueError("Provide at least two distinct player ids to compare.")
        return cleaned


class TalentCompareResponse(BaseModel):
    talents: list[dict[str, Any]]
    component_matrix: list[dict[str, Any]]
    viewer_scope: str
    missing_player_ids: list[str] = Field(default_factory=list)


class ShortlistCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    club_id: str | None = Field(default=None, max_length=36)


class ShortlistUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=400)
    is_archived: bool | None = None


class ShortlistEntryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str = Field(min_length=1, max_length=36)
    status: ShortlistEntryStatus = ShortlistEntryStatus.WATCHING
    priority: int = Field(default=0, ge=0, le=100)
    note: str | None = Field(default=None, max_length=2000)


class ShortlistEntryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ShortlistEntryStatus | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=2000)


class ShortlistEntryView(BaseModel):
    id: str
    player_id: str
    status: str
    priority: int
    note: str | None = None
    score_at_add: float | None = None
    added_at: str
    talent: dict[str, Any] | None = None


class ShortlistView(BaseModel):
    id: str
    name: str
    description: str | None = None
    club_id: str | None = None
    is_archived: bool
    entry_count: int
    entries: list[ShortlistEntryView] = Field(default_factory=list)


class ShortlistListResponse(BaseModel):
    shortlists: list[ShortlistView]


# --- admin -------------------------------------------------------------


class TalentVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: VerificationTier
    decision: VerificationDecision = VerificationDecision.GRANTED
    evidence_kind: str | None = Field(default=None, max_length=64)
    evidence_reference: str | None = Field(
        default=None,
        max_length=120,
        description=(
            "Opaque internal pointer such as a review ticket id. Never a document, "
            "identifier or any other personal data."
        ),
    )
    expires_at: date | None = None
    reviewer_notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_tier(self) -> "TalentVerificationRequest":
        if self.decision is VerificationDecision.GRANTED and self.tier is VerificationTier.UNVERIFIED:
            raise ValueError("Granting the 'unverified' tier is meaningless; revoke instead.")
        return self


class TalentVisibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visibility_state: VisibilityState
    reason: str | None = Field(default=None, max_length=400)


class TalentModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ModerationAction
    moderation_state: ModerationState | None = None
    reason: str | None = Field(default=None, max_length=400)
    internal_notes: str | None = Field(default=None, max_length=4000)


class TalentFeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_featured: bool
    featured_rank: int | None = Field(default=None, ge=0, le=10000)
    reason: str | None = Field(default=None, max_length=400)


class TalentCorrectionRequest(BaseModel):
    """Admin correction of factual profile fields.

    Scores are absent by design: an admin corrects *facts*, and the ranking
    pipeline recomputes from corrected facts. Hand-editing a score would make
    the ranking indefensible.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=4000)
    position_code: str | None = Field(default=None, max_length=8)
    secondary_positions: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    tactical_roles: list[str] | None = Field(default=None, max_length=SEARCH_MAX_FILTER_VALUES)
    preferred_foot: str | None = Field(default=None, max_length=8)
    date_of_birth: date | None = None
    nationality_code: str | None = Field(default=None, max_length=8)
    nationality_name: str | None = Field(default=None, max_length=96)
    location_country_code: str | None = Field(default=None, max_length=8)
    location_region: str | None = Field(default=None, max_length=120)
    location_city: str | None = Field(default=None, max_length=120)
    height_cm: int | None = Field(default=None, ge=120, le=230)
    weight_kg: int | None = Field(default=None, ge=35, le=160)
    availability_status: AvailabilityStatus | None = None
    availability_note: str | None = Field(default=None, max_length=240)
    available_from: date | None = None
    experience_years: float | None = Field(default=None, ge=0.0, le=30.0)
    technical_attributes: dict[str, float] | None = None
    tactical_attributes: dict[str, float] | None = None
    physical_attributes: dict[str, float] | None = None
    reason: str | None = Field(default=None, max_length=400)

    @field_validator("position_code", mode="after")
    @classmethod
    def _validate_position(cls, value: str | None) -> str | None:
        if value is None:
            return None
        code = value.strip().upper()
        if code not in POSITION_CODE_SET:
            raise ValueError(f"Unknown position code: {code}")
        return code

    @field_validator("secondary_positions", mode="after")
    @classmethod
    def _validate_secondary(cls, value: list[str] | None) -> list[str] | None:
        codes = _upper_unique(value)
        if codes is None:
            return None
        unknown = [code for code in codes if code not in POSITION_CODE_SET]
        if unknown:
            raise ValueError(f"Unknown position code(s): {', '.join(unknown)}")
        return codes

    @field_validator("tactical_roles", mode="after")
    @classmethod
    def _validate_roles(cls, value: list[str] | None) -> list[str] | None:
        roles = _lower_unique(value)
        if roles is None:
            return None
        unknown = [role for role in roles if role not in TACTICAL_ROLE_SET]
        if unknown:
            raise ValueError(f"Unknown tactical role(s): {', '.join(unknown)}")
        return roles

    @field_validator("preferred_foot", mode="after")
    @classmethod
    def _validate_foot(cls, value: str | None) -> str | None:
        if value is None:
            return None
        foot = value.strip().lower()
        if foot not in PREFERRED_FOOT_VALUES:
            raise ValueError(f"Unknown preferred foot: {foot}")
        return foot


class TalentRecomputeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: date | None = Field(
        default=None,
        description="Ranking reference date. Omit to use today; supply it for reproducible backfills.",
    )


class TalentAdminActionResponse(BaseModel):
    profile: dict[str, Any]
    action: str
    recorded_at: str


class TalentModerationLogEntry(BaseModel):
    id: str
    action: str
    reason: str | None = None
    actor_user_id: str | None = None
    created_at: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)


class TalentModerationLogResponse(BaseModel):
    player_id: str
    entries: list[TalentModerationLogEntry]


class TalentVerificationHistoryEntry(BaseModel):
    id: str
    tier: str
    decision: str
    evidence_kind: str | None = None
    evidence_reference: str | None = None
    decided_by_user_id: str | None = None
    decided_at: str | None = None
    expires_at: str | None = None
    reviewer_notes: str | None = None


class TalentVerificationHistoryResponse(BaseModel):
    player_id: str
    current_tier: str
    records: list[TalentVerificationHistoryEntry]


__all__ = [
    "ShortlistCreateRequest",
    "ShortlistEntryCreateRequest",
    "ShortlistEntryUpdateRequest",
    "ShortlistEntryView",
    "ShortlistListResponse",
    "ShortlistUpdateRequest",
    "ShortlistView",
    "TalentAdminActionResponse",
    "TalentCompareRequest",
    "TalentCompareResponse",
    "TalentCorrectionRequest",
    "TalentFeatureRequest",
    "TalentModerationLogEntry",
    "TalentModerationLogResponse",
    "TalentModerationRequest",
    "TalentProfileResponse",
    "TalentRankingResponse",
    "TalentRecomputeRequest",
    "TalentSearchPagination",
    "TalentSearchRequest",
    "TalentSearchResponse",
    "TalentSignalsResponse",
    "TalentVerificationHistoryEntry",
    "TalentVerificationHistoryResponse",
    "TalentVerificationRequest",
    "TalentVisibilityRequest",
]
