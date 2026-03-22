from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.common.enums.match_status import MatchStatus
from app.common.schemas.base import CommonSchema
from app.match_engine.simulation.models import (
    MatchCompetitionType,
    MatchEventType,
    MatchHighlightProfile,
    MatchSpectatorMode,
    PlayerRole,
    TacticalStyle,
)


def _validate_formation_string(formation: str, *, allowed_outfield_totals: tuple[int, ...] = (10,)) -> str:
    chunks = formation.split("-")
    if len(chunks) not in {3, 4}:
        raise ValueError("Formation must use 3 or 4 lines, for example '4-3-3' or '4-2-3-1'")
    try:
        numbers = tuple(int(chunk) for chunk in chunks)
    except ValueError as exc:
        raise ValueError("Formation must only contain integer line counts") from exc
    if any(number <= 0 for number in numbers):
        raise ValueError("Formation line counts must be positive")
    if sum(numbers) not in allowed_outfield_totals:
        totals = ", ".join(str(total) for total in allowed_outfield_totals)
        raise ValueError(f"Formation lines must sum to one of these outfield totals: {totals}")
    return formation


class MatchPlayerInput(CommonSchema):
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    role: PlayerRole
    overall: int = Field(ge=1, le=100)
    finishing: int = Field(default=50, ge=1, le=100)
    creativity: int = Field(default=50, ge=1, le=100)
    defending: int = Field(default=50, ge=1, le=100)
    goalkeeping: int = Field(default=1, ge=1, le=100)
    discipline: int = Field(default=70, ge=1, le=100)
    fitness: int = Field(default=70, ge=1, le=100)
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    display_name: str | None = Field(default=None, min_length=1, max_length=32)
    position_archetype: str | None = Field(default=None, min_length=2, max_length=32)
    pace: int | None = Field(default=None, ge=1, le=100)
    composure: int | None = Field(default=None, ge=1, le=100)
    decision_making: int | None = Field(default=None, ge=1, le=100)
    positioning: int | None = Field(default=None, ge=1, le=100)
    off_ball_movement: int | None = Field(default=None, ge=1, le=100)
    aerial_ability: int | None = Field(default=None, ge=1, le=100)
    technique: int | None = Field(default=None, ge=1, le=100)
    stamina_curve: int | None = Field(default=None, ge=1, le=100)
    consistency: int | None = Field(default=None, ge=1, le=100)
    clutch_factor: int | None = Field(default=None, ge=1, le=100)
    big_match_temperament: int | None = Field(default=None, ge=1, le=100)
    recent_form: int | None = Field(default=None, ge=1, le=100)
    morale: int | None = Field(default=None, ge=1, le=100)
    motivation: int | None = Field(default=None, ge=1, le=100)
    fatigue_load: int | None = Field(default=None, ge=0, le=100)
    injury_risk: int | None = Field(default=None, ge=0, le=100)
    leadership: int | None = Field(default=None, ge=1, le=100)


class TeamTacticalPlanInput(CommonSchema):
    style: TacticalStyle = TacticalStyle.BALANCED
    pressing: int = Field(default=55, ge=0, le=100)
    tempo: int = Field(default=55, ge=0, le=100)
    aggression: int = Field(default=50, ge=0, le=100)
    defensive_line: int = Field(default=50, ge=0, le=100)
    width: int = Field(default=50, ge=0, le=100)
    mentality: TacticalStyle = TacticalStyle.BALANCED
    set_piece_emphasis: int = Field(default=50, ge=0, le=100)
    player_instructions: dict[str, Any] | None = None
    game_state_adjustments: dict[str, Any] | None = None
    substitution_windows: tuple[int, ...] = Field(default=(60, 72, 82), min_length=1, max_length=5)
    red_card_fallback_formation: str = Field(default="4-4-1", min_length=5)
    injury_auto_substitution: bool = True
    yellow_card_substitution_minute: int = Field(default=70, ge=45, le=89)
    yellow_card_replacement_roles: tuple[PlayerRole, ...] = Field(
        default=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
        min_length=1,
    )
    max_substitutions: int = Field(default=5, ge=1, le=5)
    tactical_quality: int = Field(default=60, ge=1, le=100)
    adaptability: int = Field(default=60, ge=1, le=100)
    game_management: int = Field(default=60, ge=1, le=100)

    @model_validator(mode="after")
    def validate_tactics(self) -> TeamTacticalPlanInput:
        _validate_formation_string(self.red_card_fallback_formation, allowed_outfield_totals=(9, 10))
        if tuple(sorted(set(self.substitution_windows))) != self.substitution_windows:
            raise ValueError("Substitution windows must be unique and sorted in ascending order")
        if any(window < 46 or window > 89 for window in self.substitution_windows):
            raise ValueError("Substitution windows must be between minutes 46 and 89")
        return self


