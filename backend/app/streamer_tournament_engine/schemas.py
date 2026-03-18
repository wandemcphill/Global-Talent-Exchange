from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models.streamer_tournament import (
    StreamerTournamentApprovalStatus,
    StreamerTournamentEntryStatus,
    StreamerTournamentInviteStatus,
    StreamerTournamentQualificationType,
    StreamerTournamentRewardGrantStatus,
    StreamerTournamentRewardType,
    StreamerTournamentRiskStatus,
    StreamerTournamentStatus,
    StreamerTournamentType,
)


class StreamerTournamentRewardInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    reward_type: StreamerTournamentRewardType
    placement_start: int = Field(ge=1)
    placement_end: int = Field(ge=1)
    amount: Decimal | None = Field(default=None, ge=0)
    cosmetic_sku: str | None = Field(default=None, max_length=120)
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shape(self) -> "StreamerTournamentRewardInput":
        if self.placement_end < self.placement_start:
            raise ValueError("placement_end must be greater than or equal to placement_start")
        if self.reward_type in {
            StreamerTournamentRewardType.GTEX_COIN,
            StreamerTournamentRewardType.FAN_COIN,
        } and (self.amount is None or self.amount <= 0):
            raise ValueError("coin rewards require a positive amount")
        if self.reward_type is StreamerTournamentRewardType.EXCLUSIVE_COSMETIC and not self.cosmetic_sku:
            raise ValueError("exclusive cosmetic rewards require a cosmetic_sku")
        return self


class StreamerTournamentCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    tournament_type: StreamerTournamentType
    max_participants: int = Field(default=8, ge=2, le=256)
    season_id: str | None = None
    linked_competition_id: str | None = None
    playoff_source_competition_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    qualification_methods: list[StreamerTournamentQualificationType] = Field(default_factory=list)
    top_gifter_rank_limit: int | None = Field(default=None, ge=1, le=500)
    entry_rules_json: dict[str, object] = Field(default_factory=dict)
    metadata_json: dict[str, object] = Field(default_factory=dict)
    rewards: list[StreamerTournamentRewardInput] = Field(default_factory=list)
    invite_user_ids: list[str] = Field(default_factory=list)


class StreamerTournamentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    max_participants: int | None = Field(default=None, ge=2, le=256)
    season_id: str | None = None
    linked_competition_id: str | None = None
    playoff_source_competition_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    qualification_methods: list[StreamerTournamentQualificationType] | None = None
    top_gifter_rank_limit: int | None = Field(default=None, ge=1, le=500)
    entry_rules_json: dict[str, object] | None = None
    metadata_json: dict[str, object] | None = None


class StreamerTournamentRewardPlanReplaceRequest(BaseModel):
    rewards: list[StreamerTournamentRewardInput] = Field(default_factory=list)


class StreamerTournamentInviteCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    note: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class StreamerTournamentJoinRequest(BaseModel):
    qualification_source_hint: StreamerTournamentQualificationType | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class StreamerTournamentPublishRequest(BaseModel):
    submission_notes: str | None = Field(default=None, max_length=4000)


class StreamerTournamentReviewRequest(BaseModel):
    approve: bool
    notes: str | None = Field(default=None, max_length=4000)


class StreamerTournamentPolicyUpsertRequest(BaseModel):
    reward_coin_approval_limit: Decimal = Field(default=Decimal("500.0000"), ge=0)
    reward_credit_approval_limit: Decimal = Field(default=Decimal("5000.0000"), ge=0)
    max_cosmetic_rewards_without_review: int = Field(default=10, ge=0, le=1000)
    max_reward_slots: int = Field(default=12, ge=1, le=500)
    max_invites_per_tournament: int = Field(default=64, ge=1, le=1000)
    top_gifter_rank_limit: int = Field(default=25, ge=1, le=500)
    active: bool = True
    config_json: dict[str, object] = Field(default_factory=dict)


class StreamerTournamentRiskReviewRequest(BaseModel):
    action: StreamerTournamentRiskStatus
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_action(self) -> "StreamerTournamentRiskReviewRequest":
        if self.action not in {StreamerTournamentRiskStatus.RESOLVED, StreamerTournamentRiskStatus.DISMISSED}:
            raise ValueError("risk signals can only be resolved or dismissed")
        return self


class StreamerTournamentSettlementPlacement(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    placement: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)


class StreamerTournamentSettleRequest(BaseModel):
    placements: list[StreamerTournamentSettlementPlacement] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=500)


class StreamerTournamentRewardView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    title: str
    reward_type: StreamerTournamentRewardType
    placement_start: int
    placement_end: int
    amount: Decimal | None
    cosmetic_sku: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class StreamerTournamentInviteView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    invited_user_id: str
    invited_by_user_id: str
    status: StreamerTournamentInviteStatus
    note: str | None
    responded_at: datetime | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class StreamerTournamentEntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    user_id: str
    invite_id: str | None
    entry_role: str
    qualification_source: StreamerTournamentQualificationType
    qualification_snapshot_json: dict[str, object]
    status: StreamerTournamentEntryStatus
    seed: int | None
    placement: int | None
    joined_at: datetime | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class StreamerTournamentRiskSignalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    signal_key: str
    severity: str
    status: StreamerTournamentRiskStatus
    summary: str
    detail: str | None
    detected_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by_user_id: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class StreamerTournamentRewardGrantView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tournament_id: str
    reward_id: str
    entry_id: str | None
    recipient_user_id: str
    placement: int | None
    reward_type: StreamerTournamentRewardType
    amount: Decimal | None
    cosmetic_sku: str | None
    settlement_status: StreamerTournamentRewardGrantStatus
    reward_settlement_id: str | None
    ledger_transaction_id: str | None
    settled_by_user_id: str | None
    settled_at: datetime | None
    note: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class StreamerTournamentPolicyView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_key: str
    reward_coin_approval_limit: Decimal
    reward_credit_approval_limit: Decimal
    max_cosmetic_rewards_without_review: int
    max_reward_slots: int
    max_invites_per_tournament: int
    top_gifter_rank_limit: int
    active: bool
    config_json: dict[str, object]
    updated_by_user_id: str | None
    created_at: datetime
    updated_at: datetime


class StreamerTournamentView(BaseModel):
    id: str
    host_user_id: str
    creator_profile_id: str
    creator_club_id: str
    season_id: str | None
    linked_competition_id: str | None
    playoff_source_competition_id: str | None
    slug: str
    title: str
    description: str | None
    tournament_type: StreamerTournamentType
    status: StreamerTournamentStatus
    approval_status: StreamerTournamentApprovalStatus
    max_participants: int
    requires_admin_approval: bool
    high_reward_flag: bool
    starts_at: datetime | None
    ends_at: datetime | None
    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    completed_at: datetime | None
    approved_by_user_id: str | None
    rejected_by_user_id: str | None
    submission_notes: str | None
    approval_notes: str | None
    entry_rules_json: dict[str, object]
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    rewards: list[StreamerTournamentRewardView] = Field(default_factory=list)
    invites: list[StreamerTournamentInviteView] = Field(default_factory=list)
    entries: list[StreamerTournamentEntryView] = Field(default_factory=list)
    open_risk_signals: list[StreamerTournamentRiskSignalView] = Field(default_factory=list)


class StreamerTournamentListView(BaseModel):
    tournaments: list[StreamerTournamentView] = Field(default_factory=list)


class StreamerTournamentSettlementView(BaseModel):
    tournament: StreamerTournamentView
    grants: list[StreamerTournamentRewardGrantView] = Field(default_factory=list)

