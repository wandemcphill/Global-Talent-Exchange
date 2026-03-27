from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class RivalryPlayerView(CommonSchema):
    player_id: str
    player_name: str
    club_id: str | None = None
    club_name: str | None = None
    position: str | None = None


class PlayerRivalryView(CommonSchema):
    id: str
    intensity_score: float
    players: list[RivalryPlayerView] = Field(default_factory=list)
    history: dict[str, Any] = Field(default_factory=dict)
    stats_comparison: dict[str, Any] = Field(default_factory=dict)


class StoryChapterView(CommonSchema):
    title: str
    summary: str
    source_keys: list[str] = Field(default_factory=list)


class StoryMomentView(CommonSchema):
    title: str
    event_type: str
    summary: str
    occurred_on: date | None = None
    importance: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryMatchView(CommonSchema):
    match_id: str
    match_date: date | None = None
    competition: str | None = None
    club_name: str | None = None
    opponent_name: str | None = None
    rating: float | None = None
    goals: int = 0
    assists: int = 0
    summary: str


class PlayerStoryView(CommonSchema):
    id: str
    player_id: str
    chapters: list[StoryChapterView] = Field(default_factory=list)
    key_moments: list[StoryMomentView] = Field(default_factory=list)
    rivalries: list[PlayerRivalryView] = Field(default_factory=list)
    timeline_narrative: list[StoryMomentView] = Field(default_factory=list)
    key_matches: list[StoryMatchView] = Field(default_factory=list)
    defining_moments: list[StoryMomentView] = Field(default_factory=list)
    narrative_score: float
    created_at: datetime


class PlayerDNATraitsView(CommonSchema):
    tempo: float
    risk_taking: float
    creativity: float
    discipline: float


class PlayerDNAView(CommonSchema):
    player_id: str
    archetype: str
    traits: PlayerDNATraitsView
    evolution: list[dict[str, Any]] = Field(default_factory=list)


class YouthTournamentParticipantView(CommonSchema):
    team_id: str
    team_name: str
    source: str
    player_count: int
    average_age: float | None = None
    average_rating: float | None = None
    player_ids: list[str] = Field(default_factory=list)


class YouthTournamentFixtureView(CommonSchema):
    match_id: str
    stage: str
    group: str | None = None
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    home_score: int
    away_score: int
    winner_team_id: str | None = None
    top_performers: list[dict[str, Any]] = Field(default_factory=list)


class YouthTournamentStandingView(CommonSchema):
    team_id: str
    team_name: str
    group: str | None = None
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0


class YouthTournamentTopPlayerView(CommonSchema):
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    source_type: str
    goals: int = 0
    assists: int = 0
    average_rating: float = 0.0
    award: str | None = None


class YouthTournamentView(CommonSchema):
    id: str
    name: str
    age_limit: str
    participants: list[YouthTournamentParticipantView] = Field(default_factory=list)
    rewards: dict[str, Any] = Field(default_factory=dict)
    start_date: date
    end_date: date
    fixtures: list[YouthTournamentFixtureView] = Field(default_factory=list)
    standings: list[YouthTournamentStandingView] = Field(default_factory=list)
    top_players: list[YouthTournamentTopPlayerView] = Field(default_factory=list)
    status: str


class YouthTournamentCreateRequest(CommonSchema):
    name: str = Field(min_length=3, max_length=160)
    age_limit: str = Field(min_length=2, max_length=12)
    rewards: dict[str, Any] = Field(default_factory=dict)
    start_date: date
    end_date: date
    participant_club_ids: list[str] = Field(default_factory=list, max_length=16)
    participant_limit: int = Field(default=4, ge=4, le=8)
    simulate_immediately: bool = True


class RegenUniverseJobRunView(CommonSchema):
    job_id: str
    name: str
    status: str
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


__all__ = [
    "PlayerDNAView",
    "PlayerDNATraitsView",
    "PlayerRivalryView",
    "PlayerStoryView",
    "RegenUniverseJobRunView",
    "RivalryPlayerView",
    "StoryChapterView",
    "StoryMatchView",
    "StoryMomentView",
    "YouthTournamentCreateRequest",
    "YouthTournamentFixtureView",
    "YouthTournamentParticipantView",
    "YouthTournamentStandingView",
    "YouthTournamentTopPlayerView",
    "YouthTournamentView",
]