class MatchKitIdentityInput(CommonSchema):
    kit_type: str = Field(default="home", min_length=2, max_length=24)
    primary_color: str = Field(default="#123C73", min_length=4, max_length=16)
    secondary_color: str = Field(default="#F5F7FA", min_length=4, max_length=16)
    accent_color: str = Field(default="#E2A400", min_length=4, max_length=16)
    shorts_color: str = Field(default="#0C1F3F", min_length=4, max_length=16)
    socks_color: str = Field(default="#F5F7FA", min_length=4, max_length=16)
    pattern_type: str = Field(default="solid", min_length=3, max_length=24)
    collar_style: str = Field(default="crew", min_length=3, max_length=24)
    sleeve_style: str = Field(default="short", min_length=3, max_length=24)
    badge_placement: str = Field(default="left_chest", min_length=3, max_length=32)
    front_text: str | None = Field(default=None, max_length=20)


class MatchTeamIdentityInput(CommonSchema):
    club_name: str | None = Field(default=None, min_length=1, max_length=120)
    short_club_code: str | None = Field(default=None, min_length=2, max_length=8)
    is_national_team: bool = False
    national_team_code: str | None = Field(default=None, min_length=2, max_length=8)
    badge_url: str | None = Field(default=None, max_length=255)
    badge_shape: str = Field(default="shield", min_length=3, max_length=24)
    badge_initials: str = Field(default="FC", min_length=1, max_length=6)
    badge_primary_color: str = Field(default="#123C73", min_length=4, max_length=16)
    badge_secondary_color: str = Field(default="#F5F7FA", min_length=4, max_length=16)
    badge_accent_color: str = Field(default="#E2A400", min_length=4, max_length=16)
    home_kit: MatchKitIdentityInput | None = None
    away_kit: MatchKitIdentityInput | None = None
    third_kit: MatchKitIdentityInput | None = None
    goalkeeper_kit: MatchKitIdentityInput | None = None


class MatchClubContextInput(CommonSchema):
    club_tier: int = Field(default=60, ge=1, le=100)
    competition_tier: int = Field(default=60, ge=1, le=100)
    team_chemistry: int = Field(default=62, ge=1, le=100)
    recent_form: int = Field(default=58, ge=1, le=100)
    morale: int = Field(default=60, ge=1, le=100)
    motivation: int = Field(default=60, ge=1, le=100)
    fatigue_load: int = Field(default=36, ge=0, le=100)
    travel_load: int = Field(default=28, ge=0, le=100)
    rivalry_intensity: int = Field(default=0, ge=0, le=100)
    schedule_pressure: int = Field(default=34, ge=0, le=100)


