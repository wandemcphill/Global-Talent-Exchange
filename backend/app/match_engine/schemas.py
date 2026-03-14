from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from backend.app.common.enums.match_status import MatchStatus
from backend.app.common.schemas.base import CommonSchema
from backend.app.match_engine.simulation.models import MatchCompetitionType, MatchEventType, PlayerRole, TacticalStyle


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
    badge_url: str | None = Field(default=None, max_length=255)
    badge_shape: str = Field(default="shield", min_length=3, max_length=24)
    badge_initials: str = Field(default="FC", min_length=1, max_length=6)
    badge_primary_color: str = Field(default="#123C73", min_length=4, max_length=16)
    badge_secondary_color: str = Field(default="#F5F7FA", min_length=4, max_length=16)
    badge_accent_color: str = Field(default="#E2A400", min_length=4, max_length=16)
    home_kit: MatchKitIdentityInput | None = None
    away_kit: MatchKitIdentityInput | None = None
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


class MatchSimulationRequest(CommonSchema):
    match_id: str = Field(min_length=1)
    seed: int | None = Field(default=None, ge=0)
    kickoff_at: datetime | None = None
    competition: MatchCompetitionContextInput = Field(default_factory=MatchCompetitionContextInput)
    home_team: MatchTeamInput
    away_team: MatchTeamInput

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




class MatchHighlightClipView(CommonSchema):
    title: str
    start_second: int = Field(ge=0)
    end_second: int = Field(ge=0)
    importance: int = Field(default=1, ge=1, le=5)
    event_type: MatchEventType
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
    manager_influence_notes: list[str] = Field(default_factory=list)
    injury_report: list[MatchInjuryReportView] = Field(default_factory=list)
    visual_identity: MatchVisualIdentityView | None = None
    status: MatchStatus
    summary: MatchFinalSummaryView
    timeline: MatchEventTimelineView
    replay_log: list[ReplayEventLogEntryView] = Field(default_factory=list)
