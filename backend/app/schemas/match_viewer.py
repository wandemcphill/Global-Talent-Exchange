from __future__ import annotations

from enum import StrEnum

from pydantic import AliasChoices, Field, field_validator

from app.common.schemas.base import CommonSchema
from app.fairness.spend_balance_controller import SpendTier, TournamentFairnessMode
from app.match_engine.simulation.models import PlayerRole
from app.services.ads.schemas import MatchAdPlacementView, MatchViewerMonetizationView


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
    PASS = "pass"
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


class MatchViewerAnimationState(StrEnum):
    IDLE = "idle"
    JOG = "jog"
    RUN = "run"
    SPRINT = "sprint"
    PASS = "pass"
    SHOOT = "shoot"
    PRESS = "press"
    SAVE = "save"
    CELEBRATE = "celebrate"
    SET_PIECE = "set_piece"
    SENT_OFF = "sent_off"


class MatchViewerSide(StrEnum):
    HOME = "home"
    AWAY = "away"


class MatchViewerPossessionPhase(StrEnum):
    RESTART = "restart"
    BUILD_UP = "build_up"
    TRANSITION = "transition"
    FINAL_THIRD = "final_third"
    BOX_ATTACK = "box_attack"
    SET_PIECE = "set_piece"
    DEAD_BALL = "dead_ball"


class MatchViewerTransitionState(StrEnum):
    STABLE = "stable"
    HOME_BREAK = "home_break"
    AWAY_BREAK = "away_break"
    HOME_RESET = "home_reset"
    AWAY_RESET = "away_reset"
    STOPPED = "stopped"


class MatchMode(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    CINEMATIC = "cinematic"


class MatchViewerAvailabilityStatus(StrEnum):
    READY = "ready"
    EMPTY = "empty"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class MatchViewerPointView(CommonSchema):
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)


class MatchViewerVector2View(CommonSchema):
    x: float = 0.0
    y: float = 0.0


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
    animation_state: MatchViewerAnimationState = MatchViewerAnimationState.IDLE
    speed_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    blend_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    stamina_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    has_possession: bool = False
    facing: MatchViewerVector2View = Field(default_factory=MatchViewerVector2View)
    velocity: MatchViewerVector2View = Field(default_factory=MatchViewerVector2View)


class MatchViewerBallFrameView(CommonSchema):
    position: MatchViewerPointView
    height: float = Field(default=0.0, ge=0.0)
    owner_player_id: str | None = None
    state: str = Field(default="rolling", min_length=1)
    spin: MatchViewerVector3View | None = None
    velocity: MatchViewerVector3View | None = None


class MatchViewerEventPositionView(CommonSchema):
    player_id: str
    player_name: str | None = None
    team_id: str | None = None
    side: MatchViewerSide | None = None
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    role: str | None = None
    line: str | None = None
    position: MatchViewerPointView


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
    duration_ms: int = Field(default=500, ge=300, le=800)
    positions: list[MatchViewerEventPositionView] = Field(default_factory=list)
    ball: MatchViewerBallFrameView | None = None

    @field_validator("duration_ms", mode="before")
    @classmethod
    def _clamp_duration_ms(cls, value: object) -> int:
        if value is None:
            return 500
        try:
            duration_ms = int(value)
        except (TypeError, ValueError):
            return 500
        return max(300, min(800, duration_ms))


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
    possession_phase: MatchViewerPossessionPhase = MatchViewerPossessionPhase.BUILD_UP
    transition_state: MatchViewerTransitionState = MatchViewerTransitionState.STABLE
    danger_zone: str | None = None
    pressure_index: float = Field(default=0.0, ge=0.0, le=1.0)
    compactness_home: float = Field(default=0.5, ge=0.0, le=1.0)
    compactness_away: float = Field(default=0.5, ge=0.0, le=1.0)
    frame_tags: list[str] = Field(default_factory=list)
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
    presentation_package: "MatchViewerPresentationPackageView | None" = None
    engagement: "MatchViewerEngagementView | None" = None


class MatchViewerPresentationPlayerView(CommonSchema):
    player_id: str | None = None
    player_name: str = Field(min_length=1)
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    role: str | None = Field(default=None, min_length=1)
    line: str | None = Field(default=None, min_length=1)
    x: float | None = Field(default=None, ge=0.0, le=100.0)
    y: float | None = Field(default=None, ge=0.0, le=100.0)
    rating: float | None = Field(default=None, ge=0.0, le=10.0)


class MatchViewerPresentationCrestView(CommonSchema):
    image_url: str | None = None
    shape: str | None = None
    initials: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None


class MatchViewerPresentationTeamView(CommonSchema):
    team_id: str
    team_name: str
    short_name: str
    formation: str
    crest: MatchViewerPresentationCrestView | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    goalkeeper_color: str | None = None
    coach_name: str | None = None
    recent_form: int | None = Field(default=None, ge=0, le=100)
    mentality: str | None = None
    instruction_summary: list[str] = Field(default_factory=list)
    starters: list[MatchViewerPresentationPlayerView] = Field(default_factory=list)
    bench: list[MatchViewerPresentationPlayerView] = Field(default_factory=list)