class MatchTeamInput(CommonSchema):
    team_id: str = Field(min_length=1)
    team_name: str = Field(min_length=1)
    formation: str = Field(default="4-3-3", min_length=5)
    tactics: TeamTacticalPlanInput = Field(default_factory=TeamTacticalPlanInput)
    manager_profile: dict[str, Any] | None = None
    club_context: MatchClubContextInput = Field(default_factory=MatchClubContextInput)
    identity: MatchTeamIdentityInput | None = None
    starters: list[MatchPlayerInput] = Field(min_length=11, max_length=11)
    bench: list[MatchPlayerInput] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_team(self) -> MatchTeamInput:
        _validate_formation_string(self.formation)
        starter_goalkeepers = [player for player in self.starters if player.role is PlayerRole.GOALKEEPER]
        if len(starter_goalkeepers) != 1:
            raise ValueError("Exactly one goalkeeper must be named in the starting lineup")
        starter_ids = {player.player_id for player in self.starters}
        if len(starter_ids) != len(self.starters):
            raise ValueError("Starter player IDs must be unique within a team")
        bench_ids = {player.player_id for player in self.bench}
        if len(bench_ids) != len(self.bench):
            raise ValueError("Bench player IDs must be unique within a team")
        if starter_ids & bench_ids:
            raise ValueError("Starters and bench players must not overlap")
        return self


class MatchCompetitionContextInput(CommonSchema):
    competition_type: MatchCompetitionType = MatchCompetitionType.LEAGUE
    stage: str = Field(default="regular", min_length=1)
    is_final: bool = False
    requires_winner: bool | None = None
    halftime_duration_seconds: int | None = Field(default=None, ge=60, le=120)


class MatchTacticalAdjustmentInput(CommonSchema):
    formation: str | None = Field(default=None, min_length=5)
    tempo: int | None = Field(default=None, ge=0, le=100)
    pressing: int | None = Field(default=None, ge=0, le=100)
    aggression: int | None = Field(default=None, ge=0, le=100)
    defensive_line: int | None = Field(default=None, ge=0, le=100)
    width: int | None = Field(default=None, ge=0, le=100)
    mentality: TacticalStyle | None = None
    set_piece_emphasis: int | None = Field(default=None, ge=0, le=100)
    player_instructions: dict[str, Any] | None = None
    game_state_adjustments: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_adjustments(self) -> MatchTacticalAdjustmentInput:
        if self.formation is not None:
            _validate_formation_string(self.formation, allowed_outfield_totals=(9, 10))
        return self


class MatchSubstitutionRequestInput(CommonSchema):
    outgoing_player_id: str = Field(min_length=1)
    incoming_player_id: str = Field(min_length=1)
    urgency: str = Field(default="normal", min_length=3, max_length=16)
    reason: str | None = Field(default=None, max_length=64)


class MatchTacticalChangeInput(CommonSchema):
    change_id: str | None = None
    team_id: str = Field(min_length=1)
    requested_minute: int = Field(ge=0, le=120)
    requested_second: int = Field(default=0, ge=0, le=59)
    urgency: str = Field(default="normal", min_length=3, max_length=16)
    adjustment: MatchTacticalAdjustmentInput | None = None
    substitution: MatchSubstitutionRequestInput | None = None
    notes: str | None = Field(default=None, max_length=140)

    @model_validator(mode="after")
    def validate_change(self) -> MatchTacticalChangeInput:
        if self.adjustment is None and self.substitution is None:
            raise ValueError("Tactical changes require at least an adjustment or a substitution request")
        return self


