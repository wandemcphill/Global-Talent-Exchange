from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.live_matches.schemas import LiveMatchStateView


class ManagerDuelCreateRequest(CommonSchema):
    home_user_id: str
    away_user_id: str
    home_manager_asset_id: str | None = None
    away_manager_asset_id: str | None = None
    home_self_managed: bool = False
    away_self_managed: bool = False
    simulation_seed: int | None = Field(default=None, ge=0)


class ManagerDuelView(CommonSchema):
    id: str
    competition_type: str
    status: str
    home_user_id: str
    away_user_id: str
    home_manager_id: str
    away_manager_id: str
    home_manager_name: str
    away_manager_name: str
    home_manager_source: str
    away_manager_source: str
    controller_home: str
    controller_away: str
    user_control_enabled: bool
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    winner_manager_id: str | None = None
    winner_user_id: str | None = None
    reputation_delta_home: float = 0.0
    reputation_delta_away: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    live_state: LiveMatchStateView | None = None


class ManagerDuelLeaderboardEntryView(CommonSchema):
    manager_id: str
    manager_name: str
    manager_source: str
    duel_wins: int = Field(ge=0)
    duel_draws: int = Field(ge=0)
    duel_losses: int = Field(ge=0)
    matches_played: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    reputation_score: float = Field(ge=0.0)
    leaderboard_rank: int = Field(ge=1)
