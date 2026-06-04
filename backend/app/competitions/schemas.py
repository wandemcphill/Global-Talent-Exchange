from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.competition_lifecycle import (
    CompetitionMatchView,
    CompetitionStandingView,
)


CompetitionDataStatus = Literal["synced", "empty", "syncing", "blocked", "degraded"]


class CompetitionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    code: str | None
    country_name: str | None
    season_count: int
    club_count: int
    updated_at: datetime


class CompetitionFeedState(BaseModel):
    status: CompetitionDataStatus
    reason: str | None = None
    blocked_reason: str | None = None
    missing_data: tuple[str, ...] = ()
    degraded_reasons: tuple[str, ...] = ()
    authoritative: bool = False
    generated_at: datetime
    updated_at: datetime | None = None


class CompetitionFixtureMatchView(CompetitionMatchView):
    home_score: int | None = Field(default=None, ge=0)
    away_score: int | None = Field(default=None, ge=0)


class CompetitionFixturesContract(BaseModel):
    competition_id: str
    state: CompetitionFeedState
    status: CompetitionDataStatus
    item_count: int = Field(ge=0)
    total_fixtures: int = Field(ge=0)
    completed_fixtures: int = Field(ge=0)
    score_status: str
    authoritative_scores: bool
    items: tuple[CompetitionFixtureMatchView, ...] = ()


class CompetitionStandingsContract(BaseModel):
    competition_id: str
    state: CompetitionFeedState
    status: CompetitionDataStatus
    item_count: int = Field(ge=0)
    total_participants: int = Field(ge=0)
    total_matches: int = Field(ge=0)
    completed_matches: int = Field(ge=0)
    standings_complete: bool
    items: tuple[CompetitionStandingView, ...] = ()


class CompetitionBracketLifecycleView(BaseModel):
    stage: str
    status: str
    bracket_published: bool = False
    reason: str | None = None
    blocked_reason: str | None = None
    degraded: bool = False
    degraded_reasons: tuple[str, ...] = ()
    starts_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None


class CompetitionBracketSideView(BaseModel):
    participant_id: str | None = None
    club_id: str | None = None
    name: str | None = None
    seed: int | None = None
    score: int | None = None
    source_match_id: str | None = None
    source_label: str | None = None


class CompetitionBracketMatchView(BaseModel):
    id: str
    round_id: str | None = None
    order: int = Field(ge=0)
    label: str | None = None
    status: str
    home: CompetitionBracketSideView
    away: CompetitionBracketSideView
    home_score: int | None = Field(default=None, ge=0)
    away_score: int | None = Field(default=None, ge=0)
    winner_participant_id: str | None = None
    live_match_id: str | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CompetitionBracketRoundView(BaseModel):
    id: str
    order: int = Field(ge=0)
    name: str | None = None
    status: str
    matches: tuple[CompetitionBracketMatchView, ...] = ()
    starts_at: datetime | None = None
    completed_at: datetime | None = None


class CompetitionBracketContract(BaseModel):
    competition_id: str
    bracket_id: str | None = None
    title: str | None = None
    revision: str | None = None
    lifecycle: CompetitionBracketLifecycleView
    state: CompetitionFeedState
    status: CompetitionDataStatus
    rounds: tuple[CompetitionBracketRoundView, ...] = ()
    generated_at: datetime
    updated_at: datetime | None = None
    backend_warnings: tuple[str, ...] = ()