class MatchSimulationRequest(CommonSchema):
    match_id: str = Field(min_length=1)
    seed: int | None = Field(default=None, ge=0)
    kickoff_at: datetime | None = None
    competition: MatchCompetitionContextInput = Field(default_factory=MatchCompetitionContextInput)
    home_team: MatchTeamInput
    away_team: MatchTeamInput
    tactical_changes: list[MatchTacticalChangeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_match(self) -> MatchSimulationRequest:
        if self.home_team.team_id == self.away_team.team_id:
            raise ValueError("Home and away teams must be different")
        combined_player_ids = {
            player.player_id
            for player in [*self.home_team.starters, *self.home_team.bench, *self.away_team.starters, *self.away_team.bench]
        }
        expected_count = len(self.home_team.starters) + len(self.home_team.bench) + len(self.away_team.starters) + len(self.away_team.bench)
        if len(combined_player_ids) != expected_count:
            raise ValueError("Player IDs must be unique across both squads")
        return self


class MatchPlayerReferenceView(CommonSchema):
    player_id: str
    player_name: str


class MatchTeamStrengthView(CommonSchema):
    overall: float
    attack: float
    midfield: float
    defense: float
    goalkeeping: float
    depth: float
    discipline: float
    fitness: float
    chemistry: float
    tactical_cohesion: float
    recent_form: float
    morale: float
    motivation: float
    fatigue_load: float
    coach_quality: float
    tactical_quality: float
    adaptability: float
    upset_resistance: float
    upset_punch: float


class MatchBadgeVisualView(CommonSchema):
    badge_url: str | None = None
    shape: str
    initials: str
    primary_color: str
    secondary_color: str
    accent_color: str


class MatchKitVisualView(CommonSchema):
    kit_type: str
    primary_color: str
    secondary_color: str
    accent_color: str
    shorts_color: str
    socks_color: str
    pattern_type: str
    collar_style: str
    sleeve_style: str
    badge_placement: str
    front_text: str | None = None


class MatchPlayerVisualView(CommonSchema):
    player_id: str
    display_name: str
    shirt_name: str
    shirt_number: int | None = Field(default=None, ge=1, le=99)
    role: PlayerRole


class MatchTeamVisualIdentityView(CommonSchema):
    team_id: str
    team_name: str
    short_club_code: str
    badge: MatchBadgeVisualView
    selected_kit: MatchKitVisualView
    alternate_kit: MatchKitVisualView
    third_kit: MatchKitVisualView | None = None
    goalkeeper_kit: MatchKitVisualView
    player_visuals: list[MatchPlayerVisualView] = Field(default_factory=list)
    clash_adjusted: bool = False


class MatchVisualIdentityView(CommonSchema):
    home_team: MatchTeamVisualIdentityView
    away_team: MatchTeamVisualIdentityView
    clash_resolved: bool = False


class MatchEventView(CommonSchema):
    event_id: str
    sequence: int
    event_type: MatchEventType
    minute: int = Field(ge=0, le=120)
    added_time: int = Field(default=0, ge=0, le=15)
    presentation_second: int = Field(ge=0)
    clock_label: str
    team_id: str | None = None
    team_name: str | None = None
    primary_player: MatchPlayerReferenceView | None = None
    secondary_player: MatchPlayerReferenceView | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    commentary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayEventLogEntryView(CommonSchema):
    sequence: int
    event_type: MatchEventType
    minute: int = Field(ge=0, le=120)
    added_time: int = Field(default=0, ge=0, le=15)
    team_id: str | None = None
    team_name: str | None = None
    player_id: str | None = None
    related_player_id: str | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)


class PenaltyAttemptView(CommonSchema):
    order: int = Field(ge=1)
    team_id: str
    team_name: str
    taker: MatchPlayerReferenceView
    goalkeeper: MatchPlayerReferenceView | None = None
    scored: bool
    home_penalties: int = Field(ge=0)
    away_penalties: int = Field(ge=0)


class PenaltyShootoutView(CommonSchema):
    winner_team_id: str
    winner_team_name: str
    home_penalties: int = Field(ge=0)
    away_penalties: int = Field(ge=0)
    attempts: list[PenaltyAttemptView] = Field(default_factory=list)


class MatchTeamStatsView(CommonSchema):
    team_id: str
    team_name: str
    started_formation: str
    current_formation: str
    goals: int = Field(ge=0)
    shots: int = Field(ge=0)
    shots_on_target: int = Field(ge=0)
    saves: int = Field(ge=0)
    missed_chances: int = Field(ge=0)
    yellow_cards: int = Field(ge=0)
    red_cards: int = Field(ge=0)
    injuries: int = Field(ge=0)
    substitutions: int = Field(ge=0)
    possession: int = Field(ge=0, le=100)
    big_chances: int = Field(ge=0)
    woodwork: int = Field(ge=0)
    tactical_swings: int = Field(ge=0)
    strength: MatchTeamStrengthView


