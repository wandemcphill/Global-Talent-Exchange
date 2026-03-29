from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class NewsHeadlineVariantsView(CommonSchema):
    dramatic: str
    neutral: str
    click_worthy: str


class NewsArticleView(CommonSchema):
    id: str
    article_type: str
    title: str
    body: str
    summary: str | None = None
    tags_json: list[str] = Field(default_factory=list)
    headline_variants_json: NewsHeadlineVariantsView
    related_match_id: str | None = None
    related_player_id: str | None = None
    related_club_id: str | None = None
    related_user_id: str | None = None
    trend_score: float
    perception_delta: float
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PrestigeRankingEntryView(CommonSchema):
    id: str
    entity_type: str
    entity_id: str
    entity_name: str
    scope: str
    season_key: str
    prestige_score: float
    trophies: float
    win_rate: float = Field(ge=0.0, le=1.0)
    player_development: float
    earnings: float
    difficulty_modifier: float
    perception_score: float
    prestige_tier: str
    rank_position: int | None = Field(default=None, ge=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PrestigeRankingListView(CommonSchema):
    entity_type: str
    scope: str
    season_key: str
    generated_at: datetime
    entries: list[PrestigeRankingEntryView] = Field(default_factory=list)


class GlobalPrestigeRankingsView(CommonSchema):
    scope: str
    season_key: str
    generated_at: datetime
    players: list[PrestigeRankingEntryView] = Field(default_factory=list)
    clubs: list[PrestigeRankingEntryView] = Field(default_factory=list)
    users: list[PrestigeRankingEntryView] = Field(default_factory=list)
    national_teams: list[PrestigeRankingEntryView] = Field(default_factory=list)


class PlayerPersonalityView(CommonSchema):
    player_id: str
    player_name: str
    aggression: int = Field(ge=1, le=99)
    confidence: int = Field(ge=1, le=99)
    loyalty: int = Field(ge=1, le=99)
    ego: int = Field(ge=1, le=99)
    consistency: int = Field(ge=1, le=99)
    clutch_factor: int = Field(ge=1, le=99)
    competitiveness: int = Field(ge=1, le=99)
    professionalism: int = Field(ge=1, le=99)
    media_appetite: int = Field(ge=1, le=99)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class PlayerInterviewView(CommonSchema):
    id: str
    player_id: str
    article_id: str | None = None
    match_id: str | None = None
    interview_type: str
    sentiment: str
    question: str | None = None
    quote: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
