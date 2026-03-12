from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.club_identity.models.reputation import PrestigeTier


class ContinentalStage(str, Enum):
    NONE = "none"
    LEAGUE_PHASE = "league_phase"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    RUNNER_UP = "runner_up"
    WINNER = "winner"


class WorldSuperCupStage(str, Enum):
    NONE = "none"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    RUNNER_UP = "runner_up"
    WINNER = "winner"


class SeasonReputationOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    club_id: str = Field(min_length=1, max_length=36)
    season: int = Field(ge=1)
    league_finish: int | None = Field(default=None, ge=1, le=20)
    qualified_for_continental: bool = False
    continental_stage: ContinentalStage = ContinentalStage.NONE
    qualified_for_world_super_cup: bool = False
    world_super_cup_stage: WorldSuperCupStage = WorldSuperCupStage.NONE
    other_trophy_wins: int = Field(default=0, ge=0, le=20)
    consecutive_top_competition_seasons: int = Field(default=0, ge=0, le=100)
    top_scorer_awards: int = Field(default=0, ge=0, le=20)
    top_assist_awards: int = Field(default=0, ge=0, le=20)
    undefeated_league_season: bool = False
    league_title_streak: int = Field(default=0, ge=0, le=50)
    continental_title_streak: int = Field(default=0, ge=0, le=50)
    club_age_years: int = Field(default=0, ge=0, le=250)
    activity_consistency_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    fair_play_bonus: bool = False
    giant_killer: bool = False

    @field_validator("league_title_streak")
    @classmethod
    def validate_league_title_streak(cls, value: int, info) -> int:
        league_finish = info.data.get("league_finish")
        if value > 0 and league_finish != 1:
            raise ValueError("league_title_streak requires league_finish=1")
        return value

    @field_validator("continental_title_streak")
    @classmethod
    def validate_continental_title_streak(cls, value: int, info) -> int:
        continental_stage = info.data.get("continental_stage")
        if value > 0 and continental_stage != ContinentalStage.WINNER:
            raise ValueError("continental_title_streak requires continental_stage=winner")
        return value


class ReputationMilestoneView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    badge_code: str | None
    season: int | None
    delta: int
    occurred_at: datetime


class SeasonReputationSnapshotView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    season: int
    score_before: int
    season_delta: int
    score_after: int
    prestige_tier: PrestigeTier
    badges: list[str]
    milestones: list[str]
    event_count: int
    rolled_up_at: datetime


class ClubReputationView(BaseModel):
    club_id: str
    current_score: int
    current_prestige_tier: PrestigeTier
    highest_score: int
    last_active_season: int | None
    badges_earned: list[str]
    biggest_milestones: list[ReputationMilestoneView]


class ClubReputationHistoryView(BaseModel):
    club_id: str
    current_score: int
    current_prestige_tier: PrestigeTier
    history: list[SeasonReputationSnapshotView]


class ClubPrestigeView(BaseModel):
    club_id: str
    current_score: int
    current_prestige_tier: PrestigeTier
    next_tier: PrestigeTier | None
    points_to_next_tier: int | None


class PrestigeLeaderboardEntry(BaseModel):
    club_id: str
    current_score: int
    current_prestige_tier: PrestigeTier
    highest_score: int
    total_seasons: int


class PrestigeLeaderboardView(BaseModel):
    leaderboard: list[PrestigeLeaderboardEntry]
