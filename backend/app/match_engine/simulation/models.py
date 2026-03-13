from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from backend.app.common.enums.match_status import MatchStatus


class MatchCompetitionType(StrEnum):
    LEAGUE = "league"
    CUP = "cup"


class PlayerRole(StrEnum):
    GOALKEEPER = "GK"
    DEFENDER = "DF"
    MIDFIELDER = "MF"
    FORWARD = "FW"


class TacticalStyle(StrEnum):
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    ATTACKING = "attacking"


class MatchEventType(StrEnum):
    KICKOFF = "kickoff"
    MISSED_CHANCE = "missed_chance"
    SAVE = "save"
    GOAL = "goal"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    INJURY = "injury"
    SUBSTITUTION = "substitution"
    HALFTIME = "halftime"
    FULLTIME = "fulltime"
    PENALTY_GOAL = "penalty_goal"
    PENALTY_MISS = "penalty_miss"


@dataclass(frozen=True, slots=True)
class InternalPlayer:
    player_id: str
    player_name: str
    role: PlayerRole
    overall: int
    finishing: int
    creativity: int
    defending: int
    goalkeeping: int
    discipline: int
    fitness: int

    def attacking_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -18.0,
            PlayerRole.DEFENDER: -4.0,
            PlayerRole.MIDFIELDER: 2.0,
            PlayerRole.FORWARD: 8.0,
        }[self.role]
        return max(5.0, (self.overall * 0.30) + (self.finishing * 0.45) + (self.creativity * 0.25) + role_adjustment)

    def control_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -20.0,
            PlayerRole.DEFENDER: -2.0,
            PlayerRole.MIDFIELDER: 8.0,
            PlayerRole.FORWARD: 1.0,
        }[self.role]
        return max(5.0, (self.overall * 0.35) + (self.creativity * 0.40) + (self.fitness * 0.15) + (self.discipline * 0.10) + role_adjustment)

    def defensive_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -8.0,
            PlayerRole.DEFENDER: 8.0,
            PlayerRole.MIDFIELDER: 1.0,
            PlayerRole.FORWARD: -6.0,
        }[self.role]
        return max(5.0, (self.overall * 0.25) + (self.defending * 0.55) + (self.discipline * 0.10) + (self.fitness * 0.10) + role_adjustment)

    def goalkeeping_value(self) -> float:
        return max(5.0, (self.goalkeeping * 0.80) + (self.overall * 0.20))

    def penalty_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -12.0,
            PlayerRole.DEFENDER: -2.0,
            PlayerRole.MIDFIELDER: 4.0,
            PlayerRole.FORWARD: 7.0,
        }[self.role]
        return max(5.0, (self.overall * 0.20) + (self.finishing * 0.50) + (self.creativity * 0.20) + (self.discipline * 0.10) + role_adjustment)


@dataclass(frozen=True, slots=True)
class TacticalPlan:
    style: TacticalStyle
    pressing: int
    tempo: int
    aggression: int
    substitution_windows: tuple[int, ...]
    red_card_fallback_formation: str
    injury_auto_substitution: bool
    yellow_card_substitution_minute: int
    yellow_card_replacement_roles: tuple[PlayerRole, ...]
    max_substitutions: int


@dataclass(frozen=True, slots=True)
class MatchTeamProfile:
    team_id: str
    team_name: str
    formation: str
    tactics: TacticalPlan
    manager_profile: dict[str, object] | None = None
    starters: tuple[InternalPlayer, ...] = ()
    bench: tuple[InternalPlayer, ...] = ()


@dataclass(frozen=True, slots=True)
class TeamStrengthSnapshot:
    overall: float
    attack: float
    midfield: float
    defense: float
    goalkeeping: float
    depth: float
    discipline: float
    fitness: float


@dataclass(slots=True)
class PlayerMatchStats:
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    role: PlayerRole
    started: bool
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    saves: int = 0
    missed_chances: int = 0
    yellow_cards: int = 0
    red_card: bool = False
    injured: bool = False
    substituted_in_minute: int | None = None
    substituted_out_minute: int | None = None

    def is_notable(self) -> bool:
        return any(
            (
                self.goals,
                self.assists,
                self.saves,
                self.missed_chances,
                self.yellow_cards,
                self.red_card,
                self.injured,
                self.substituted_in_minute is not None,
                self.substituted_out_minute is not None,
            )
        )


