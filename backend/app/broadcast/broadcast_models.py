from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScoreUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")

    match_id: str
    score: str
    home_score: int | None = None
    away_score: int | None = None
    minute: int | None = None
    status: str | None = None


class MatchSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    match_id: str
    viewer_count: int = 0
    peak_viewers: int = 0
    active_user_ids: list[str] = Field(default_factory=list)
    is_live: bool = True
    featured: bool = False
    score_update: ScoreUpdate | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpectatorEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    match_id: str
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=utcnow)
    sequence: int | None = None
    user_id: str | None = None
    display_name: str | None = None
    reaction: str | None = None
    message: str | None = None
    snapshot: MatchSnapshot | None = None
    score_update: ScoreUpdate | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TournamentEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    tournament_id: str
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=utcnow)
    match_id: str | None = None
    featured_match_id: str | None = None
    score_update: ScoreUpdate | None = None
    standings: list[dict[str, Any]] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class SpectatorPresenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    active_viewers: int = 0
    peak_viewers: int = 0
    active_user_ids: list[str] = Field(default_factory=list)
