from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.common.enums.club_reputation_tier import ClubReputationTier
from app.common.schemas.base import CommonSchema


class _ClubOrmSchema(CommonSchema):
    model_config = ConfigDict(from_attributes=True)


class ReputationEventCore(_ClubOrmSchema):
    id: str
    club_id: str
    season: int | None = None
    event_type: str
    source: str
    delta: int
    score_after: int
    summary: str
    milestone: str | None = None
    badge_code: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReputationSnapshotCore(_ClubOrmSchema):
    id: str
    club_id: str
    season: int
    score_before: int
    season_delta: int
    score_after: int
    tier: ClubReputationTier
    badges: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    event_count: int
    rolled_up_at: datetime


class ReputationScoreBreakdown(CommonSchema):
    competition_participation: int = 0
    competition_completion: int = 0
    competition_wins: int = 0
    creator_competition_performance: int = 0
    fair_play: int = 0
    community_growth: int = 0
    sustained_activity: int = 0
    trophy_prestige: int = 0


class ClubReputationCore(CommonSchema):
    club_id: str
    current_score: int
    highest_score: int
    tier: ClubReputationTier
    breakdown: ReputationScoreBreakdown = Field(default_factory=ReputationScoreBreakdown)
    recent_events: list[ReputationEventCore] = Field(default_factory=list)
    last_snapshot: ReputationSnapshotCore | None = None
