from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema


class PunditPersonaView(CommonSchema):
    name: str
    style: str
    stance: str


class PunditMatchAnalysisView(CommonSchema):
    score: str
    winner_team_name: str | None = None
    xg_diff: float = 0.0
    shot_diff: int = 0
    possession_winner: str | None = None
    upset: bool = False
    is_final: bool = False
    key_player: str | None = None
    key_player_team: str | None = None
    key_player_rating: float | None = None
    summary_line: str = ""
    turning_point: str | None = None


class PunditDebateLineView(CommonSchema):
    speaker: str
    style: str
    stance: str
    line: str
    emphasis: str = "medium"


class PunditDebateResponse(CommonSchema):
    match_id: str
    headline: str
    format: str = "chat"
    analysis: PunditMatchAnalysisView
    personas: list[PunditPersonaView] = Field(default_factory=list)
    hot_takes: list[str] = Field(default_factory=list)
    lines: list[PunditDebateLineView] = Field(default_factory=list)
    generated_at: datetime
