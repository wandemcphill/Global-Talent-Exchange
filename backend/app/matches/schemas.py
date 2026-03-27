from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.models.match_event import MatchEventTeam, MatchEventType


class MatchReplayEventView(CommonSchema):
    id: str
    match_id: str
    sequence: int = Field(ge=1)
    minute: int = Field(ge=0, le=130)
    type: MatchEventType
    team: MatchEventTeam
    player_id: str | None = None
    player_name: str | None = None
    team_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MatchReplayTeamStatsView(CommonSchema):
    goals: int = Field(default=0, ge=0)
    possession_estimate: int = Field(default=50, ge=0, le=100)
    total_shots: int = Field(default=0, ge=0)
    shots_on_target: int = Field(default=0, ge=0)
    big_chances: int = Field(default=0, ge=0)
    pass_accuracy: float = Field(default=0.0, ge=0.0, le=100.0)
    fouls: int = Field(default=0, ge=0)
    yellow_cards: int = Field(default=0, ge=0)
    red_cards: int = Field(default=0, ge=0)
    substitutions: int = Field(default=0, ge=0)


class MatchReplayStatsView(CommonSchema):
    home: MatchReplayTeamStatsView
    away: MatchReplayTeamStatsView


class MatchKeyMomentView(CommonSchema):
    minute: int = Field(ge=0, le=130)
    type: MatchEventType
    team: MatchEventTeam
    headline: str


class MatchMomentumShiftView(CommonSchema):
    minute: int = Field(ge=0, le=130)
    team: MatchEventTeam
    reason: str


class MatchReplaySummaryView(CommonSchema):
    stats: MatchReplayStatsView
    key_moments: list[MatchKeyMomentView] = Field(default_factory=list)
    momentum_shifts: list[MatchMomentumShiftView] = Field(default_factory=list)


class MatchReplayView(CommonSchema):
    match_id: str
    timeline: list[MatchReplayEventView] = Field(default_factory=list)
    summary: MatchReplaySummaryView


class MatchAnalysisView(CommonSchema):
    match_id: str
    team: MatchEventTeam
    problems: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
