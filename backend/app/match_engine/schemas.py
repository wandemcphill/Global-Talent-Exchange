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

    @model_validator(mode="after")
    def validate_tactics(self) -> TeamTacticalPlanInput:
        _validate_formation_string(self.red_card_fallback_formation, allowed_outfield_totals=(9, 10))
        if tuple(sorted(set(self.substitution_windows))) != self.substitution_windows:
            raise ValueError("Substitution windows must be unique and sorted in ascending order")
        if any(window < 46 or window > 89 for window in self.substitution_windows):
            raise ValueError("Substitution windows must be between minutes 46 and 89")
        return self


class MatchTeamInput(CommonSchema):
    team_id: str = Field(min_length=1)
    team_name: str = Field(min_length=1)
    formation: str = Field(default="4-3-3", min_length=5)
    tactics: TeamTacticalPlanInput = Field(default_factory=TeamTacticalPlanInput)
    manager_profile: dict[str, Any] | None = None
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
    status: MatchStatus
    summary: MatchFinalSummaryView
    timeline: MatchEventTimelineView
    replay_log: list[ReplayEventLogEntryView] = Field(default_factory=list)
