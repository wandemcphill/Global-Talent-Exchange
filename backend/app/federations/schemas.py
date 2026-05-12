from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.federation import (
    FederationCompetitionType,
    FederationMembershipStatus,
    FederationProposalStatus,
    FederationSanctionType,
    FederationVoteType,
)
from app.models.real_world_hub import RealityMode


class FederationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=160)
    structure_json: dict[str, Any] = Field(default_factory=dict)
    rules_json: dict[str, Any] = Field(default_factory=dict)
    is_public: bool = True
    default_reality_mode: RealityMode = RealityMode.HYBRID
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationLeagueCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=160)
    competition_type: FederationCompetitionType = FederationCompetitionType.LEAGUE
    format: str = Field(min_length=2, max_length=32)
    divisions_json: list[dict[str, Any]] = Field(default_factory=list)
    promotion_relegation_rules_json: dict[str, Any] = Field(default_factory=dict)
    entry_requirements_json: dict[str, Any] = Field(default_factory=dict)
    governance_rules_override_json: dict[str, Any] = Field(default_factory=dict)
    season_label: str | None = Field(default=None, max_length=48)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationMembershipCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    club_id: str
    user_id: str | None = None
    role: str = Field(default="member_club", min_length=2, max_length=32)
    auto_activate: bool = False
    entry_requirements_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationProposalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    league_id: str | None = None
    proposal_type: str = Field(default="rule_change", min_length=2, max_length=48)
    title: str = Field(min_length=4, max_length=180)
    summary: str = Field(min_length=10, max_length=5000)
    payload_json: dict[str, Any] = Field(default_factory=dict)
    voting_ends_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationVoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vote_type: FederationVoteType
    comment: str | None = Field(default=None, max_length=1000)


class FederationSanctionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    league_id: str | None = None
    club_id: str | None = None
    player_id: str | None = None
    sanction_type: FederationSanctionType = FederationSanctionType.FINE
    reason: str = Field(min_length=5, max_length=5000)
    fine_amount: Decimal = Decimal("0.0000")
    points_deduction: int = Field(default=0, ge=0, le=100)
    suspension_matches: int = Field(default=0, ge=0, le=100)
    ends_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationValidateActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    league_id: str | None = None
    action_type: str = Field(min_length=2, max_length=48)
    club_id: str | None = None
    player_id: str | None = None
    proposed_fee: Decimal | None = None
    proposed_wage: Decimal | None = None
    source_reference: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class NationalEligibilityReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None
    club_id: str | None = None
    competition_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationRevenueDistributionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(min_length=2, max_length=32)
    source_reference: str | None = None
    gross_amount: Decimal | None = None
    federation_share_bps: int | None = Field(default=None, ge=0, le=10000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    owner_user_id: str
    structure_json: dict[str, Any]
    rules_json: dict[str, Any]
    competitions_json: list[dict[str, Any]]
    members_json: list[dict[str, Any]]
    reputation_score: float
    ranking_score: float
    treasury_balance: Decimal
    audience_size: int
    is_public: bool
    default_reality_mode: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationLeagueView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    federation_id: str
    linked_competition_id: str | None
    name: str
    competition_type: str
    format: str
    divisions_json: list[dict[str, Any]]
    promotion_relegation_rules_json: dict[str, Any]
    entry_requirements_json: dict[str, Any]
    governance_rules_override_json: dict[str, Any]
    season_label: str | None
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RegionalTournamentLeagueView(BaseModel):
    federation_id: str
    federation_name: str
    league_id: str
    linked_competition_id: str | None = None
    name: str
    competition_type: str
    season_label: str | None = None
    status: str
    member_count: int = 0


class RegionalTournamentView(BaseModel):
    region_code: str
    region_label: str
    federation_count: int
    active_league_count: int
    total_member_clubs: int
    leagues: list[RegionalTournamentLeagueView] = Field(default_factory=list)


class NationalAssociationFederationView(BaseModel):
    federation_id: str
    name: str
    ranking_score: float = 0
    reputation_score: float = 0
    active_league_count: int = 0
    active_member_count: int = 0
    rules: dict[str, Any] = Field(default_factory=dict)


class NationalAssociationProfileView(BaseModel):
    country_code: str
    country_name: str
    confederation_code: str | None = None
    market_region: str | None = None
    federation_count: int = 0
    active_league_count: int = 0
    member_club_count: int = 0
    sanction_count: int = 0
    ranking_score: float = 0
    top_federations: list[NationalAssociationFederationView] = Field(default_factory=list)
    national_team_oversight: dict[str, Any] = Field(default_factory=dict)


class NationalEligibilityReviewView(BaseModel):
    country_code: str
    country_name: str
    allowed: bool
    audit_id: str | None = None
    applied_rules: list[str] = Field(default_factory=list)
    violations: list[dict[str, Any]] = Field(default_factory=list)
    federation_ids: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FederationMembershipView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    federation_id: str
    club_id: str
    user_id: str | None
    role: str
    status: FederationMembershipStatus
    entry_requirements_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationProposalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    federation_id: str
    league_id: str | None
    proposer_user_id: str
    proposal_type: str
    title: str
    summary: str
    payload_json: dict[str, Any]
    status: FederationProposalStatus
    voting_starts_at: datetime
    voting_ends_at: datetime | None
    yes_votes: int
    no_votes: int
    abstain_votes: int
    result_summary: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationVoteView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    proposal_id: str
    federation_id: str
    user_id: str
    vote_type: FederationVoteType
    weight: int
    comment: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationSanctionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    federation_id: str
    league_id: str | None
    club_id: str | None
    player_id: str | None
    applied_by_user_id: str
    sanction_type: FederationSanctionType
    reason: str
    fine_amount: Decimal
    points_deduction: int
    suspension_matches: int
    starts_at: datetime
    ends_at: datetime | None
    status: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationTreasuryEntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    federation_id: str
    source_type: str
    source_reference: str
    gross_amount: Decimal
    federation_share: Decimal
    club_distribution_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationNarrativeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    federation_id: str
    narrative_type: str
    headline: str
    body: str
    score: float
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FederationRuleViolationView(BaseModel):
    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class FederationValidationResultView(BaseModel):
    allowed: bool
    applied_rules: list[str] = Field(default_factory=list)
    violations: list[FederationRuleViolationView] = Field(default_factory=list)
    audit_id: str


class FederationDashboardView(BaseModel):
    leagues: list[FederationLeagueView] = Field(default_factory=list)
    rules: dict[str, Any] = Field(default_factory=dict)
    members: list[dict[str, Any]] = Field(default_factory=list)
    reputation: dict[str, Any] = Field(default_factory=dict)


class FederationGovernanceView(BaseModel):
    proposals: list[FederationProposalView] = Field(default_factory=list)
    votes: list[FederationVoteView] = Field(default_factory=list)
    sanctions: list[FederationSanctionView] = Field(default_factory=list)


class FederationRankingItemView(BaseModel):
    federation_id: str
    name: str
    ranking_score: float
    reputation_score: float
    audience_size: int
    activity_score: float
    competitiveness_score: float


class FederationJobsRunView(BaseModel):
    closed_proposals: int
    audits_run: int
    broadcast_distributions: int
    narratives_refreshed: int
    rankings_refreshed: int
