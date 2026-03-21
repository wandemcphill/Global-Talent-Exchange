from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.match_engine.simulation.models import PlayerRole


class MatchViewerEventType(StrEnum):
    KICKOFF = "kickoff"
    GOAL = "goal"
    SAVE = "save"
    MISS = "miss"
    OFFSIDE = "offside"
    RED_CARD = "red_card"
    YELLOW_CARD = "yellow_card"
    SUBSTITUTION = "substitution"
    INJURY = "injury"
    HALFTIME = "halftime"
    FULLTIME = "fulltime"
    ATTACK = "attack"
    SET_PIECE = "set_piece"
    PENALTY = "penalty"
    NEUTRAL = "neutral"


class MatchViewerPhase(StrEnum):
    KICKOFF = "kickoff"
    OPEN_PLAY = "open_play"
    SET_PIECE = "set_piece"
    HALFTIME = "halftime"
    FULLTIME = "fulltime"


class MatchViewerPlayerState(StrEnum):
    IDLE = "idle"
    MOVING = "moving"
    PRESSING = "pressing"
    ATTACKING = "attacking"
    DEFENDING = "defending"
    SENT_OFF = "sent_off"


class MatchViewerSide(StrEnum):
    HOME = "home"
    AWAY = "away"


class MatchViewerPointView(CommonSchema):
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)


class MatchViewerTeamView(CommonSchema):
    team_id: str
    team_name: str
    short_name: str
    side: MatchViewerSide
    formation: str
    primary_color: str
    secondary_color: str
    accent_color: str
    goalkeeper_color: str


class MatchViewerPlayerFrameView(CommonSchema):
    player_id: str
    team_id: str
    side: MatchViewerSide
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    label: str
    role: PlayerRole
    line: str
    state: MatchViewerPlayerState
    active: bool = True
    highlighted: bool = False
    position: MatchViewerPointView
    anchor_position: MatchViewerPointView


class MatchViewerBallFrameView(CommonSchema):
    position: MatchViewerPointView
    owner_player_id: str | None = None
    state: str = Field(default="rolling", min_length=1)


class MatchViewerEventView(CommonSchema):
    event_id: str
    sequence: int = Field(ge=0)
    event_type: MatchViewerEventType
    minute: int = Field(ge=0, le=120)
    added_time: int = Field(default=0, ge=0, le=15)
    clock_label: str
    time_seconds: float = Field(ge=0.0)
    team_id: str | None = None
    team_name: str | None = None
    primary_player_id: str | None = None
    primary_player_name: str | None = None
    secondary_player_id: str | None = None
    secondary_player_name: str | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    banner_text: str
    commentary: str
    emphasis_level: int = Field(default=1, ge=1, le=3)
    highlighted_player_ids: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class MatchTimelineFrameView(CommonSchema):
    frame_id: str
    time_seconds: float = Field(ge=0.0)
    clock_minute: float = Field(ge=0.0, le=120.0)
    phase: MatchViewerPhase
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    home_attacks_right: bool
    possession_side: MatchViewerSide = MatchViewerSide.HOME
    active_event_id: str | None = None
    event_banner: str | None = None
    players: list[MatchViewerPlayerFrameView] = Field(default_factory=list)
    ball: MatchViewerBallFrameView


class MatchViewStateView(CommonSchema):
    match_id: str
    source: str
    supports_offside: bool = False
    deterministic_seed: int | None = Field(default=None, ge=0)
    duration_seconds: int = Field(ge=0)
    home_team: MatchViewerTeamView
    away_team: MatchViewerTeamView
    events: list[MatchViewerEventView] = Field(default_factory=list)
    frames: list[MatchTimelineFrameView] = Field(default_factory=list)
