from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HistoricalRecordView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    subject_type: str | None = None
    subject_id: str | None = None
    headline: str
    narrative: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class HistoricalLeaderboardEntryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: str
    entity_id: str
    entity_name: str
    rank: int
    score: float
    score_breakdown_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class HistoricalLeaderboardsResponse(BaseModel):
    generated_at: datetime | None = None
    top_players_ever: list[HistoricalLeaderboardEntryView]
    top_clubs_ever: list[HistoricalLeaderboardEntryView]
    top_managers: list[HistoricalLeaderboardEntryView]
    tracked_records: list[HistoricalRecordView]


class GoatRankingsResponse(BaseModel):
    entity_type: str
    generated_at: datetime | None = None
    entries: list[HistoricalLeaderboardEntryView]


class HistoricalTimelineItemView(BaseModel):
    timestamp: datetime
    headline: str
    narrative: str | None = None
    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class HistoricalTimelineResponse(BaseModel):
    subject_type: str
    subject_id: str
    narrative: str | None = None
    historical_ranking: HistoricalLeaderboardEntryView | None = None
    major_milestones: list[HistoricalTimelineItemView]
    career_timeline: list[HistoricalTimelineItemView]


class AchievementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    achievement_key: str
    name: str
    description: str
    category: str
    condition: dict[str, Any] = Field(default_factory=dict)
    reward: dict[str, Any] = Field(default_factory=dict)
    active: bool


class UserAchievementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    achievement_id: str
    unlocked_at: datetime
    reward_settlement_id: str | None = None
    reward_payload_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class MilestoneProgressView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    milestone_key: str
    name: str
    description: str
    target_value: int
    current_value: int
    best_value: int
    reached_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class UserProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    followers: int
    following: int
    reputation_score: int
    profile_boost_total: int
    badge_inventory_json: list[str] = Field(default_factory=list)
    cosmetic_inventory_json: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class UserFollowCreate(BaseModel):
    target_type: str
    target_id: str


class UserFollowView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    follower_user_id: str
    target_key: str
    target_type: str
    target_user_id: str | None = None
    target_club_id: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SocialActivityCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1_000)


class SocialActivityView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None = None
    activity_type: str
    target_user_id: str | None = None
    target_club_id: str | None = None
    rivalry_key: str | None = None
    headline: str
    body: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ClubCommunityResponse(BaseModel):
    club_id: str
    follower_count: int
    fan_chat: list[SocialActivityView]
    activity_wall: list[SocialActivityView]


class RivalryPageResponse(BaseModel):
    rivalry_key: str
    club_a_id: str
    club_b_id: str
    label: str
    intensity_score: int
    streak_length: int
    streak_holder_club_id: str | None = None
    notable_moments: list[str] = Field(default_factory=list)
    banter: list[SocialActivityView]


class ObjectiveProgressView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    task_frequency: str
    task_key: str
    period_key: str
    description: str
    threshold_value: float
    progress_value: float
    reward_multiplier: float
    completed: bool
    completed_at: datetime | None = None
    reward_granted_at: datetime | None = None
    reward_settlement_id: str | None = None
    reward_payload_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SeasonMissionProgressView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mission_key: str
    frequency: str
    period_key: str
    description: str
    threshold_value: float
    progress_value: float
    reward_payload_json: dict[str, Any] = Field(default_factory=dict)
    completed: bool
    completed_at: datetime | None = None
    reward_granted_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SeasonPassRewardView(BaseModel):
    id: str
    level: int
    premium_only: bool = False
    title: str
    description: str | None = None
    reward_payload_json: dict[str, Any] = Field(default_factory=dict)
    unlocked: bool
    claimable: bool
    claimed: bool


class SeasonRewardClaimView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    season_id: str
    reward_id: str
    claimed_at: datetime
    granted_payload_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SeasonPassView(BaseModel):
    season_id: str
    title: str
    duration_days: int
    levels: int
    starts_at: datetime
    ends_at: datetime
    current_level: int
    current_xp: int
    xp_per_level: int
    xp_into_current_level: int
    xp_for_next_level: int
    xp_progress: float
    premium_enabled: bool
    has_premium: bool
    xp_rules: dict[str, int] = Field(default_factory=dict)
    daily_missions: list[SeasonMissionProgressView]
    rewards: list[SeasonPassRewardView]


class UserStreakView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    streak_days: int
    longest_streak_days: int
    last_completed_on: date | None = None
    reward_multiplier: Decimal
    xp_boost_multiplier: Decimal
    coin_boost_multiplier: Decimal
    warning_sent_on: date | None = None
    last_reset_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ObjectivesResponse(BaseModel):
    streak: UserStreakView
    daily_tasks: list[ObjectiveProgressView]
    weekly_tasks: list[ObjectiveProgressView]


class EngagementSyncResponse(BaseModel):
    profile: UserProfileView
    streak: UserStreakView
    unlocked_achievements: list[UserAchievementView]
    daily_tasks: list[ObjectiveProgressView]
    weekly_tasks: list[ObjectiveProgressView]
    season_pass: SeasonPassView


class WorkerRunResponse(BaseModel):
    history_records: int
    leaderboard_entries: int
    reconciled_users: int
    notifications_created: int
