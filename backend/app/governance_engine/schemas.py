from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.governance_engine import (
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


class GovernanceClubPolicyView(BaseModel):
    governance_mode: str
    vote_weight_model: str
    anti_takeover_enabled: bool
    max_holder_bps: int
    owner_approval_threshold_bps: int
    proposal_share_threshold: int
    quorum_share_bps: int
    shareholder_rights_preserved_on_sale: bool


class GovernanceClubRecentProposalView(BaseModel):
    id: str
    title: str
    status: GovernanceProposalStatus
    yes_weight: int
    no_weight: int
    abstain_weight: int
    created_at: datetime
    updated_at: datetime


class GovernanceClubTransferView(BaseModel):
    transfer_id: str
    seller_user_id: str
    buyer_user_id: str
    executed_sale_price: Decimal
    created_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class GovernanceClubOwnershipHistoryView(BaseModel):
    transfer_count: int
    last_transfer_id: str | None = None
    last_transfer_at: datetime | None = None
    shareholder_continuity_transfers: int
    recent_transfers: list[GovernanceClubTransferView] = Field(default_factory=list)


class GovernanceClubDynastySnapshotView(BaseModel):
    dynasty_score: int
    dynasty_level: int
    dynasty_title: str
    seasons_completed: int
    last_season_label: str | None = None
    ownership_eras: int
    shareholder_continuity_transfers: int
    showcase_summary_json: dict[str, object] = Field(default_factory=dict)


class GovernanceClubPanelResponse(BaseModel):
    club_id: str
    current_owner_user_id: str
    market_id: str | None = None
    market_status: str
    governance_unit: str
    viewer_is_owner: bool
    viewer_share_count: int
    viewer_vote_weight: int
    viewer_ownership_bps: int
    viewer_can_create_proposals: bool
    viewer_can_vote: bool
    viewer_eligibility_reason: str | None = None
    viewer_owner_approval_required: bool
    total_governance_shares: int
    quorum_share_weight: int
    anti_takeover_cap_share_count: int
    shareholder_count: int
    open_proposal_count: int
    ownership_eras: int
    policy: GovernanceClubPolicyView
    recent_proposals: list[GovernanceClubRecentProposalView] = Field(default_factory=list)
    ownership_history: GovernanceClubOwnershipHistoryView
    dynasty_snapshot: GovernanceClubDynastySnapshotView


class GovernanceOverviewResponse(BaseModel):
    open_proposal_count: int
    clubs_with_tokens: int
    eligible_club_ids: list[str]
    recent_vote_count: int
