from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.common.schemas.base import CommonSchema
from app.fairness.spend_balance_controller import SpendTier, TournamentFairnessMode
from app.match_engine.simulation.models import PlayerRole
from app.services.ads.schemas import MatchViewerMonetizationView


class MatchViewerEventType(StrEnum):
    KICKOFF = "kickoff"
    GOAL = "goal"
    SAVE = "save"
    MISS = "miss"
    FOUL = "foul"
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


class MatchViewerPlaybackStage(StrEnum):
    PRE = "pre"
    EVENT = "event"
    HOLD = "hold"
    REVIEW = "review"
    DECISION = "decision"
    POST = "post"
    RESET = "reset"


class MatchViewerCameraPreset(StrEnum):
    BROADCAST = "broadcast"
    ATTACK_PUSH = "attack_push"
    BOX_ZOOM = "box_zoom"
    GOAL_CELEBRATION = "goal_celebration"
    ASSISTANT_FLAG = "assistant_flag"
    VAR_REPLAY = "var_replay"


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


class MatchMode(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    CINEMATIC = "cinematic"


class MatchViewerPointView(CommonSchema):
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)


class MatchViewerVector3View(CommonSchema):
    x: float
    y: float
    z: float


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
    height: float = Field(default=0.0, ge=0.0)
    owner_player_id: str | None = None
    state: str = Field(default="rolling", min_length=1)
    spin: MatchViewerVector3View | None = None
    velocity: MatchViewerVector3View | None = None


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
    playback_profile: str = Field(default="neutral")
    miss_variant: str | None = None
    reviewable: bool = False
    review_reason: str | None = None
    review_decision: str | None = None
    score_commit: str = Field(default="immediate")


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
    stage: MatchViewerPlaybackStage = MatchViewerPlaybackStage.EVENT
    camera_preset: MatchViewerCameraPreset = MatchViewerCameraPreset.BROADCAST
    overlay_text: str | None = None
    pause_playback: bool = False
    playback_rate: float = Field(default=1.0, ge=0.05, le=4.0)
    flag_animation: bool = False
    celebration_team_id: str | None = None
    players: list[MatchViewerPlayerFrameView] = Field(default_factory=list)
    ball: MatchViewerBallFrameView


class MatchViewStateView(CommonSchema):
    match_id: str
    source: str
    match_mode: MatchMode = MatchMode.STANDARD
    supports_offside: bool = False
    deterministic_seed: int | None = Field(default=None, ge=0)
    duration_seconds: int = Field(ge=0)
    home_team: MatchViewerTeamView
    away_team: MatchViewerTeamView
    events: list[MatchViewerEventView] = Field(default_factory=list)
    frames: list[MatchTimelineFrameView] = Field(default_factory=list)
    monetization: MatchViewerMonetizationView | None = None


class FairnessIndicatorStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    TAMPERED = "tampered"


class MatchTimelineProofStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    TAMPERED = "tampered"


class MatchFairnessIndicatorView(CommonSchema):
    status: FairnessIndicatorStatus = FairnessIndicatorStatus.UNVERIFIED
    label: str = "Fair Play Pending"
    message: str | None = None
    no_pay_to_win: bool = True
    visual_only_monetization: bool = True
    server_authoritative: bool = True
    tournament_fairness_mode: TournamentFairnessMode | None = None
    home_spend_tier: SpendTier | None = None
    away_spend_tier: SpendTier | None = None
    squad_balance_policy: str | None = None
    soft_balance_applied: bool = False


class MatchTimelineProofView(CommonSchema):
    status: MatchTimelineProofStatus = MatchTimelineProofStatus.UNVERIFIED
    match_hash: str = Field(default="", min_length=0)
    timeline_hash: str = Field(default="", min_length=0)
    visible_timeline_hash: str = Field(default="", min_length=0)
    signed: bool = True
    revealed_through_seconds: int = Field(default=0, ge=0)


class MatchViewerSessionView(MatchViewStateView):
    fairness_indicator: MatchFairnessIndicatorView = Field(default_factory=MatchFairnessIndicatorView)
    timeline_proof: MatchTimelineProofView = Field(default_factory=MatchTimelineProofView)
    score_reveal_locked: bool = True
    segment_start_seconds: int = Field(default=0, ge=0)
    segment_end_seconds: int = Field(default=0, ge=0)
    has_more_segments: bool = False
    next_segment_token: str | None = None
