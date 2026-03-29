from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema


class PunditPersonaView(CommonSchema):
    name: str
    style: str
    stance: str | None = None
    bias: dict[str, list[str]] = Field(default_factory=dict)
    confidence_level: float | None = Field(default=None, ge=0.0, le=1.0)
    debate_style: str | None = None
    signature_line: str | None = None


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
    stance: str | None = None
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


class PunditShowMatchContextView(CommonSchema):
    match_id: str
    home_team_name: str
    away_team_name: str
    status: str
    stage: str
    competition_type: str
    is_final: bool = False
    kickoff_at: datetime | None = None
    score: str | None = None
    winner_team_name: str | None = None
    featured_event_name: str | None = None


class PunditShowStatsView(CommonSchema):
    home_win_probability: int = Field(default=0, ge=0, le=100)
    draw_probability: int = Field(default=0, ge=0, le=100)
    away_win_probability: int = Field(default=0, ge=0, le=100)
    expected_goals_home: float = Field(default=0.0, ge=0.0)
    expected_goals_away: float = Field(default=0.0, ge=0.0)
    total_expected_goals: float = Field(default=0.0, ge=0.0)
    possession_winner: str | None = None
    key_player: str | None = None
    key_player_rating: float | None = None
    summary_line: str | None = None


class PunditPredictionView(CommonSchema):
    predicted_winner: str | None = None
    predicted_score: str
    confidence: float = Field(ge=0.0, le=1.0)
    home_win_probability: int = Field(default=0, ge=0, le=100)
    draw_probability: int = Field(default=0, ge=0, le=100)
    away_win_probability: int = Field(default=0, ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)


class PunditShowSegmentView(CommonSchema):
    order: int = Field(ge=1)
    segment_type: str
    title: str
    speaker: str
    summary: str
    talking_points: list[str] = Field(default_factory=list)


class PunditInteractionView(CommonSchema):
    speaker: str
    interaction_type: str
    target_speaker: str | None = None
    line: str
    tone: str = "balanced"


class PunditPlayerRatingView(CommonSchema):
    player_id: str | None = None
    player_name: str
    team_name: str | None = None
    rating: float = Field(ge=0.0, le=10.0)
    verdict: str


class PunditShowResponse(CommonSchema):
    match_id: str
    show_type: str
    headline: str
    match_context: PunditShowMatchContextView
    pundit_profiles: list[PunditPersonaView] = Field(default_factory=list)
    stats: PunditShowStatsView
    global_memory: list[str] = Field(default_factory=list)
    segments: list[PunditShowSegmentView] = Field(default_factory=list)
    interactions: list[PunditInteractionView] = Field(default_factory=list)
    player_ratings: list[PunditPlayerRatingView] = Field(default_factory=list)
    controversial_decisions: list[str] = Field(default_factory=list)
    prediction: PunditPredictionView | None = None
    pipeline: list[str] = Field(default_factory=list)
    generated_at: datetime
