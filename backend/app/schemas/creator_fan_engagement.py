from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.creator_fan_engagement import (
    CreatorFanCompetitionStatus,
    CreatorMatchChatMessageVisibility,
    CreatorMatchChatRoomStatus,
    CreatorRivalrySignalStatus,
    CreatorRivalrySignalSurface,
    CreatorTacticalAdviceStatus,
    CreatorTacticalAdviceType,
)


class CreatorClubFollowCreateRequest(BaseModel):
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorClubFollowView(BaseModel):
    id: str
    club_id: str
    user_id: str
    source: str
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatorFanGroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    identity_label: str | None = Field(default=None, max_length=120)
    is_official: bool = False
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorFanGroupJoinRequest(BaseModel):
    fan_identity_label: str | None = Field(default=None, max_length=120)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorFanGroupMembershipView(BaseModel):
    id: str
    group_id: str
    user_id: str
    club_id: str
    member_role: str
    fan_identity_label: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatorFanGroupView(BaseModel):
    id: str
    club_id: str
    created_by_user_id: str
    slug: str
    name: str
    description: str | None
    identity_label: str | None
    is_official: bool
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class CreatorFanCompetitionCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    match_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorFanCompetitionJoinRequest(BaseModel):
    fan_group_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorFanCompetitionEntryView(BaseModel):
    id: str
    fan_competition_id: str
    user_id: str
    club_id: str
    fan_group_id: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatorFanCompetitionView(BaseModel):
    id: str
    club_id: str
    created_by_user_id: str
    match_id: str | None
    title: str
    description: str | None
    status: CreatorFanCompetitionStatus
    starts_at: datetime | None
    ends_at: datetime | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    entry_count: int = 0

    model_config = {"from_attributes": True}


class CreatorFanChatEligibilityView(BaseModel):
    can_comment: bool
    reason: str | None = None
    shareholder: bool
    supporter_share_balance: int = 0
    creator_share_balance: int = 0
    creator_shareholder: bool = False
    season_pass_holder: bool
    paying_viewer: bool
    visibility_priority: int
    has_cosmetic_voting_rights: bool = False
    cosmetic_vote_power: int = 0
    followed_club_ids: list[str] = Field(default_factory=list)
    fan_group_ids: list[str] = Field(default_factory=list)
    fan_competition_ids: list[str] = Field(default_factory=list)


class CreatorMatchChatMessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    supported_club_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorMatchChatMessageView(BaseModel):
    id: str
    room_id: str
    author_user_id: str
    supported_club_id: str | None
    body: str
    visibility: CreatorMatchChatMessageVisibility
    visibility_priority: int
    shareholder: bool
    season_pass_holder: bool
    paying_viewer: bool
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatorMatchChatRoomView(BaseModel):
    id: str
    season_id: str
    competition_id: str
    match_id: str
    room_key: str
    status: CreatorMatchChatRoomStatus
    phase: str
    opens_at: datetime | None
    closes_at: datetime | None
    is_open: bool
    message_count: int
    layout_hints_json: dict[str, object]
    metadata_json: dict[str, object]
    access: CreatorFanChatEligibilityView
    created_at: datetime
    updated_at: datetime


class CreatorTacticalAdviceCreateRequest(BaseModel):
    advice_type: CreatorTacticalAdviceType
    suggestion_text: str = Field(min_length=3, max_length=255)
    supported_club_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorTacticalAdviceView(BaseModel):
    id: str
    season_id: str
    competition_id: str
    match_id: str
    author_user_id: str
    supported_club_id: str | None
    advice_type: CreatorTacticalAdviceType
    suggestion_text: str
    visibility_priority: int
    status: CreatorTacticalAdviceStatus
    authority: str
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatorFanWallItemView(BaseModel):
    item_id: str
    item_type: str
    club_id: str | None
    match_id: str | None
    headline: str
    body: str | None = None
    prominence: int
    created_at: datetime
    reference_type: str | None = None
    reference_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CreatorFanWallView(BaseModel):
    match_id: str
    layout_hints_json: dict[str, object]
    items: list[CreatorFanWallItemView] = Field(default_factory=list)


class CreatorFanStateView(BaseModel):
    club_id: str
    match_id: str | None = None
    following: bool
    shareholder: bool
    supporter_share_balance: int
    creator_share_balance: int = 0
    creator_shareholder: bool = False
    season_pass_holder: bool
    paying_viewer: bool
    can_comment: bool
    visibility_priority: int
    has_cosmetic_voting_rights: bool = False
    cosmetic_vote_power: int = 0
    fan_group_ids: list[str] = Field(default_factory=list)
    fan_competition_ids: list[str] = Field(default_factory=list)
    gifts_sent_count: int


class CreatorRivalrySignalView(BaseModel):
    id: str
    match_id: str
    home_club_id: str
    away_club_id: str
    club_social_rivalry_id: str | None
    surface: CreatorRivalrySignalSurface
    signal_status: CreatorRivalrySignalStatus
    score: int
    headline: str
    message: str
    target_user_count: int
    rationale_json: dict[str, object]
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
