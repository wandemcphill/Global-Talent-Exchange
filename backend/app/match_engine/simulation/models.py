from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

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


class MatchSpectatorMode(StrEnum):
    FREE_2D_COMMENTARY = "free_2d_commentary"
    PAID_LIVE_KEY_MOMENT_VIDEO = "paid_live_key_moment_video"


class MatchHighlightProfile(StrEnum):
    BORING_DRAW = "boring_draw"
    NORMAL = "normal"
    HIGH_DRAMA = "high_drama"
    ELITE_FINAL = "elite_final"


class MatchEventType(StrEnum):
    KICKOFF = "kickoff"
    POSSESSION_SWING = "possession_swing"
    DANGEROUS_ATTACK = "dangerous_attack"
    SHOT = "shot"
    SHOT_ON_TARGET = "shot_on_target"
    MISSED_CHANCE = "missed_chance"
    MISSED_BIG_CHANCE = "missed_big_chance"
    SAVE = "save"
    GOALKEEPER_SAVE = "goalkeeper_save"
    GOAL = "goal"
    WOODWORK = "woodwork"
    DOUBLE_SAVE = "double_save"
    COUNTER_ATTACK = "counter_attack"
    TACTICAL_FOUL = "tactical_foul"
    PENALTY_AWARDED = "penalty_awarded"
    PENALTY_SCORED = "penalty_scored"
    PENALTY_MISSED = "penalty_missed"
    SET_PIECE_CHANCE = "set_piece_chance"
    DEFENSIVE_ERROR = "defensive_error"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    INJURY = "injury"
    FATIGUE_EVENT = "fatigue_event"
    SUBSTITUTION = "substitution"
    SUBSTITUTION_IMPACT = "substitution_impact"
    TACTICAL_SWING = "tactical_swing"
    TACTICAL_CHANGE = "tactical_change"
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
    shirt_number: int | None = None
    display_name: str | None = None
    position_archetype: str | None = None
    pace: int = 50
    composure: int = 50
    decision_making: int = 50
    positioning: int = 50
    off_ball_movement: int = 50
    aerial_ability: int = 50
    technique: int = 50
    stamina_curve: int = 50
    consistency: int = 50
    clutch_factor: int = 50
    big_match_temperament: int = 50
    recent_form: int = 50
    morale: int = 60
    motivation: int = 60
    fatigue_load: int = 35
    injury_risk: int = 20
    leadership: int = 50

    def shirt_name(self) -> str:
        if self.display_name:
            return self.display_name
        chunks = [chunk for chunk in self.player_name.split(" ") if chunk]
        return chunks[-1] if chunks else self.player_name

    def attacking_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -20.0,
            PlayerRole.DEFENDER: -6.0,
            PlayerRole.MIDFIELDER: 1.5,
            PlayerRole.FORWARD: 9.0,
        }[self.role]
        return max(
            5.0,
            (self.overall * 0.18)
            + (self.finishing * 0.24)
            + (self.composure * 0.14)
            + (self.off_ball_movement * 0.14)
            + (self.technique * 0.10)
            + (self.pace * 0.08)
            + (self.creativity * 0.07)
            + (self.recent_form * 0.05)
            + role_adjustment,
        )

    def control_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -22.0,
            PlayerRole.DEFENDER: -1.5,
            PlayerRole.MIDFIELDER: 8.5,
            PlayerRole.FORWARD: 0.5,
        }[self.role]
        return max(
            5.0,
            (self.overall * 0.17)
            + (self.creativity * 0.24)
            + (self.decision_making * 0.17)
            + (self.technique * 0.11)
            + (self.positioning * 0.09)
            + (self.consistency * 0.08)
            + (self.fitness * 0.08)
            + (self.recent_form * 0.06)
            + role_adjustment,
        )

    def defensive_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -9.0,
            PlayerRole.DEFENDER: 9.0,
            PlayerRole.MIDFIELDER: 1.5,
            PlayerRole.FORWARD: -7.0,
        }[self.role]
        return max(
            5.0,
            (self.overall * 0.14)
            + (self.defending * 0.26)
            + (self.positioning * 0.17)
            + (self.decision_making * 0.12)
            + (self.aerial_ability * 0.11)
            + (self.pace * 0.06)
            + (self.discipline * 0.07)
            + (self.consistency * 0.05)
            + role_adjustment,
        )

    def goalkeeping_value(self) -> float:
        return max(
            5.0,
            (self.goalkeeping * 0.58)
            + (self.composure * 0.10)
            + (self.decision_making * 0.08)
            + (self.aerial_ability * 0.08)
            + (self.technique * 0.06)
            + (self.positioning * 0.05)
            + (self.overall * 0.05),
        )

    def penalty_value(self) -> float:
        role_adjustment = {
            PlayerRole.GOALKEEPER: -12.0,
            PlayerRole.DEFENDER: -2.0,
            PlayerRole.MIDFIELDER: 4.0,
            PlayerRole.FORWARD: 7.0,
        }[self.role]
        return max(
            5.0,
            (self.finishing * 0.28)
            + (self.composure * 0.22)
            + (self.technique * 0.14)
            + (self.clutch_factor * 0.14)
            + (self.big_match_temperament * 0.10)
            + (self.discipline * 0.06)
            + (self.overall * 0.06)
            + role_adjustment,
        )

    def pressing_value(self) -> float:
        return max(
            5.0,
            (self.fitness * 0.28)
            + (self.pace * 0.19)
            + (self.decision_making * 0.14)
            + (self.consistency * 0.12)
            + (self.motivation * 0.10)
            + (self.defending * 0.09)
            + (self.positioning * 0.08),
        )

    def duel_value(self) -> float:
        return max(
            5.0,
            (self.overall * 0.16)
            + (self.aerial_ability * 0.20)
            + (self.positioning * 0.16)
            + (self.composure * 0.12)
            + (self.pace * 0.10)
            + (self.strength_proxy() * 0.18)
            + (self.motivation * 0.08),
        )

    def strength_proxy(self) -> float:
        return max(5.0, (self.overall * 0.45) + (self.fitness * 0.30) + (self.aerial_ability * 0.25))


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
    defensive_line: int = 50
    width: int = 50
    mentality: TacticalStyle = TacticalStyle.BALANCED
    set_piece_emphasis: int = 50
    player_instructions: dict[str, Any] | None = None
    game_state_adjustments: dict[str, Any] | None = None
    tactical_quality: int = 60
    adaptability: int = 60
    game_management: int = 60


