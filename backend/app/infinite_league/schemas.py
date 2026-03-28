from __future__ import annotations

from typing import Any

from pydantic import Field

from app.common.schemas.base import CommonSchema


class InfiniteLeagueMatchView(CommonSchema):
    match_id: str
    league_id: str
    league_name: str
    season: int = Field(ge=1)
    round_number: int = Field(ge=1)
    home_club_name: str
    away_club_name: str
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)
    winner_club_id: str | None = None
    winner_club_name: str | None = None
    upset: bool = False
    headline: str
    hook: str
    man_of_the_match: str
    viral_score: int = Field(ge=0, le=100)
    story_tags: list[str] = Field(default_factory=list)
    narrative_flags: dict[str, bool] = Field(default_factory=dict)
    commentary_prompt: str
    pundit_prompt: str
    influencer_persona: str
    influencer_caption: str
    highlight_count: int = Field(default=0, ge=0)
    queued_publish_jobs: list[str] = Field(default_factory=list)


class InfiniteLeagueMatchesResponse(CommonSchema):
    matches: list[InfiniteLeagueMatchView] = Field(default_factory=list)


class InfiniteLeagueStatusView(CommonSchema):
    enabled: bool = True
    auto_advance: bool = True
    worker_active: bool = False
    tick_interval_seconds: float = Field(gt=0.0)
    league_name: str
    season: int = Field(ge=1)
    club_count: int = Field(ge=0)
    total_fixtures: int = Field(ge=0)
    completed_matches: int = Field(ge=0)
    queue_depth: int = Field(ge=0)
    featured_match_id: str | None = None
    next_fixture_id: str | None = None
    livestream_window_duration_seconds: int = Field(default=0, ge=0)


class InfiniteLeagueLivestreamSegmentView(CommonSchema):
    kind: str
    title: str
    path: str
    duration_seconds: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InfiniteLeagueLivestreamView(CommonSchema):
    total_duration_seconds: int = Field(ge=0)
    playlist_manifest: str
    ffmpeg_command: list[str] = Field(default_factory=list)
    segments: list[InfiniteLeagueLivestreamSegmentView] = Field(default_factory=list)


class InfiniteLeagueWalletView(CommonSchema):
    owner_id: str
    display_name: str
    coins: int = Field(ge=0)
    usd_balance: str
    cash_out_preview_usd: str
    last_event: str | None = None


class InfiniteLeagueEconomyView(CommonSchema):
    token_name: str
    token_symbol: str
    usd_per_coin: str
    wallets: list[InfiniteLeagueWalletView] = Field(default_factory=list)
