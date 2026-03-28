from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.access_control.schemas import OrganizationMembershipView
from app.models.access_control import OrganizationType
from app.models.user import KycStatus, UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str | None
    phone_number: str | None
    display_name: str | None
    role: UserRole
    kyc_status: KycStatus
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    active_organization_id: str | None = None
    active_organization_name: str | None = None
    active_organization_type: OrganizationType | None = None
    memberships: tuple[OrganizationMembershipView, ...] = ()


class UserAffinityBreakdown(BaseModel):
    format: str | None = None
    creator_id: str | None = None
    format_match: float
    creator_match: float
    engagement_history: float
    score: float


class UserAffinityProfileView(BaseModel):
    profile_key: str
    user_id: str
    favorite_formats: dict[str, float] = Field(default_factory=dict)
    favorite_creators: dict[str, float] = Field(default_factory=dict)
    avg_watch_time: float = 0.0
    skip_rate: float = 0.0
    session_duration: float = 0.0
    engagement_score: float = 0.0
    affinity_vector: dict[str, float] = Field(default_factory=dict)
    affinity: UserAffinityBreakdown | None = None
    updated_at: datetime


class FollowUserView(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    full_name: str | None = None
    creator_handle: str | None = None
    creator_tier: str | None = None
    followers_count: int = 0
    followed_at: datetime | None = None


class FollowMutationView(BaseModel):
    follower_id: str
    following_id: str
    following: bool
    target_followers_count: int = 0
    current_following_count: int = 0


class FollowListResponse(BaseModel):
    user_id: str
    total: int = 0
    users: list[FollowUserView] = Field(default_factory=list)


class SuggestedFollowView(FollowUserView):
    affinity_similarity: float = 0.0
    shared_engagement_score: float = 0.0
    social_boost: float = 0.0
    score: float = 0.0
    reason: str


class SuggestedFollowResponse(BaseModel):
    user_id: str
    suggestions: list[SuggestedFollowView] = Field(default_factory=list)
    generated_at: datetime