class MatchPlayerStatsView(CommonSchema):
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    role: PlayerRole
    started: bool
    minutes_played: int = Field(ge=0, le=90)
    goals: int = Field(ge=0)
    assists: int = Field(ge=0)
    saves: int = Field(ge=0)
    missed_chances: int = Field(ge=0)
    yellow_cards: int = Field(ge=0)
    red_card: bool
    injured: bool
    substituted_in_minute: int | None = Field(default=None, ge=0, le=90)
    substituted_out_minute: int | None = Field(default=None, ge=0, le=90)




class MatchPlayerRatingView(CommonSchema):
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    rating: float = Field(ge=0, le=10)
    summary: str | None = None


class MatchMomentumPointView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    value: float


class MatchHeatmapView(CommonSchema):
    zones: list[int] = Field(default_factory=list, min_length=9, max_length=9)


class MatchPassMapEdgeView(CommonSchema):
    source_zone: int = Field(ge=0, le=8)
    target_zone: int = Field(ge=0, le=8)
    count: int = Field(ge=0)


class MatchHalftimeAnalyticsView(CommonSchema):
    duration_seconds: int = Field(ge=0)
    home_possession: int = Field(ge=0, le=100)
    away_possession: int = Field(ge=0, le=100)
    home_shots: int = Field(ge=0)
    away_shots: int = Field(ge=0)
    home_shots_on_target: int = Field(ge=0)
    away_shots_on_target: int = Field(ge=0)
    expected_goals_home: float = Field(ge=0)
    expected_goals_away: float = Field(ge=0)
    home_heatmap: MatchHeatmapView | None = None
    away_heatmap: MatchHeatmapView | None = None
    home_pass_map: list[MatchPassMapEdgeView] = Field(default_factory=list)
    away_pass_map: list[MatchPassMapEdgeView] = Field(default_factory=list)
    player_ratings: list[MatchPlayerRatingView] = Field(default_factory=list)
    home_stamina: float = Field(ge=0, le=100)
    away_stamina: float = Field(ge=0, le=100)
    home_formation: str
    away_formation: str
    momentum_graph: list[MatchMomentumPointView] = Field(default_factory=list)
    cards_incidents: list[str] = Field(default_factory=list)
    tactical_suggestions: list[str] = Field(default_factory=list)


class MatchKeyMomentView(CommonSchema):
    event_id: str
    event_type: MatchEventType
    start_second: int = Field(ge=0)
    end_second: int = Field(ge=0)
    importance: int = Field(default=1, ge=1, le=5)
    team_name: str | None = None


class MatchHighlightAccessView(CommonSchema):
    expires_after_seconds: int | None = Field(default=None, ge=0)
    archive_mode: bool = False
    watermark_required: bool = True
    signed_url_required: bool = True
    audit_log_required: bool = True
    rate_limit_per_minute: int = Field(default=6, ge=1, le=120)
    policy_checks: list[str] = Field(default_factory=list)


class MatchSpectatorPackageView(CommonSchema):
    modes: list[MatchSpectatorMode] = Field(default_factory=list)
    free_mode: MatchSpectatorMode = MatchSpectatorMode.FREE_2D_COMMENTARY
    paid_mode: MatchSpectatorMode = MatchSpectatorMode.PAID_LIVE_KEY_MOMENT_VIDEO
    can_pause: bool = False
    continuous_stream_available: bool = False
    key_moment_delivery: str = "event_triggered"


class MatchSceneAssemblyContractView(CommonSchema):
    scene_version: str = "v1"
    enabled_scenes: list[str] = Field(default_factory=list)
    replay_angle_set: str = "standard"
    crowd_profile: str = "regular"
    branded_backdrop: bool = False


class MatchBroadcastPresentationView(CommonSchema):
    overlay_style: str = "gtex_clean"
    scoreboard_style: str = "compact"
    commentary_style: str = "tactical"
    finals_package: bool = False
    atmosphere_profile: str = "standard"