@dataclass(slots=True)
class TeamMatchStats:
    team_id: str
    team_name: str
    started_formation: str
    current_formation: str
    goals: int = 0
    shots: int = 0
    shots_on_target: int = 0
    saves: int = 0
    missed_chances: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    injuries: int = 0
    substitutions: int = 0
    possession: int = 50


@dataclass(frozen=True, slots=True)
class MatchEvent:
    event_id: str
    sequence: int
    event_type: MatchEventType
    minute: int
    added_time: int
    home_score: int
    away_score: int
    team_id: str | None = None
    team_name: str | None = None
    primary_player_id: str | None = None
    primary_player_name: str | None = None
    secondary_player_id: str | None = None
    secondary_player_name: str | None = None
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PenaltyAttempt:
    order: int
    team_id: str
    team_name: str
    taker_id: str
    taker_name: str
    goalkeeper_id: str | None
    goalkeeper_name: str | None
    scored: bool
    home_penalties: int
    away_penalties: int


@dataclass(frozen=True, slots=True)
class PenaltyShootout:
    winner_team_id: str
    winner_team_name: str
    home_penalties: int
    away_penalties: int
    attempts: tuple[PenaltyAttempt, ...]


@dataclass(frozen=True, slots=True)
class SimulationResult:
    match_id: str
    seed: int
    status: MatchStatus
    competition_type: MatchCompetitionType
    stage: str
    is_final: bool
    requires_winner: bool
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    winner_team_id: str | None
    winner_team_name: str | None
    home_score: int
    away_score: int
    decided_by_penalties: bool
    home_penalty_score: int | None
    away_penalty_score: int | None
    upset: bool
    summary_line: str
    home_strength: TeamStrengthSnapshot
    away_strength: TeamStrengthSnapshot
    home_stats: TeamMatchStats
    away_stats: TeamMatchStats
    player_stats: tuple[PlayerMatchStats, ...]
    events: tuple[MatchEvent, ...]
    shootout: PenaltyShootout | None = None


@dataclass(slots=True)
class TeamRuntimeState:
    team_id: str
    team_name: str
    is_home: bool
    starting_formation: str
    current_formation: str
    starting_shape: tuple[int, ...]
    current_shape: tuple[int, ...]
    tactics: TacticalPlan
    strength: TeamStrengthSnapshot
    players_by_id: dict[str, InternalPlayer]
    active_player_ids: list[str]
    bench_player_ids: list[str]
    stats: TeamMatchStats
    yellow_carded_ids: set[str] = field(default_factory=set)
    red_carded_ids: set[str] = field(default_factory=set)
    injured_ids: set[str] = field(default_factory=set)
    substitutions_used: int = 0
    shape_attack_adjustment: float = 0.0
    shape_defense_adjustment: float = 0.0

    def substitutions_remaining(self) -> int:
        return max(self.tactics.max_substitutions - self.substitutions_used, 0)

    def active_players(self, *, role: PlayerRole | None = None, include_goalkeeper: bool = True) -> list[InternalPlayer]:
        players = [self.players_by_id[player_id] for player_id in self.active_player_ids]
        if not include_goalkeeper:
            players = [player for player in players if player.role is not PlayerRole.GOALKEEPER]
        if role is not None:
            players = [player for player in players if player.role is role]
        return players

    def active_outfielders(self) -> list[InternalPlayer]:
        return self.active_players(include_goalkeeper=False)

    def available_bench(self, roles: tuple[PlayerRole, ...] | None = None) -> list[InternalPlayer]:
        players = [self.players_by_id[player_id] for player_id in self.bench_player_ids]
        if roles is None:
            return players
        return [player for player in players if player.role in roles]

    def goalkeeper(self) -> InternalPlayer | None:
        goalkeepers = self.active_players(role=PlayerRole.GOALKEEPER)
        return goalkeepers[0] if goalkeepers else None

    def remove_active_player(self, player_id: str) -> None:
        if player_id in self.active_player_ids:
            self.active_player_ids.remove(player_id)

    def add_active_player(self, player_id: str) -> None:
        if player_id not in self.active_player_ids:
            self.active_player_ids.append(player_id)