class MatchViewerStandingsEntryView(CommonSchema):
    team_id: str | None = None
    team_name: str
    position: int | None = Field(default=None, ge=1)
    played: int | None = Field(default=None, ge=0)
    points: int | None = Field(default=None, ge=0)
    goal_difference: int | None = None
    form: str | None = None


class MatchViewerContextBoardView(CommonSchema):
    competition_name: str | None = None
    competition_stage: str | None = None
    venue_name: str | None = None
    kickoff_label: str | None = None
    date_label: str | None = None
    referee_name: str | None = None
    match_significance: str | None = None
    standings: list[MatchViewerStandingsEntryView] = Field(default_factory=list)
    storylines: list[str] = Field(default_factory=list)


class MatchViewerReactionCardView(CommonSchema):
    source: str
    headline: str
    detail: str
    sentiment: str | None = None
    tag: str | None = None


class MatchViewerPresentationPackageView(CommonSchema):
    match_label: str
    home: MatchViewerPresentationTeamView
    away: MatchViewerPresentationTeamView
    context: MatchViewerContextBoardView = Field(default_factory=MatchViewerContextBoardView)
    reactions: list[MatchViewerReactionCardView] = Field(default_factory=list)
    rating_leaders: list[MatchViewerPresentationPlayerView] = Field(default_factory=list)
    momentum_notes: list[str] = Field(default_factory=list)
    coach_notes: list[str] = Field(default_factory=list)
    commentary_highlights: list[str] = Field(default_factory=list)


class MatchViewerAdStateView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.EMPTY
    ads_enabled: bool = False
    placements: list[MatchAdPlacementView] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    status_detail: str | None = None


class MatchViewerGiftTargetView(CommonSchema):
    recipient_user_id: str
    recipient_label: str
    source_scope: str
    target_type: str = "match_host"


class MatchViewerGiftCatalogItemView(CommonSchema):
    key: str
    display_name: str
    tier: str | None = None
    fancoin_price: float = Field(default=0.0, ge=0.0)
    animation_key: str | None = None
    sound_key: str | None = None
    description: str | None = None


class MatchViewerGiftCatalogStateView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.EMPTY
    source: str = "gift_engine_catalog"
    items: list[MatchViewerGiftCatalogItemView] = Field(default_factory=list)
    status_detail: str | None = None
    blocked_reason: str | None = None


class MatchViewerGiftSessionStateView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.BLOCKED
    active: bool = False
    can_send: bool = False
    session_id: str | None = None
    send_endpoint: str | None = None
    blocked_reason: str | None = None
    status_detail: str | None = None


class MatchViewerGiftContextView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.BLOCKED
    target: MatchViewerGiftTargetView | None = None
    catalog: MatchViewerGiftCatalogStateView = Field(default_factory=MatchViewerGiftCatalogStateView)
    session: MatchViewerGiftSessionStateView = Field(default_factory=MatchViewerGiftSessionStateView)
    status_detail: str | None = None


class MatchViewerEventSourceStateView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.BLOCKED
    source: str
    backend_authored: bool = True
    event_count: int = Field(default=0, ge=0)
    incident_event_count: int = Field(default=0, ge=0)
    presentation_only_event_count: int = Field(default=0, ge=0)
    blocked_reason: str | None = None
    degraded_reason: str | None = None


class MatchViewerCommentaryLineView(CommonSchema):
    event_id: str
    clock_label: str
    event_type: MatchViewerEventType
    text: str


class MatchViewerCommentaryStateView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.BLOCKED
    source: str = "timeline_events"
    lines: list[MatchViewerCommentaryLineView] = Field(default_factory=list)
    event_count: int = Field(default=0, ge=0)
    status_detail: str | None = None
    blocked_reason: str | None = None
    degraded_reason: str | None = None


class MatchViewerReactionStateView(CommonSchema):
    status: MatchViewerAvailabilityStatus = MatchViewerAvailabilityStatus.EMPTY
    source: str = "presentation_package"
    cards: list[MatchViewerReactionCardView] = Field(default_factory=list)
    status_detail: str | None = None


class MatchViewerEngagementView(CommonSchema):
    ads: MatchViewerAdStateView = Field(default_factory=MatchViewerAdStateView)
    gifting: MatchViewerGiftContextView = Field(default_factory=MatchViewerGiftContextView)
    event_source: MatchViewerEventSourceStateView
    commentary: MatchViewerCommentaryStateView = Field(default_factory=MatchViewerCommentaryStateView)
    reactions: MatchViewerReactionStateView = Field(default_factory=MatchViewerReactionStateView)


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
    visual_only_engagement: bool = Field(
        default=True,
        validation_alias=AliasChoices("visual_only_engagement", "visual_only_monetization"),
    )
    server_authoritative: bool = True
    tournament_fairness_mode: TournamentFairnessMode | None = None
    home_spend_tier: SpendTier | None = None
    away_spend_tier: SpendTier | None = None
    squad_balance_policy: str | None = None
    soft_balance_applied: bool = False

    @field_validator("message", mode="before")
    @classmethod
    def _neutralize_message(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.replace("Monetization remains visual only.", "Engagement features remain visual only.")


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