class MatchReplayDownloadContractView(CommonSchema):
    signed_url_required: bool = True
    watermark_required: bool = True
    audit_log_required: bool = True
    rate_limit_per_minute: int = Field(default=6, ge=1, le=120)
    policy_checks: list[str] = Field(default_factory=list)
    signed_url_hook: str = "replay.sign_url"
    watermark_hook: str = "replay.apply_watermark"
    audit_log_hook: str = "replay.audit_log"


class MatchPerformanceSyncView(CommonSchema):
    tick_rate_hz: int = Field(default=20, ge=1, le=60)
    max_latency_ms: int = Field(default=320, ge=50, le=2000)
    checkpoint_interval_seconds: int = Field(default=15, ge=5, le=60)
    deterministic_seed: int = Field(ge=0)


class MatchTacticalChangeLogView(CommonSchema):
    change_id: str
    team_id: str
    team_name: str | None = None
    requested_minute: int = Field(ge=0, le=120)
    requested_second: int = Field(default=0, ge=0, le=59)
    applied_minute: int = Field(ge=0, le=120)
    applied_second: int = Field(default=0, ge=0, le=59)
    change_type: str
    urgency: str = "normal"
    changes: dict[str, Any] = Field(default_factory=dict)


class MatchSubstitutionLogView(CommonSchema):
    team_id: str
    team_name: str | None = None
    outgoing_player_id: str
    incoming_player_id: str
    requested_minute: int = Field(ge=0, le=120)
    applied_minute: int = Field(ge=0, le=120)
    reason: str | None = None
    urgency: str | None = None


class MatchCriticalSnapshotView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    event_type: MatchEventType
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    home_formation: str
    away_formation: str
    home_momentum: float
    away_momentum: float


class MatchHighlightClipView(CommonSchema):
    title: str
    start_second: int = Field(ge=0)
    end_second: int = Field(ge=0)
    importance: int = Field(default=1, ge=1, le=5)
    event_type: MatchEventType
    event_id: str | None = None
    team_name: str | None = None


class MatchInjuryReportView(CommonSchema):
    minute: int = Field(ge=0, le=120)
    team_name: str
    player_name: str
    severity: str = Field(default='monitor')
    tactical_impact: str


class MatchFinalSummaryView(CommonSchema):
    match_id: str
    seed: int = Field(ge=0)
    win_probability_home: int = Field(default=0, ge=0, le=100)
    win_probability_draw: int = Field(default=0, ge=0, le=100)
    win_probability_away: int = Field(default=0, ge=0, le=100)
    expected_goals_home: float = Field(default=0.0, ge=0)
    expected_goals_away: float = Field(default=0.0, ge=0)
    key_highlights: list[str] = Field(default_factory=list)
    highlight_package: list[MatchHighlightClipView] = Field(default_factory=list)
    highlight_profile: MatchHighlightProfile = MatchHighlightProfile.NORMAL
    highlight_runtime_seconds: int = Field(default=0, ge=0)
    highlight_access: MatchHighlightAccessView | None = None
    manager_influence_notes: list[str] = Field(default_factory=list)
    injury_report: list[MatchInjuryReportView] = Field(default_factory=list)
    upset_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    upset_reason_codes: list[str] = Field(default_factory=list)
    home_advantage_note: str = ""
    manager_influence_score_home: float = 0.0
    manager_influence_score_away: float = 0.0
    tactical_battle_summary: str = ""
    form_motivation_summary: str = ""
    momentum_swings: list[str] = Field(default_factory=list)
    turning_points: list[str] = Field(default_factory=list)
    key_matchups: list[str] = Field(default_factory=list)
    tactical_impact_notes: list[str] = Field(default_factory=list)
    status: MatchStatus
    competition_type: MatchCompetitionType
    stage: str
    is_final: bool
    requires_winner: bool
    winner_team_id: str | None = None
    winner_team_name: str | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    decided_by_penalties: bool
    home_penalty_score: int | None = Field(default=None, ge=0)
    away_penalty_score: int | None = Field(default=None, ge=0)
    upset: bool
    presentation_duration_seconds: int = Field(ge=0)
    summary_line: str
    home_stats: MatchTeamStatsView
    away_stats: MatchTeamStatsView
    player_stats: list[MatchPlayerStatsView] = Field(default_factory=list)
    shootout: PenaltyShootoutView | None = None