@dataclass(frozen=True, slots=True)
class BadgeVisualIdentity:
    badge_url: str | None
    shape: str
    initials: str
    primary_color: str
    secondary_color: str
    accent_color: str


@dataclass(frozen=True, slots=True)
class KitVisualIdentity:
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


@dataclass(frozen=True, slots=True)
class PlayerVisualIdentity:
    player_id: str
    display_name: str
    shirt_name: str
    shirt_number: int | None
    role: PlayerRole


@dataclass(frozen=True, slots=True)
class TeamVisualIdentity:
    team_id: str
    team_name: str
    short_club_code: str
    badge: BadgeVisualIdentity
    selected_kit: KitVisualIdentity
    alternate_kit: KitVisualIdentity
    third_kit: KitVisualIdentity | None = None
    goalkeeper_kit: KitVisualIdentity
    player_visuals: tuple[PlayerVisualIdentity, ...] = ()
    clash_adjusted: bool = False


@dataclass(frozen=True, slots=True)
class MatchVisualIdentityPayload:
    home_team: TeamVisualIdentity
    away_team: TeamVisualIdentity
    clash_resolved: bool = False


@dataclass(frozen=True, slots=True)
class MatchTeamProfile:
    team_id: str
    team_name: str
    formation: str
    tactics: TacticalPlan
    manager_profile: dict[str, object] | None = None
    club_context: dict[str, Any] | None = None
    visual_identity: TeamVisualIdentity | None = None
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
    big_chances: int = 0
    woodwork: int = 0
    tactical_swings: int = 0


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
    metadata: dict[str, Any] = field(default_factory=dict)


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
    upset_probability: float
    upset_reason_codes: tuple[str, ...]
    home_advantage_note: str
    summary_line: str
    home_strength: TeamStrengthSnapshot
    away_strength: TeamStrengthSnapshot
    home_stats: TeamMatchStats
    away_stats: TeamMatchStats
    player_stats: tuple[PlayerMatchStats, ...]
    events: tuple[MatchEvent, ...]
    manager_influence_notes: tuple[str, ...]
    tactical_battle_summary: str
    form_motivation_summary: str
    momentum_swings: tuple[str, ...]
    turning_points: tuple[str, ...]
    key_matchups: tuple[str, ...]
    tactical_impact_notes: tuple[str, ...]
    visual_identity: MatchVisualIdentityPayload
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
    visual_identity: TeamVisualIdentity
    yellow_carded_ids: set[str] = field(default_factory=set)
    red_carded_ids: set[str] = field(default_factory=set)
    injured_ids: set[str] = field(default_factory=set)
    substitutions_used: int = 0
    shape_attack_adjustment: float = 0.0
    shape_defense_adjustment: float = 0.0
    dynamic_morale: float = 60.0
    dynamic_motivation: float = 60.0
    fatigue_level: float = 35.0
    momentum: float = 0.0
    live_upset_momentum: float = 0.0
    manager_influence_score: float = 0.0
    tactical_mismatch_edge: float = 0.0
    home_advantage_score: float = 0.0
    upset_potential: float = 0.0

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
