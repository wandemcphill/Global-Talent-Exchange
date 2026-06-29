from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LiveTeamTacticsView(BaseModel):
    formation: str
    mentality: str
    pressing: int
    tempo: int


class LiveMatchSessionView(BaseModel):
    match_id: str
    minute: int
    phase: str
    home_name: str
    away_name: str
    home_score: int
    away_score: int
    home_tactics: LiveTeamTacticsView
    away_tactics: LiveTeamTacticsView
    halftime_seconds_remaining: int | None = None
    halftime_ready: list[str] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class CreateLiveMatchRequest(BaseModel):
    match_id: str
    home_id: str
    away_id: str
    home_name: str = "Home"
    away_name: str = "Away"
    home_overall: int = 70
    away_overall: int = 70
    home_formation: str = "4-3-3"
    away_formation: str = "4-3-3"


class SetLiveTacticsRequest(BaseModel):
    side: str = Field(description="home | away")
    formation: str | None = None
    mentality: str | None = Field(default=None, description="attacking | balanced | defensive")
    pressing: int | None = None
    tempo: int | None = None


class HalftimeReadyRequest(BaseModel):
    side: str = Field(description="home | away")
