from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.governance_engine import (
    GovernanceProposalScope,
    GovernanceProposalStatus,
    GovernanceVoteChoice,
)


class GovernanceProposalCreateRequest(BaseModel):
    club_id: str | None = None
    scope: GovernanceProposalScope = GovernanceProposalScope.CLUB
    title: str = Field(min_length=4, max_length=180)
    summary: str = Field(min_length=10, max_length=5000)
    category: str = Field(default="general", min_length=2, max_length=64)
    minimum_tokens_required: int = Field(default=1, ge=1, le=1_000_000)
    quorum_token_weight: int = Field(default=0, ge=0, le=10_000_000)
    voting_ends_at_iso: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class GovernanceVoteRequest(BaseModel):
    choice: GovernanceVoteChoice
    comment: str | None = Field(default=None, max_length=1000)


class GovernanceProposalStatusRequest(BaseModel):
    status: GovernanceProposalStatus
    result_summary: str | None = Field(default=None, max_length=2000)


class GovernanceProposalView(BaseModel):
    id: str
    club_id: str | None
    proposer_user_id: str
    scope: GovernanceProposalScope
    status: GovernanceProposalStatus
    title: str
    summary: str
    category: str
    voting_starts_at_iso: str | None
    voting_ends_at_iso: str | None
    minimum_tokens_required: int
    quorum_token_weight: int
    yes_weight: int
    no_weight: int
    abstain_weight: int
    unique_voter_count: int
    result_summary: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GovernanceVoteView(BaseModel):
    id: str
    proposal_id: str
    voter_user_id: str
    club_id: str | None
    choice: GovernanceVoteChoice
    token_weight: int
    influence_weight: int
    comment: str | None
    is_proxy_vote: bool
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GovernanceProposalListResponse(BaseModel):
    proposals: list[GovernanceProposalView]


class GovernanceProposalDetailResponse(BaseModel):
    proposal: GovernanceProposalView
    votes: list[GovernanceVoteView]
    my_vote: GovernanceVoteView | None = None
    user_eligible: bool
    eligibility_reason: str | None = None


class GovernanceVoteResponse(BaseModel):
    proposal: GovernanceProposalView
    vote: GovernanceVoteView
    summary: str


class GovernanceOverviewResponse(BaseModel):
    open_proposal_count: int
    clubs_with_tokens: int
    eligible_club_ids: list[str]
    recent_vote_count: int
