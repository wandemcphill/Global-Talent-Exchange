from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema


class YouthAcademyUpsertRequest(CommonSchema):
    club_user_id: str
    club_id: str | None = None
    level: int = Field(default=1, ge=1, le=10)
    scouting_regions: tuple[str, ...] = Field(default_factory=tuple)
    capacity: int = Field(default=6, ge=1, le=64)
    upgrade_cost: int = Field(default=100_000, ge=0)


class YouthAcademyView(CommonSchema):
    id: str
    club_user_id: str
    club_id: str | None = None
    level: int
    scouting_regions: tuple[str, ...] = Field(default_factory=tuple)
    capacity: int
    upgrade_cost: int
    created_at: datetime
    updated_at: datetime


class AcademyGenerationRequest(CommonSchema):
    club_user_id: str
    club_id: str | None = None
    season_label: str | None = None


class AcademyGeneratedPlayerView(CommonSchema):
    academy_candidate_id: str
    player_id: str
    regen_profile_id: str
    regen_id: str
    display_name: str
    age: int
    primary_position: str
    potential_min: int
    potential_max: int
    rarity_tier: str
    badge_codes: tuple[str, ...] = Field(default_factory=tuple)
    market_value_coin: int


class AcademyGenerationResultView(CommonSchema):
    academy: YouthAcademyView
    batch_id: str | None = None
    season_label: str
    generated_count: int = Field(ge=0)
    generated_players: tuple[AcademyGeneratedPlayerView, ...] = Field(default_factory=tuple)


class AcademyPromotionView(CommonSchema):
    academy_candidate_id: str
    player_id: str
    regen_profile_id: str
    promoted: bool
    contract_id: str | None = None
    academy_slots_remaining: int = Field(ge=0)
    status: str


class ScoutCreateRequest(CommonSchema):
    club_user_id: str
    club_id: str | None = None
    region: str
    skill_rating: int = Field(ge=0, le=100)
    specialty: str = Field(default="youth")


class ScoutView(CommonSchema):
    id: str
    club_user_id: str
    club_id: str | None = None
    region: str
    skill_rating: int
    specialty: str
    active: bool = True
    created_at: datetime
    updated_at: datetime


class ScoutDiscoveryResultView(CommonSchema):
    scout: ScoutView
    discovery_probability: float
    discovered_players: tuple[AcademyGeneratedPlayerView, ...] = Field(default_factory=tuple)


class ScoutReportView(CommonSchema):
    scout_id: str
    player_id: str
    regen_profile_id: str
    accuracy: int = Field(ge=0, le=100)
    visible_stats: dict[str, int] = Field(default_factory=dict)
    hidden_stats: dict[str, int | None] = Field(default_factory=dict)
    potential_range: dict[str, int] = Field(default_factory=dict)
    personality_state: dict[str, int | float | str | bool] = Field(default_factory=dict)
    rarity_tier: str
    badge_codes: tuple[str, ...] = Field(default_factory=tuple)
    summary_text: str
    generated_at: datetime


class CareerEventView(CommonSchema):
    id: str
    player_id: str
    regen_profile_id: str | None = None
    type: str
    occurred_on: date
    impact: dict[str, object] = Field(default_factory=dict)
    summary: str | None = None
    created_at: datetime


class AgentCreateRequest(CommonSchema):
    name: str
    negotiation_skill: int = Field(ge=0, le=100)
    player_ids: tuple[str, ...] = Field(default_factory=tuple)


class AgentView(CommonSchema):
    id: str
    name: str
    negotiation_skill: int
    player_ids: tuple[str, ...] = Field(default_factory=tuple)
    created_at: datetime
    updated_at: datetime


class RegenFeedItemView(CommonSchema):
    event_type: str
    occurred_at: datetime
    player_id: str | None = None
    regen_profile_id: str | None = None
    display_name: str | None = None
    headline: str
    details: dict[str, object] = Field(default_factory=dict)


class RegenHubPlayerView(CommonSchema):
    player_id: str
    regen_profile_id: str
    regen_id: str
    display_name: str
    age: int
    primary_position: str
    current_rating: int
    potential_max: int
    rarity_tier: str
    uniqueness_score: float
    market_value_coin: int
    badge_codes: tuple[str, ...] = Field(default_factory=tuple)
    score: float
    rank: int | None = None


class RegenBloodlineNodeView(CommonSchema):
    regen_profile_id: str
    regen_id: str
    display_name: str
    parent_legacy_id: str | None = None
    legacy_score: float | None = None
    legacy_tier: str | None = None


class RegenLineageChainView(CommonSchema):
    regen_profile_id: str
    chain: tuple[RegenBloodlineNodeView, ...] = Field(default_factory=tuple)


class AwardVoteRequest(CommonSchema):
    user_id: str
    player_id: str
    season_id: str | None = None


class AwardVoteView(CommonSchema):
    id: str
    user_id: str
    player_id: str
    award_id: str
    season_id: str
    voted_at: datetime


class RegenAwardHubView(CommonSchema):
    award_id: str
    award_code: str
    award_name: str
    season_id: str
    season_number: int
    winners: list[dict[str, object]] = Field(default_factory=list)
    vote_totals: list[dict[str, object]] = Field(default_factory=list)


class RegenJobRunView(CommonSchema):
    job_name: str
    result: dict[str, object] = Field(default_factory=dict)


__all__ = [
    "AcademyGeneratedPlayerView",
    "AcademyGenerationRequest",
    "AcademyGenerationResultView",
    "AcademyPromotionView",
    "AgentCreateRequest",
    "AgentView",
    "AwardVoteRequest",
    "AwardVoteView",
    "CareerEventView",
    "RegenAwardHubView",
    "RegenBloodlineNodeView",
    "RegenFeedItemView",
    "RegenHubPlayerView",
    "RegenJobRunView",
    "RegenLineageChainView",
    "ScoutCreateRequest",
    "ScoutDiscoveryResultView",
    "ScoutReportView",
    "ScoutView",
    "YouthAcademyUpsertRequest",
    "YouthAcademyView",
]
