from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.tournament import TournamentGameType, TournamentStatus


class TournamentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    game_type: TournamentGameType
    entry_fee: int = Field(default=0, ge=0)
    max_players: int = Field(default=8, ge=2, le=256)
    round_timeout_minutes: int = Field(default=60, ge=1, le=10_080)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class TournamentJoinRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)


class TournamentMatchResultRequest(BaseModel):
    winner_user_id: str = Field(min_length=1, max_length=36)
    player_one_score: int | None = Field(default=None, ge=0)
    player_two_score: int | None = Field(default=None, ge=0)


class TournamentPlayerView(BaseModel):
    user_id: str
    display_name: str | None = None
    bracket_slot: int
    status: str
    joined_at: datetime


class TournamentRoundView(BaseModel):
    round_number: int
    status: str
    starts_at: datetime
    timeout_at: datetime
    completed_at: datetime | None = None


class TournamentMatchView(BaseModel):
    match_id: str
    round_number: int
    slot_index: int
    player_one_user_id: str | None = None
    player_two_user_id: str | None = None
    winner_user_id: str | None = None
    player_one_score: int | None = None
    player_two_score: int | None = None
    status: str
    resolution: str | None = None
    completed_at: datetime | None = None


class TournamentView(BaseModel):
    tournament_id: str
    name: str
    game_type: TournamentGameType
    entry_fee: int
    max_players: int
    status: TournamentStatus
    rounds: int
    current_round: int
    prize_pool: int
    round_timeout_minutes: int
    player_count: int
    spots_remaining: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    winner_user_id: str | None = None
    players: list[TournamentPlayerView] = Field(default_factory=list)
    rounds_detail: list[TournamentRoundView] = Field(default_factory=list)
    matches: list[TournamentMatchView] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class TournamentListView(BaseModel):
    tournaments: list[TournamentView] = Field(default_factory=list)