class MatchEventTimelineView(CommonSchema):
    match_id: str
    status: MatchStatus
    presentation_duration_seconds: int = Field(ge=0)
    events: list[MatchEventView] = Field(default_factory=list)


class MatchLiveFeedEventView(CommonSchema):
    event_id: str
    minute: int = Field(ge=0)
    event_type: str
    team_id: str | None = None
    team_name: str | None = None
    player_name: str | None = None
    secondary_player_name: str | None = None
    description: str | None = None
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    is_penalty: bool = False


class MatchMediaAvailabilityView(CommonSchema):
    halftime_analytics_available: bool = False
    key_moments_available: bool = False
    highlights_available: bool = False
    replay_available: bool = False
    archive_available: bool = False
    download_available: bool = False


class MatchLiveFeedView(CommonSchema):
    match_id: str
    home_team_name: str
    away_team_name: str
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    status: MatchStatus
    minute: int | None = Field(default=None, ge=0)
    phase: str = Field(min_length=1)
    timeline_events: list[MatchLiveFeedEventView] = Field(default_factory=list)
    availability: MatchMediaAvailabilityView


class MatchHighlightItemView(CommonSchema):
    highlight_id: str
    title: str
    label: str | None = None
    minute: int = Field(ge=0)
    event_type: str
    team_name: str | None = None
    player_name: str | None = None
    access_state: str = "available"
    archive_available: bool = False
    download_available: bool = False


class MatchHighlightListView(CommonSchema):
    match_id: str
    highlights: list[MatchHighlightItemView] = Field(default_factory=list)
    replay_available: bool = False
    archive_available: bool = False
    download_available: bool = False


class MatchReplayPayloadView(CommonSchema):
    match_id: str
    seed: int = Field(ge=0)
    win_probability_home: int = Field(default=0, ge=0, le=100)
    win_probability_draw: int = Field(default=0, ge=0, le=100)
    win_probability_away: int = Field(default=0, ge=0, le=100)
    expected_goals_home: float = Field(default=0.0, ge=0)
    expected_goals_away: float = Field(default=0.0, ge=0)
    key_highlights: list[str] = Field(default_factory=list)
    highlight_package: list[MatchHighlightClipView] = Field(default_factory=list)
    highlight_profile: MatchHighlightProfile = MatchHighlightProfile.NORMAL
    highlight_runtime_seconds: int = Field(default=0, ge=0)
    highlight_access: MatchHighlightAccessView | None = None
    key_moments: list[MatchKeyMomentView] = Field(default_factory=list)
    manager_influence_notes: list[str] = Field(default_factory=list)
    injury_report: list[MatchInjuryReportView] = Field(default_factory=list)
    halftime_analytics: MatchHalftimeAnalyticsView | None = None
    spectator_package: MatchSpectatorPackageView | None = None
    scene_assembly: MatchSceneAssemblyContractView | None = None
    broadcast_presentation: MatchBroadcastPresentationView | None = None
    replay_download: MatchReplayDownloadContractView | None = None
    sync_contract: MatchPerformanceSyncView | None = None
    tactical_change_log: list[MatchTacticalChangeLogView] = Field(default_factory=list)
    substitution_log: list[MatchSubstitutionLogView] = Field(default_factory=list)
    critical_snapshots: list[MatchCriticalSnapshotView] = Field(default_factory=list)
    visual_identity: MatchVisualIdentityView | None = None
    status: MatchStatus
    summary: MatchFinalSummaryView
    timeline: MatchEventTimelineView
    replay_log: list[ReplayEventLogEntryView] = Field(default_factory=list)
