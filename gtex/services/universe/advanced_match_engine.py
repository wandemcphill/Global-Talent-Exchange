from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Any, Mapping, Sequence

from services.universe.generator import GeneratedClub, GeneratedPlayer, UniverseGenerator
from services.universe.scheduler import Fixture
from services.universe.storyline import StorylineBundle, build_content_brief, inject_storylines


_STYLE_TEMPO = {
    "attacking": 1.07,
    "defensive": 0.92,
    "balanced": 1.00,
    "counter": 1.03,
    "pressing": 1.09,
}
_STYLE_POSSESSION = {
    "attacking": 1.01,
    "defensive": 0.95,
    "balanced": 1.00,
    "counter": 0.94,
    "pressing": 1.00,
}
_STYLE_PRESS = {
    "attacking": 0.98,
    "defensive": 0.94,
    "balanced": 0.97,
    "counter": 0.96,
    "pressing": 1.08,
}
_STYLE_FORMATIONS = {
    "attacking": ("GK", "RB", "CB", "CB", "LB", "CM", "AM", "CM", "RW", "LW", "ST"),
    "defensive": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "DM", "RW", "LW", "ST"),
    "balanced": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST"),
    "counter": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "CM", "RW", "LW", "ST"),
    "pressing": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST"),
}
_POSITION_COMPATIBILITY = {
    "GK": ("GK",),
    "RB": ("RB", "LB", "CB", "DM"),
    "LB": ("LB", "RB", "CB", "DM"),
    "CB": ("CB", "RB", "LB", "DM"),
    "DM": ("DM", "CM", "CB"),
    "CM": ("CM", "DM", "AM", "RW", "LW"),
    "AM": ("AM", "CM", "RW", "LW", "ST"),
    "RW": ("RW", "LW", "AM", "ST", "CM"),
    "LW": ("LW", "RW", "AM", "ST", "CM"),
    "ST": ("ST", "AM", "RW", "LW"),
}
_SHOTTER_POSITION_WEIGHTS = {
    "ST": 28,
    "RW": 16,
    "LW": 16,
    "AM": 11,
    "CM": 6,
    "DM": 3,
    "CB": 2,
    "RB": 2,
    "LB": 2,
    "GK": 1,
}
_CREATOR_POSITION_WEIGHTS = {
    "AM": 18,
    "CM": 15,
    "RW": 13,
    "LW": 13,
    "DM": 8,
    "RB": 6,
    "LB": 6,
    "ST": 4,
    "CB": 2,
    "GK": 1,
}
_PASS_ROLE_WEIGHTS = {
    "GK": 0.60,
    "RB": 0.95,
    "LB": 0.95,
    "CB": 1.18,
    "DM": 1.25,
    "CM": 1.18,
    "AM": 0.96,
    "RW": 0.78,
    "LW": 0.78,
    "ST": 0.56,
}
_TACKLE_ROLE_WEIGHTS = {
    "GK": 0.06,
    "RB": 0.95,
    "LB": 0.95,
    "CB": 1.14,
    "DM": 1.22,
    "CM": 0.86,
    "AM": 0.34,
    "RW": 0.26,
    "LW": 0.26,
    "ST": 0.18,
}
_DEFENSIVE_POSITIONS = {"CB", "RB", "LB", "DM"}
_ATTACKING_POSITIONS = {"ST", "RW", "LW", "AM"}
_LINEUP_SIZE = 11


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _round_stat(value: float) -> float:
    return round(value, 2)


def _average(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _normalize_rating(value: float) -> float:
    return _clamp(value / 100.0, 0.40, 0.99)


def _stable_seed(*parts: object) -> int:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return int(digest, 16)


def _noise(rng: random.Random, *, factor: float, amplitude: float) -> float:
    return (rng.random() - 0.5) * 2.0 * factor * amplitude


def _position_label(position: str) -> str:
    return {
        "GK": "Goalkeeper",
        "RB": "Full-back",
        "LB": "Full-back",
        "CB": "Center-back",
        "DM": "Holding midfielder",
        "CM": "Midfielder",
        "AM": "Playmaker",
        "RW": "Winger",
        "LW": "Winger",
        "ST": "Forward",
    }.get(position, "Player")


def _fit_score(player: GeneratedPlayer, role: str) -> float:
    compatibility = _POSITION_COMPATIBILITY.get(role, (role,))
    try:
        penalty = compatibility.index(player.position) * 4.0
    except ValueError:
        penalty = 14.0
    return player.rating - penalty


def _pick_lineup(club: GeneratedClub) -> tuple[GeneratedPlayer, ...]:
    formation = _STYLE_FORMATIONS.get(club.style, _STYLE_FORMATIONS["balanced"])
    remaining = list(club.roster)
    lineup: list[GeneratedPlayer] = []
    for role in formation:
        best = max(remaining, key=lambda player, target=role: (_fit_score(player, target), player.potential, -player.age))
        lineup.append(best)
        remaining.remove(best)
    return tuple(lineup[:_LINEUP_SIZE])


def _weighted_choice(
    players: Sequence[GeneratedPlayer],
    rng: random.Random,
    *,
    weights_by_position: Mapping[str, int | float],
) -> GeneratedPlayer:
    weights = [max(1, int(player.rating + float(weights_by_position.get(player.position, 1)))) for player in players]
    return rng.choices(list(players), weights=weights, k=1)[0]


def _event_minute(match_second: int) -> int:
    return max(1, min(90, ((match_second - 1) // 60) + 1))


def _team_result_code(*, goals_for: int, goals_against: int) -> str:
    if goals_for > goals_against:
        return "W"
    if goals_for < goals_against:
        return "L"
    return "D"


def _form_momentum_from_symbols(symbols: Sequence[str]) -> float:
    if not symbols:
        return 0.0
    weights = [0.45, 0.75, 1.00, 1.20, 1.45]
    recent = [str(symbol).upper()[:1] for symbol in tuple(symbols)[-5:]]
    weighted_total = 0.0
    weighted_max = 0.0
    for index, symbol in enumerate(recent):
        weight = weights[-len(recent) + index]
        value = 1.0 if symbol == "W" else 0.0 if symbol == "D" else -1.0
        weighted_total += value * weight
        weighted_max += weight
    if weighted_max <= 0.0:
        return 0.0
    return _clamp(weighted_total / weighted_max, -1.0, 1.0)


@dataclass(frozen=True, slots=True)
class League:
    league_id: str
    name: str
    season: int
    clubs: tuple[GeneratedClub, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "league_id": self.league_id,
            "name": self.name,
            "season": self.season,
            "clubs": [club.as_dict() for club in self.clubs],
        }

    def club_map(self) -> dict[str, GeneratedClub]:
        return {club.club_id: club for club in self.clubs}


@dataclass(frozen=True, slots=True)
class TeamMatchInputs:
    chemistry: float = 0.65
    fatigue: float = 0.18
    form_last_five: tuple[str, ...] = ()
    form_momentum: float = 0.0

    def normalized(self) -> "TeamMatchInputs":
        symbols = tuple(str(symbol).upper()[:1] for symbol in self.form_last_five[-5:] if str(symbol).strip())
        momentum = self.form_momentum
        if symbols and abs(momentum) < 1e-9:
            momentum = _form_momentum_from_symbols(symbols)
        return TeamMatchInputs(
            chemistry=_clamp(self.chemistry, 0.20, 0.98),
            fatigue=_clamp(self.fatigue, 0.0, 0.95),
            form_last_five=symbols,
            form_momentum=_clamp(momentum, -1.0, 1.0),
        )

    def as_dict(self) -> dict[str, object]:
        normalized = self.normalized()
        return {
            "chemistry": _round_stat(normalized.chemistry),
            "fatigue": _round_stat(normalized.fatigue),
            "form_last_five": list(normalized.form_last_five),
            "form_momentum": _round_stat(normalized.form_momentum),
        }


@dataclass(frozen=True, slots=True)
class MatchSimulationSettings:
    randomness_factor: float = 0.18
    tick_seconds_min: int = 1
    tick_seconds_max: int = 5

    def normalized(self) -> "MatchSimulationSettings":
        minimum = max(1, min(self.tick_seconds_min, self.tick_seconds_max))
        maximum = max(minimum, self.tick_seconds_max)
        return MatchSimulationSettings(
            randomness_factor=_clamp(self.randomness_factor, 0.0, 1.0),
            tick_seconds_min=minimum,
            tick_seconds_max=maximum,
        )

    def as_dict(self) -> dict[str, object]:
        normalized = self.normalized()
        return {
            "randomness_factor": _round_stat(normalized.randomness_factor),
            "tick_seconds_min": normalized.tick_seconds_min,
            "tick_seconds_max": normalized.tick_seconds_max,
        }


@dataclass(frozen=True, slots=True)
class MatchTeamStats:
    possession_share: float
    possession_pct: float
    shots: int
    shots_on_target: int
    xg: float
    fouls: int

    def as_dict(self) -> dict[str, object]:
        return {
            "possession_share": _round_stat(self.possession_share),
            "possession_pct": _round_stat(self.possession_pct),
            "shots": self.shots,
            "shots_on_target": self.shots_on_target,
            "xg": _round_stat(self.xg),
            "fouls": self.fouls,
        }


@dataclass(frozen=True, slots=True)
class PlayerPerformance:
    player_id: str
    team_id: str
    team_name: str
    player_name: str
    position: str
    minutes: int
    rating: float
    goals: int
    assists: int
    shots: int
    shots_on_target: int
    xg: float
    key_passes: int
    passes_completed: int
    tackles_won: int
    fouls_committed: int
    yellow_cards: int
    red_card: bool
    saves: int
    clean_sheet: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "player_name": self.player_name,
            "position": self.position,
            "minutes": self.minutes,
            "rating": _round_stat(self.rating),
            "goals": self.goals,
            "assists": self.assists,
            "shots": self.shots,
            "shots_on_target": self.shots_on_target,
            "xg": _round_stat(self.xg),
            "key_passes": self.key_passes,
            "passes_completed": self.passes_completed,
            "tackles_won": self.tackles_won,
            "fouls_committed": self.fouls_committed,
            "yellow_cards": self.yellow_cards,
            "red_card": self.red_card,
            "saves": self.saves,
            "clean_sheet": self.clean_sheet,
        }


@dataclass(frozen=True, slots=True)
class MatchEvent:
    minute: int
    match_second: int
    team_id: str
    team_name: str
    player_name: str
    event_type: str
    outcome: str
    description: str
    secondary_player_name: str | None = None
    xg: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "minute": self.minute,
            "match_second": self.match_second,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "player_name": self.player_name,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "description": self.description,
            "secondary_player_name": self.secondary_player_name,
            "xg": _round_stat(self.xg),
        }


@dataclass(frozen=True, slots=True)
class MatchResult:
    match_id: str
    league_id: str
    fixture_id: str
    round_number: int
    home_club_id: str
    away_club_id: str
    home_club_name: str
    away_club_name: str
    home_goals: int
    away_goals: int
    winner_club_id: str | None
    upset: bool
    man_of_the_match: str
    storyline: StorylineBundle
    events: tuple[MatchEvent, ...]
    commentary_prompt: str
    pundit_prompt: str
    viral_score: int
    content_brief: dict[str, object]
    highlight_payload: dict[str, object]
    home_stats: MatchTeamStats
    away_stats: MatchTeamStats
    home_inputs: TeamMatchInputs
    away_inputs: TeamMatchInputs
    simulation_settings: MatchSimulationSettings
    player_performances: tuple[PlayerPerformance, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "match_id": self.match_id,
            "league_id": self.league_id,
            "fixture_id": self.fixture_id,
            "round_number": self.round_number,
            "home_club_id": self.home_club_id,
            "away_club_id": self.away_club_id,
            "home_club_name": self.home_club_name,
            "away_club_name": self.away_club_name,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "winner_club_id": self.winner_club_id,
            "upset": self.upset,
            "man_of_the_match": self.man_of_the_match,
            "storyline": self.storyline.as_dict(),
            "events": [event.as_dict() for event in self.events],
            "commentary_prompt": self.commentary_prompt,
            "pundit_prompt": self.pundit_prompt,
            "viral_score": self.viral_score,
            "content_brief": dict(self.content_brief),
            "highlight_payload": dict(self.highlight_payload),
            "home_stats": self.home_stats.as_dict(),
            "away_stats": self.away_stats.as_dict(),
            "home_inputs": self.home_inputs.as_dict(),
            "away_inputs": self.away_inputs.as_dict(),
            "simulation_settings": self.simulation_settings.as_dict(),
            "player_performances": [performance.as_dict() for performance in self.player_performances],
        }


@dataclass(frozen=True, slots=True)
class _TeamRuntime:
    club: GeneratedClub
    inputs: TeamMatchInputs
    lineup: tuple[GeneratedPlayer, ...]
    keeper: GeneratedPlayer
    attackers: tuple[GeneratedPlayer, ...]
    creators: tuple[GeneratedPlayer, ...]
    defenders: tuple[GeneratedPlayer, ...]
    attack_index: float
    midfield_index: float
    defense_index: float
    goalkeeper_index: float
    finishing_index: float
    creativity_index: float
    press_index: float
    tempo: float
    possession_bias: float


@dataclass(slots=True)
class _PlayerAccumulator:
    player: GeneratedPlayer
    team_id: str
    team_name: str
    minutes: int = 90
    goals: int = 0
    assists: int = 0
    shots: int = 0
    shots_on_target: int = 0
    xg: float = 0.0
    key_passes: int = 0
    passes_completed: int = 0
    tackles_won: int = 0
    fouls_committed: int = 0
    yellow_cards: int = 0
    red_card: bool = False
    saves: int = 0


def _result_value(result: Mapping[str, object] | MatchResult, key: str) -> object:
    if isinstance(result, MatchResult):
        return getattr(result, key)
    return result.get(key)


def create_league(
    *,
    name: str = "GTEX Premier League",
    season: int = 1,
    club_count: int = 20,
    clubs: Sequence[GeneratedClub] | None = None,
    generator: UniverseGenerator | None = None,
) -> League:
    resolved_clubs = tuple(clubs or (generator or UniverseGenerator()).generate_clubs(count=club_count))
    digest = hashlib.sha1(f"{name}|{season}".encode("utf-8")).hexdigest()[:12]
    return League(
        league_id=f"league_{digest}",
        name=name,
        season=season,
        clubs=resolved_clubs,
    )


def build_table(*, league: League, results: Sequence[MatchResult]) -> list[dict[str, object]]:
    rows: dict[str, dict[str, object]] = {
        club.club_id: {
            "club_id": club.club_id,
            "club_name": club.name,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }
        for club in league.clubs
    }
    for result in results:
        home_row = rows[result.home_club_id]
        away_row = rows[result.away_club_id]
        home_row["played"] = int(home_row["played"]) + 1
        away_row["played"] = int(away_row["played"]) + 1
        home_row["goals_for"] = int(home_row["goals_for"]) + result.home_goals
        home_row["goals_against"] = int(home_row["goals_against"]) + result.away_goals
        away_row["goals_for"] = int(away_row["goals_for"]) + result.away_goals
        away_row["goals_against"] = int(away_row["goals_against"]) + result.home_goals
        if result.home_goals > result.away_goals:
            home_row["won"] = int(home_row["won"]) + 1
            away_row["lost"] = int(away_row["lost"]) + 1
            home_row["points"] = int(home_row["points"]) + 3
        elif result.away_goals > result.home_goals:
            away_row["won"] = int(away_row["won"]) + 1
            home_row["lost"] = int(home_row["lost"]) + 1
            away_row["points"] = int(away_row["points"]) + 3
        else:
            home_row["drawn"] = int(home_row["drawn"]) + 1
            away_row["drawn"] = int(away_row["drawn"]) + 1
            home_row["points"] = int(home_row["points"]) + 1
            away_row["points"] = int(away_row["points"]) + 1
    ordered = list(rows.values())
    for row in ordered:
        row["goal_difference"] = int(row["goals_for"]) - int(row["goals_against"])
    ordered.sort(
        key=lambda item: (
            int(item["points"]),
            int(item["goal_difference"]),
            int(item["goals_for"]),
            item["club_name"],
        ),
        reverse=True,
    )
    for index, row in enumerate(ordered, start=1):
        row["position"] = index
    return ordered


def _result_event_type(result: MatchResult) -> str:
    last_goal = next((event for event in reversed(result.events) if event.event_type == "goal"), None)
    if result.home_goals == result.away_goals and last_goal is not None:
        return "equalizer"
    if last_goal is not None and last_goal.minute >= 80 and abs(result.home_goals - result.away_goals) == 1:
        return "winner"
    if result.home_goals + result.away_goals >= 4:
        return "goal"
    return "highlight"


def _team_recent_form(
    *,
    club_id: str,
    previous_results: Sequence[Mapping[str, object] | MatchResult],
) -> tuple[tuple[str, ...], float]:
    recent: list[tuple[str, float]] = []
    for result in previous_results:
        home_id = str(_result_value(result, "home_club_id") or "")
        away_id = str(_result_value(result, "away_club_id") or "")
        if club_id not in {home_id, away_id}:
            continue
        is_home = club_id == home_id
        goals_for = int(_result_value(result, "home_goals") if is_home else _result_value(result, "away_goals"))
        goals_against = int(_result_value(result, "away_goals") if is_home else _result_value(result, "home_goals"))
        symbol = _team_result_code(goals_for=goals_for, goals_against=goals_against)
        xg_bonus = 0.0
        stats_key = "home_stats" if is_home else "away_stats"
        opp_stats_key = "away_stats" if is_home else "home_stats"
        team_stats = _result_value(result, stats_key)
        opp_stats = _result_value(result, opp_stats_key)
        if isinstance(team_stats, Mapping) and isinstance(opp_stats, Mapping):
            xg_delta = float(team_stats.get("xg", 0.0)) - float(opp_stats.get("xg", 0.0))
            xg_bonus = _clamp(xg_delta / 3.5, -0.18, 0.18)
        goal_delta_bonus = _clamp((goals_for - goals_against) / 6.0, -0.22, 0.22)
        recent.append((symbol, goal_delta_bonus + xg_bonus))
    last_five = recent[-5:]
    symbols = tuple(item[0] for item in last_five)
    momentum = _form_momentum_from_symbols(symbols)
    if last_five:
        momentum += _average([item[1] for item in last_five]) * 0.55
    return symbols, _clamp(momentum, -1.0, 1.0)


def _default_team_chemistry(club: GeneratedClub, lineup: Sequence[GeneratedPlayer]) -> float:
    ages = [player.age for player in lineup]
    ratings = [player.rating for player in lineup]
    nationalities = [player.nationality for player in lineup]
    age_balance = 1.0 - (_clamp(abs(_average(ages) - 26.5), 0.0, 10.0) / 10.0)
    rating_spread = 1.0 - (_clamp((max(ratings) - min(ratings)) / 24.0, 0.0, 1.0))
    nationality_links = len(nationalities) - len(set(nationalities))
    chemistry = 0.52
    chemistry += age_balance * 0.12
    chemistry += rating_spread * 0.10
    chemistry += _clamp(nationality_links / 10.0, 0.0, 0.12)
    chemistry += 0.04 if club.style in {"balanced", "counter"} else 0.06 if club.style in {"pressing", "attacking"} else 0.0
    return _clamp(chemistry, 0.42, 0.92)


def _default_team_fatigue(club: GeneratedClub, lineup: Sequence[GeneratedPlayer], form_momentum: float) -> float:
    average_age = _average([player.age for player in lineup])
    fatigue = 0.14
    fatigue += 0.06 if club.style == "pressing" else 0.03 if club.style in {"attacking", "counter"} else 0.01
    fatigue += _clamp((average_age - 27.0) / 40.0, 0.0, 0.08)
    fatigue += _clamp(abs(form_momentum) * 0.04, 0.0, 0.04)
    return _clamp(fatigue, 0.08, 0.42)


def _runtime_for_team(
    *,
    club: GeneratedClub,
    inputs: TeamMatchInputs,
) -> _TeamRuntime:
    lineup = _pick_lineup(club)
    attackers = tuple(player for player in lineup if player.position in _ATTACKING_POSITIONS) or lineup
    creators = tuple(player for player in lineup if player.position in {"AM", "CM", "DM", "RW", "LW", "RB", "LB"}) or lineup
    defenders = tuple(player for player in lineup if player.position in _DEFENSIVE_POSITIONS) or lineup
    keepers = tuple(player for player in lineup if player.position == "GK") or lineup
    keeper = max(keepers, key=lambda player: (player.rating, player.potential, -player.age))
    attack_index = _normalize_rating((club.attack_rating * 0.55) + (_average([player.rating for player in attackers]) * 0.45))
    midfield_core = tuple(player for player in lineup if player.position in {"CM", "DM", "AM"}) or lineup
    midfield_index = _normalize_rating((club.midfield_rating * 0.60) + (_average([player.rating for player in midfield_core]) * 0.40))
    defense_index = _normalize_rating((club.defense_rating * 0.60) + (_average([player.rating for player in defenders]) * 0.40))
    goalkeeper_index = _normalize_rating(keeper.rating)
    finishing_index = _normalize_rating(_average([player.rating for player in attackers]))
    creativity_index = _normalize_rating(_average([player.rating for player in creators]))
    press_index = _clamp((_STYLE_PRESS.get(club.style, 0.97) * 0.52) + (defense_index * 0.48), 0.40, 1.10)
    return _TeamRuntime(
        club=club,
        inputs=inputs.normalized(),
        lineup=lineup,
        keeper=keeper,
        attackers=attackers,
        creators=creators,
        defenders=defenders,
        attack_index=attack_index,
        midfield_index=midfield_index,
        defense_index=defense_index,
        goalkeeper_index=goalkeeper_index,
        finishing_index=finishing_index,
        creativity_index=creativity_index,
        press_index=press_index,
        tempo=_STYLE_TEMPO.get(club.style, 1.0),
        possession_bias=_STYLE_POSSESSION.get(club.style, 1.0),
    )


def _resolve_team_inputs(
    *,
    club: GeneratedClub,
    previous_results: Sequence[Mapping[str, object] | MatchResult],
    override: TeamMatchInputs | None,
) -> TeamMatchInputs:
    lineup = _pick_lineup(club)
    form_last_five, derived_momentum = _team_recent_form(club_id=club.club_id, previous_results=previous_results)
    if override is None:
        return TeamMatchInputs(
            chemistry=_default_team_chemistry(club, lineup),
            fatigue=_default_team_fatigue(club, lineup, derived_momentum),
            form_last_five=form_last_five,
            form_momentum=derived_momentum,
        ).normalized()
    if not override.form_last_five and abs(override.form_momentum) < 1e-9:
        return TeamMatchInputs(
            chemistry=override.chemistry,
            fatigue=override.fatigue,
            form_last_five=form_last_five,
            form_momentum=derived_momentum,
        ).normalized()
    return override.normalized()


def _dynamic_fatigue(runtime: _TeamRuntime, *, elapsed_ratio: float) -> float:
    workload = runtime.inputs.fatigue + (elapsed_ratio * (0.14 + max(runtime.tempo - 1.0, 0.0) * 0.34 + max(runtime.press_index - 0.8, 0.0) * 0.22))
    return _clamp(workload, 0.04, 0.78)


def _create_player_accumulators(runtime: _TeamRuntime) -> dict[str, _PlayerAccumulator]:
    return {
        player.player_id: _PlayerAccumulator(
            player=player,
            team_id=runtime.club.club_id,
            team_name=runtime.club.name,
        )
        for player in runtime.lineup
    }


def _describe_shot_event(
    *,
    shot_kind: str,
    goal: bool,
    on_target: bool,
    team_name: str,
    shooter: GeneratedPlayer,
    creator: GeneratedPlayer | None,
    keeper: GeneratedPlayer,
) -> str:
    if goal:
        if shot_kind == "through_ball" and creator is not None:
            return f"{_position_label(creator.position)} {creator.name} breaks the line - {shooter.name} is through - GOAL for {team_name}!"
        if shot_kind == "cutback" and creator is not None:
            return f"{creator.name} gets to the byline, cuts it back, and {shooter.name} finishes for {team_name}."
        if shot_kind == "set_piece":
            return f"{shooter.name} whips the set piece home for {team_name}."
        if shot_kind == "long":
            return f"{shooter.name} lets it fly from distance and beats {keeper.name} for {team_name}."
        if creator is not None and creator.player_id != shooter.player_id:
            return f"{creator.name} slips the pass inside and {shooter.name} converts for {team_name}."
        return f"{shooter.name} stays composed in the box and scores for {team_name}."
    if on_target:
        if shot_kind == "through_ball" and creator is not None:
            return f"{creator.name} threads it through, but {keeper.name} stands tall to deny {shooter.name}."
        if shot_kind == "set_piece":
            return f"{shooter.name} bends the free kick on target and {keeper.name} beats it away."
        return f"{shooter.name} works a clean strike, and {keeper.name} turns it aside."
    if shot_kind == "long":
        return f"{shooter.name} opens up from range, but the effort fades wide."
    if shot_kind == "cutback" and creator is not None:
        return f"{creator.name} picks out the cutback, and {shooter.name} drags it off target."
    return f"{shooter.name} gets a look at goal, but the finish is loose."


def _shot_outcome_event_type(*, goal: bool, on_target: bool) -> str:
    if goal:
        return "goal"
    if on_target:
        return "save"
    return "chance"


def _build_match_team_stats(
    *,
    possession_seconds: int,
    total_possession_seconds: int,
    shots: int,
    shots_on_target: int,
    xg: float,
    fouls: int,
) -> MatchTeamStats:
    share = 0.5 if total_possession_seconds <= 0 else possession_seconds / total_possession_seconds
    return MatchTeamStats(
        possession_share=_clamp(share, 0.0, 1.0),
        possession_pct=_clamp(share * 100.0, 0.0, 100.0),
        shots=shots,
        shots_on_target=shots_on_target,
        xg=_round_stat(xg),
        fouls=fouls,
    )


def _assign_volume_stats(
    *,
    runtime: _TeamRuntime,
    accumulators: Mapping[str, _PlayerAccumulator],
    team_stats: MatchTeamStats,
    conceding_goals: int,
    rng: random.Random,
) -> None:
    final_fatigue = _dynamic_fatigue(runtime, elapsed_ratio=1.0)
    passes_multiplier = (team_stats.possession_pct / 50.0) * (0.92 + (runtime.inputs.chemistry * 0.18)) * (1.04 - (final_fatigue * 0.12))
    tackle_multiplier = ((100.0 - team_stats.possession_pct) / 50.0) * (0.90 + (runtime.press_index * 0.16))
    for accumulator in accumulators.values():
        minutes_ratio = accumulator.minutes / 90.0
        pass_weight = _PASS_ROLE_WEIGHTS.get(accumulator.player.position, 0.75)
        tackle_weight = _TACKLE_ROLE_WEIGHTS.get(accumulator.player.position, 0.25)
        accumulator.passes_completed = max(
            accumulator.passes_completed,
            int(
                round(
                    (22 + (pass_weight * 24) + ((accumulator.player.rating - 70) * 0.40))
                    * passes_multiplier
                    * minutes_ratio
                    * rng.uniform(0.88, 1.12)
                )
            ),
        )
        accumulator.tackles_won = max(
            accumulator.tackles_won,
            int(
                round(
                    (tackle_weight * 4.2)
                    * tackle_multiplier
                    * minutes_ratio
                    * rng.uniform(0.80, 1.20)
                )
            ),
        )
        if accumulator.player.position in _DEFENSIVE_POSITIONS and conceding_goals == 0:
            accumulator.tackles_won += 1


def _to_player_performance(
    *,
    accumulator: _PlayerAccumulator,
    team_goals: int,
    team_goals_against: int,
) -> PlayerPerformance:
    clean_sheet = team_goals_against == 0 and accumulator.player.position in {"GK", "CB", "RB", "LB", "DM"}
    result_bonus = 0.22 if team_goals > team_goals_against else 0.04 if team_goals == team_goals_against else -0.18
    missed_xg_penalty = max(0.0, accumulator.xg - (accumulator.goals * 0.35) - 0.20) * 0.45
    rating = 6.15
    rating += accumulator.goals * 1.10
    rating += accumulator.assists * 0.70
    rating += accumulator.shots_on_target * 0.08
    rating += accumulator.key_passes * 0.05
    rating += accumulator.tackles_won * 0.05
    rating += accumulator.saves * 0.20
    rating += accumulator.passes_completed * 0.003
    rating += 0.32 if clean_sheet else 0.0
    rating += result_bonus
    rating -= accumulator.fouls_committed * 0.08
    rating -= accumulator.yellow_cards * 0.22
    rating -= 1.15 if accumulator.red_card else 0.0
    rating -= missed_xg_penalty
    return PlayerPerformance(
        player_id=accumulator.player.player_id,
        team_id=accumulator.team_id,
        team_name=accumulator.team_name,
        player_name=accumulator.player.name,
        position=accumulator.player.position,
        minutes=max(0, min(90, accumulator.minutes)),
        rating=_round_stat(_clamp(rating, 4.8, 10.0)),
        goals=accumulator.goals,
        assists=accumulator.assists,
        shots=accumulator.shots,
        shots_on_target=accumulator.shots_on_target,
        xg=_round_stat(accumulator.xg),
        key_passes=accumulator.key_passes,
        passes_completed=max(0, accumulator.passes_completed),
        tackles_won=max(0, accumulator.tackles_won),
        fouls_committed=accumulator.fouls_committed,
        yellow_cards=accumulator.yellow_cards,
        red_card=accumulator.red_card,
        saves=accumulator.saves,
        clean_sheet=clean_sheet,
    )


def match_result_from_mapping(payload: Mapping[str, object]) -> MatchResult:
    storyline_payload = dict(payload.get("storyline") or {})
    story_tags = storyline_payload.get("tags") or ()
    storyline = StorylineBundle(
        rivalry=bool(storyline_payload.get("rivalry", False)),
        revenge_match=bool(storyline_payload.get("revenge_match", False)),
        underdog=bool(storyline_payload.get("underdog", False)),
        pressure_match=bool(storyline_payload.get("pressure_match", False)),
        title_race=bool(storyline_payload.get("title_race", False)),
        headline=str(storyline_payload.get("headline", "")),
        hook=str(storyline_payload.get("hook", "")),
        commentary_angle=str(storyline_payload.get("commentary_angle", "")),
        pundit_angle=str(storyline_payload.get("pundit_angle", "")),
        viral_boost=int(storyline_payload.get("viral_boost", 0)),
        tags=tuple(str(tag) for tag in story_tags),
    )
    home_stats_payload = dict(payload.get("home_stats") or {})
    away_stats_payload = dict(payload.get("away_stats") or {})
    home_goals = int(payload.get("home_goals", 0))
    away_goals = int(payload.get("away_goals", 0))
    home_stats = MatchTeamStats(
        possession_share=float(home_stats_payload.get("possession_share", 0.5)),
        possession_pct=float(home_stats_payload.get("possession_pct", 50.0)),
        shots=int(home_stats_payload.get("shots", max(home_goals, 4))),
        shots_on_target=int(home_stats_payload.get("shots_on_target", max(home_goals, 2))),
        xg=float(home_stats_payload.get("xg", max(home_goals * 0.70, 0.45))),
        fouls=int(home_stats_payload.get("fouls", 10)),
    )
    away_stats = MatchTeamStats(
        possession_share=float(away_stats_payload.get("possession_share", 0.5)),
        possession_pct=float(away_stats_payload.get("possession_pct", 50.0)),
        shots=int(away_stats_payload.get("shots", max(away_goals, 4))),
        shots_on_target=int(away_stats_payload.get("shots_on_target", max(away_goals, 2))),
        xg=float(away_stats_payload.get("xg", max(away_goals * 0.70, 0.45))),
        fouls=int(away_stats_payload.get("fouls", 10)),
    )
    home_inputs_payload = dict(payload.get("home_inputs") or {})
    away_inputs_payload = dict(payload.get("away_inputs") or {})
    settings_payload = dict(payload.get("simulation_settings") or {})
    events = tuple(
        MatchEvent(
            minute=int(event.get("minute", 1)),
            match_second=int(event.get("match_second", int(event.get("minute", 1)) * 60)),
            team_id=str(event.get("team_id", "")),
            team_name=str(event.get("team_name", "")),
            player_name=str(event.get("player_name", "")),
            event_type=str(event.get("event_type", "highlight")),
            outcome=str(event.get("outcome", "recorded")),
            description=str(event.get("description", "")),
            secondary_player_name=(str(event["secondary_player_name"]) if event.get("secondary_player_name") else None),
            xg=float(event.get("xg", 0.0)),
        )
        for event in tuple(payload.get("events") or ())
        if isinstance(event, Mapping)
    )
    player_performances = tuple(
        PlayerPerformance(
            player_id=str(item.get("player_id", "")),
            team_id=str(item.get("team_id", "")),
            team_name=str(item.get("team_name", "")),
            player_name=str(item.get("player_name", "")),
            position=str(item.get("position", "")),
            minutes=int(item.get("minutes", 90)),
            rating=float(item.get("rating", 6.0)),
            goals=int(item.get("goals", 0)),
            assists=int(item.get("assists", 0)),
            shots=int(item.get("shots", 0)),
            shots_on_target=int(item.get("shots_on_target", 0)),
            xg=float(item.get("xg", 0.0)),
            key_passes=int(item.get("key_passes", 0)),
            passes_completed=int(item.get("passes_completed", 0)),
            tackles_won=int(item.get("tackles_won", 0)),
            fouls_committed=int(item.get("fouls_committed", 0)),
            yellow_cards=int(item.get("yellow_cards", 0)),
            red_card=bool(item.get("red_card", False)),
            saves=int(item.get("saves", 0)),
            clean_sheet=bool(item.get("clean_sheet", False)),
        )
        for item in tuple(payload.get("player_performances") or ())
        if isinstance(item, Mapping)
    )
    return MatchResult(
        match_id=str(payload.get("match_id", "")),
        league_id=str(payload.get("league_id", "")),
        fixture_id=str(payload.get("fixture_id", "")),
        round_number=int(payload.get("round_number", 0)),
        home_club_id=str(payload.get("home_club_id", "")),
        away_club_id=str(payload.get("away_club_id", "")),
        home_club_name=str(payload.get("home_club_name", "")),
        away_club_name=str(payload.get("away_club_name", "")),
        home_goals=home_goals,
        away_goals=away_goals,
        winner_club_id=(str(payload["winner_club_id"]) if payload.get("winner_club_id") else None),
        upset=bool(payload.get("upset", False)),
        man_of_the_match=str(payload.get("man_of_the_match", "")),
        storyline=storyline,
        events=events,
        commentary_prompt=str(payload.get("commentary_prompt", "")),
        pundit_prompt=str(payload.get("pundit_prompt", "")),
        viral_score=int(payload.get("viral_score", 35)),
        content_brief=dict(payload.get("content_brief") or {}),
        highlight_payload=dict(payload.get("highlight_payload") or {}),
        home_stats=home_stats,
        away_stats=away_stats,
        home_inputs=TeamMatchInputs(
            chemistry=float(home_inputs_payload.get("chemistry", 0.65)),
            fatigue=float(home_inputs_payload.get("fatigue", 0.18)),
            form_last_five=tuple(home_inputs_payload.get("form_last_five") or ()),
            form_momentum=float(home_inputs_payload.get("form_momentum", 0.0)),
        ).normalized(),
        away_inputs=TeamMatchInputs(
            chemistry=float(away_inputs_payload.get("chemistry", 0.65)),
            fatigue=float(away_inputs_payload.get("fatigue", 0.18)),
            form_last_five=tuple(away_inputs_payload.get("form_last_five") or ()),
            form_momentum=float(away_inputs_payload.get("form_momentum", 0.0)),
        ).normalized(),
        simulation_settings=MatchSimulationSettings(
            randomness_factor=float(settings_payload.get("randomness_factor", 0.18)),
            tick_seconds_min=int(settings_payload.get("tick_seconds_min", 1)),
            tick_seconds_max=int(settings_payload.get("tick_seconds_max", 5)),
        ).normalized(),
        player_performances=player_performances,
    )


class LeagueEngine:
    def __init__(
        self,
        seed: int | None = None,
        *,
        randomness_factor: float = 0.18,
        tick_seconds_min: int = 1,
        tick_seconds_max: int = 5,
    ) -> None:
        self._seed = seed
        self._settings = MatchSimulationSettings(
            randomness_factor=randomness_factor,
            tick_seconds_min=tick_seconds_min,
            tick_seconds_max=tick_seconds_max,
        ).normalized()

    def simulate_fixture(
        self,
        *,
        league: League,
        fixture: Fixture,
        previous_results: Sequence[Mapping[str, object] | MatchResult] = (),
        table_positions: Mapping[str, int] | None = None,
        team_inputs: Mapping[str, TeamMatchInputs] | None = None,
        randomness_factor: float | None = None,
    ) -> MatchResult:
        clubs_by_id = league.club_map()
        home = clubs_by_id[fixture.home_club_id]
        away = clubs_by_id[fixture.away_club_id]
        storyline = inject_storylines(
            fixture,
            clubs_by_id,
            previous_results=tuple(result.as_dict() if isinstance(result, MatchResult) else result for result in previous_results),
            table_positions=table_positions,
        )
        settings = MatchSimulationSettings(
            randomness_factor=self._settings.randomness_factor if randomness_factor is None else randomness_factor,
            tick_seconds_min=self._settings.tick_seconds_min,
            tick_seconds_max=self._settings.tick_seconds_max,
        ).normalized()
        seed_basis = self._seed if self._seed is not None else random.SystemRandom().randint(1, 2**31 - 1)
        rng = random.Random(_stable_seed(seed_basis, league.league_id, fixture.fixture_id, fixture.round_number))
        resolved_team_inputs = dict(team_inputs or {})
        home_inputs = _resolve_team_inputs(club=home, previous_results=previous_results, override=resolved_team_inputs.get(home.club_id))
        away_inputs = _resolve_team_inputs(club=away, previous_results=previous_results, override=resolved_team_inputs.get(away.club_id))
        home_runtime = _runtime_for_team(club=home, inputs=home_inputs)
        away_runtime = _runtime_for_team(club=away, inputs=away_inputs)
        accumulators = _create_player_accumulators(home_runtime)
        accumulators.update(_create_player_accumulators(away_runtime))
        possession_seconds = {home.club_id: 0, away.club_id: 0}
        shots = {home.club_id: 0, away.club_id: 0}
        shots_on_target = {home.club_id: 0, away.club_id: 0}
        xg_totals = {home.club_id: 0.0, away.club_id: 0.0}
        fouls = {home.club_id: 0, away.club_id: 0}
        goals = {home.club_id: 0, away.club_id: 0}
        players_on_pitch = {home.club_id: 11, away.club_id: 11}
        major_events: list[MatchEvent] = []
        total_seconds = 90 * 60
        current_second = 0
        current_possession = home.club_id if rng.random() < 0.5 else away.club_id
        while current_second < total_seconds:
            tick_seconds = min(rng.randint(settings.tick_seconds_min, settings.tick_seconds_max), total_seconds - current_second)
            current_second += tick_seconds
            elapsed_ratio = current_second / total_seconds
            home_fatigue = _dynamic_fatigue(home_runtime, elapsed_ratio=elapsed_ratio)
            away_fatigue = _dynamic_fatigue(away_runtime, elapsed_ratio=elapsed_ratio)
            home_numbers = 1.0 - max(0, 11 - players_on_pitch[home.club_id]) * 0.055
            away_numbers = 1.0 - max(0, 11 - players_on_pitch[away.club_id]) * 0.055
            home_control = (
                (home_runtime.midfield_index * 0.54)
                + (home_runtime.creativity_index * 0.12)
                + (home_runtime.inputs.chemistry * 0.15)
                + (home_runtime.inputs.form_momentum * 0.07)
                + (home_runtime.possession_bias * 0.12)
                + 0.05
            ) * home_numbers - (home_fatigue * 0.15)
            away_control = (
                (away_runtime.midfield_index * 0.54)
                + (away_runtime.creativity_index * 0.12)
                + (away_runtime.inputs.chemistry * 0.15)
                + (away_runtime.inputs.form_momentum * 0.07)
                + (away_runtime.possession_bias * 0.12)
            ) * away_numbers - (away_fatigue * 0.15)
            home_share = _clamp(0.5 + ((home_control - away_control) * 1.35) + _noise(rng, factor=settings.randomness_factor, amplitude=0.05), 0.31, 0.69)
            retain_probability = _clamp(0.53 + abs(home_share - 0.5) + _noise(rng, factor=settings.randomness_factor, amplitude=0.02), 0.42, 0.82)
            if rng.random() > retain_probability:
                current_possession = home.club_id if rng.random() < home_share else away.club_id
            possession_seconds[current_possession] += tick_seconds
            attacker = home_runtime if current_possession == home.club_id else away_runtime
            defender = away_runtime if attacker.club.club_id == home.club_id else home_runtime
            attacker_fatigue = home_fatigue if attacker.club.club_id == home.club_id else away_fatigue
            defender_fatigue = away_fatigue if defender.club.club_id == away.club_id else home_fatigue
            attacker_numbers = home_numbers if attacker.club.club_id == home.club_id else away_numbers
            defender_numbers = away_numbers if defender.club.club_id == away.club_id else home_numbers
            score_gap = abs(goals[home.club_id] - goals[away.club_id])
            late_pressure = 0.10 if storyline.pressure_match and elapsed_ratio >= 0.74 and score_gap <= 1 else 0.0
            attack_score = (
                (attacker.attack_index * 0.42)
                + (attacker.creativity_index * 0.18)
                + (attacker.inputs.chemistry * 0.12)
                + (attacker.inputs.form_momentum * 0.09)
                + (attacker.tempo * 0.10)
            ) * attacker_numbers - (attacker_fatigue * 0.20)
            defense_score = (
                (defender.defense_index * 0.48)
                + (defender.goalkeeper_index * 0.14)
                + (defender.inputs.chemistry * 0.08)
                + (defender.press_index * 0.08)
            ) * defender_numbers - (defender_fatigue * 0.06)
            attack_edge = attack_score - defense_score
            foul_probability = _clamp(
                0.0014
                * tick_seconds
                * (1.0 + (0.40 if storyline.rivalry else 0.0) + (defender_fatigue * 0.80) + (late_pressure * 1.3)),
                0.0004,
                0.03,
            )
            if rng.random() < foul_probability:
                fouls[defender.club.club_id] += 1
                offender = _weighted_choice(defender.defenders or defender.lineup, rng, weights_by_position=_TACKLE_ROLE_WEIGHTS)
                offender_accumulator = accumulators[offender.player_id]
                offender_accumulator.fouls_committed += 1
                red_card_probability = 0.010 + (0.010 if storyline.rivalry else 0.0) + (0.010 if elapsed_ratio > 0.70 else 0.0)
                yellow_card_probability = 0.16 + (0.06 if storyline.rivalry else 0.0)
                if not offender_accumulator.red_card and players_on_pitch[defender.club.club_id] > 9 and rng.random() < red_card_probability:
                    players_on_pitch[defender.club.club_id] -= 1
                    offender_accumulator.red_card = True
                    offender_accumulator.minutes = min(offender_accumulator.minutes, _event_minute(current_second))
                    major_events.append(
                        MatchEvent(
                            minute=_event_minute(current_second),
                            match_second=current_second,
                            team_id=defender.club.club_id,
                            team_name=defender.club.name,
                            player_name=offender.name,
                            event_type="red_card",
                            outcome="sent_off",
                            description=f"{offender.name} arrives late and leaves the referee no choice: red card for {defender.club.name}.",
                        )
                    )
                    continue
                if rng.random() < yellow_card_probability:
                    offender_accumulator.yellow_cards += 1
                if rng.random() < 0.14:
                    attack_edge += 0.05
                else:
                    continue
            shot_probability = _clamp(
                0.0025
                * tick_seconds
                * (
                    0.92
                    + (attacker.tempo * 0.28)
                    + max(attack_edge, -0.12) * 2.40
                    + (0.12 if storyline.rivalry else 0.0)
                    + late_pressure
                ),
                0.0008,
                0.05,
            )
            if rng.random() >= shot_probability:
                continue
            shot_source = "set_piece" if rng.random() < 0.10 else "open_play"
            creator = _weighted_choice(attacker.creators or attacker.lineup, rng, weights_by_position=_CREATOR_POSITION_WEIGHTS)
            shooter = _weighted_choice(attacker.attackers or attacker.lineup, rng, weights_by_position=_SHOTTER_POSITION_WEIGHTS)
            if shooter.player_id == creator.player_id and len(attacker.lineup) > 1:
                alternatives = tuple(player for player in attacker.attackers if player.player_id != creator.player_id) or tuple(player for player in attacker.lineup if player.player_id != creator.player_id)
                if alternatives:
                    shooter = _weighted_choice(alternatives, rng, weights_by_position=_SHOTTER_POSITION_WEIGHTS)
            finisher_delta = (shooter.rating - defender.keeper.rating) / 100.0
            quality_score = _clamp(
                0.44
                + (attack_edge * 1.80)
                + (finisher_delta * 0.55)
                + (attacker.inputs.form_momentum * 0.10)
                - (attacker_fatigue * 0.18)
                + _noise(rng, factor=settings.randomness_factor, amplitude=0.18),
                0.05,
                0.95,
            )
            shot_roll = rng.random()
            if shot_source == "set_piece":
                shot_kind = "set_piece"
                base_xg = rng.uniform(0.04, 0.13)
            elif shot_roll < 0.10 + (quality_score * 0.16):
                shot_kind = "through_ball"
                base_xg = rng.uniform(0.22, 0.40)
            elif shot_roll < 0.34 + (quality_score * 0.18):
                shot_kind = "cutback"
                base_xg = rng.uniform(0.12, 0.27)
            elif shot_roll < 0.76:
                shot_kind = "box"
                base_xg = rng.uniform(0.08, 0.20)
            else:
                shot_kind = "long"
                base_xg = rng.uniform(0.02, 0.08)
            shot_xg = _clamp(
                base_xg
                + (attack_edge * 0.08)
                + ((shooter.rating - 75) * 0.0018)
                + (attacker.inputs.chemistry * 0.025)
                - (defender.goalkeeper_index * 0.02)
                - (attacker_fatigue * 0.04),
                0.01,
                0.62,
            )
            goal_probability = _clamp(
                shot_xg
                * (
                    1.02
                    + ((shooter.rating - 75) * 0.004)
                    + (attacker.inputs.form_momentum * 0.06)
                    - (attacker_fatigue * 0.12)
                    - ((defender.keeper.rating - 75) * 0.0025)
                ),
                0.01,
                0.82,
            )
            goal = rng.random() < goal_probability
            on_target_probability = _clamp(
                0.24
                + (shot_xg * 1.55)
                + ((shooter.rating - 70) * 0.004)
                - (attacker_fatigue * 0.06),
                0.18,
                0.94,
            )
            on_target = goal or rng.random() < on_target_probability
            shots[attacker.club.club_id] += 1
            shots_on_target[attacker.club.club_id] += 1 if on_target else 0
            xg_totals[attacker.club.club_id] += shot_xg
            shooter_accumulator = accumulators[shooter.player_id]
            creator_accumulator = accumulators[creator.player_id]
            keeper_accumulator = accumulators[defender.keeper.player_id]
            shooter_accumulator.shots += 1
            shooter_accumulator.shots_on_target += 1 if on_target else 0
            shooter_accumulator.xg += shot_xg
            if creator.player_id != shooter.player_id:
                creator_accumulator.key_passes += 1
            if goal:
                goals[attacker.club.club_id] += 1
                shooter_accumulator.goals += 1
                if creator.player_id != shooter.player_id:
                    creator_accumulator.assists += 1
            elif on_target:
                keeper_accumulator.saves += 1
            should_log = goal or shot_xg >= 0.18 or (on_target and elapsed_ratio >= 0.70 and score_gap <= 1)
            if should_log:
                major_events.append(
                    MatchEvent(
                        minute=_event_minute(current_second),
                        match_second=current_second,
                        team_id=attacker.club.club_id,
                        team_name=attacker.club.name,
                        player_name=shooter.name,
                        event_type=_shot_outcome_event_type(goal=goal, on_target=on_target),
                        outcome="goal" if goal else "saved" if on_target else "off_target",
                        description=_describe_shot_event(
                            shot_kind=shot_kind,
                            goal=goal,
                            on_target=on_target,
                            team_name=attacker.club.name,
                            shooter=shooter,
                            creator=None if creator.player_id == shooter.player_id else creator,
                            keeper=defender.keeper,
                        ),
                        secondary_player_name=None if creator.player_id == shooter.player_id else creator.name,
                        xg=shot_xg,
                    )
                )
        return self._finalize_result(
            league=league,
            fixture=fixture,
            home=home,
            away=away,
            storyline=storyline,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            settings=settings,
            goals=goals,
            possession_seconds=possession_seconds,
            shots=shots,
            shots_on_target=shots_on_target,
            xg_totals=xg_totals,
            fouls=fouls,
            accumulators=accumulators,
            major_events=major_events,
            rng=rng,
        )

    def simulate_round(
        self,
        *,
        league: League,
        fixtures: Sequence[Fixture],
        previous_results: Sequence[Mapping[str, object] | MatchResult] = (),
        team_inputs: Mapping[str, TeamMatchInputs] | None = None,
        randomness_factor: float | None = None,
    ) -> list[MatchResult]:
        historic_results = [
            result
            for result in previous_results
            if str(_result_value(result, "league_id") or "") == league.league_id
        ]
        table_positions: Mapping[str, int] = {}
        if historic_results:
            converted = [result if isinstance(result, MatchResult) else match_result_from_mapping(dict(result)) for result in historic_results]
            table_positions = {row["club_id"]: int(row["position"]) for row in build_table(league=league, results=converted)}
        return [
            self.simulate_fixture(
                league=league,
                fixture=fixture,
                previous_results=previous_results,
                table_positions=table_positions,
                team_inputs=team_inputs,
                randomness_factor=randomness_factor,
            )
            for fixture in fixtures
        ]

    def _finalize_result(
        self,
        *,
        league: League,
        fixture: Fixture,
        home: GeneratedClub,
        away: GeneratedClub,
        storyline: StorylineBundle,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        settings: MatchSimulationSettings,
        goals: Mapping[str, int],
        possession_seconds: Mapping[str, int],
        shots: Mapping[str, int],
        shots_on_target: Mapping[str, int],
        xg_totals: Mapping[str, float],
        fouls: Mapping[str, int],
        accumulators: Mapping[str, _PlayerAccumulator],
        major_events: Sequence[MatchEvent],
        rng: random.Random,
    ) -> MatchResult:
        total_possession_seconds = possession_seconds[home.club_id] + possession_seconds[away.club_id]
        home_stats = _build_match_team_stats(
            possession_seconds=possession_seconds[home.club_id],
            total_possession_seconds=total_possession_seconds,
            shots=shots[home.club_id],
            shots_on_target=shots_on_target[home.club_id],
            xg=xg_totals[home.club_id],
            fouls=fouls[home.club_id],
        )
        away_stats = _build_match_team_stats(
            possession_seconds=possession_seconds[away.club_id],
            total_possession_seconds=total_possession_seconds,
            shots=shots[away.club_id],
            shots_on_target=shots_on_target[away.club_id],
            xg=xg_totals[away.club_id],
            fouls=fouls[away.club_id],
        )
        _assign_volume_stats(
            runtime=home_runtime,
            accumulators={player_id: accumulator for player_id, accumulator in accumulators.items() if accumulator.team_id == home.club_id},
            team_stats=home_stats,
            conceding_goals=goals[away.club_id],
            rng=rng,
        )
        _assign_volume_stats(
            runtime=away_runtime,
            accumulators={player_id: accumulator for player_id, accumulator in accumulators.items() if accumulator.team_id == away.club_id},
            team_stats=away_stats,
            conceding_goals=goals[home.club_id],
            rng=rng,
        )
        player_performances = tuple(
            sorted(
                (
                    _to_player_performance(
                        accumulator=accumulator,
                        team_goals=goals[accumulator.team_id],
                        team_goals_against=goals[away.club_id if accumulator.team_id == home.club_id else home.club_id],
                    )
                    for accumulator in accumulators.values()
                ),
                key=lambda performance: (
                    performance.rating,
                    performance.goals,
                    performance.assists,
                    performance.player_name,
                ),
                reverse=True,
            )
        )
        winner_club_id = home.club_id if goals[home.club_id] > goals[away.club_id] else away.club_id if goals[away.club_id] > goals[home.club_id] else None
        favorite = home if home.overall_rating >= away.overall_rating else away
        underdog = away if favorite.club_id == home.club_id else home
        upset = winner_club_id == underdog.club_id and abs(home.overall_rating - away.overall_rating) >= 4
        man_of_the_match = player_performances[0].player_name if player_performances else home.star_player.name
        content_brief = build_content_brief(fixture, storyline, home_club=home, away_club=away)
        last_highlight = next((event for event in reversed(major_events) if event.event_type == "goal"), major_events[-1] if major_events else None)
        last_highlight_line = last_highlight.description if last_highlight is not None else "The match stayed tense and compact."
        commentary_prompt = (
            f"{storyline.commentary_angle} Final score: {home.name} {goals[home.club_id]}-{goals[away.club_id]} {away.name}. "
            f"Possession {home_stats.possession_pct:.1f}-{away_stats.possession_pct:.1f}, shots {home_stats.shots}-{away_stats.shots}, "
            f"xG {home_stats.xg:.2f}-{away_stats.xg:.2f}. "
            f"Lean on event lines like '{last_highlight_line}' and name {man_of_the_match} as the decisive performer."
        )
        pundit_prompt = (
            f"{storyline.pundit_angle} Use the actual tick-driven profile: possession {home_stats.possession_pct:.1f}-{away_stats.possession_pct:.1f}, "
            f"shots {home_stats.shots}-{away_stats.shots}, xG {home_stats.xg:.2f}-{away_stats.xg:.2f}, fouls {home_stats.fouls}-{away_stats.fouls}. "
            f"Argue whether the scoreline was deserved, volatile, or a product of game-state swings."
        )
        result = MatchResult(
            match_id=f"match_{fixture.fixture_id}",
            league_id=league.league_id,
            fixture_id=fixture.fixture_id,
            round_number=fixture.round_number,
            home_club_id=home.club_id,
            away_club_id=away.club_id,
            home_club_name=home.name,
            away_club_name=away.name,
            home_goals=goals[home.club_id],
            away_goals=goals[away.club_id],
            winner_club_id=winner_club_id,
            upset=upset,
            man_of_the_match=man_of_the_match,
            storyline=storyline,
            events=tuple(sorted(major_events, key=lambda event: (event.match_second, event.team_name, event.player_name))),
            commentary_prompt=commentary_prompt,
            pundit_prompt=pundit_prompt,
            viral_score=self._viral_score(
                home_goals=goals[home.club_id],
                away_goals=goals[away.club_id],
                storyline=storyline,
                upset=upset,
                events=major_events,
                home_stats=home_stats,
                away_stats=away_stats,
            ),
            content_brief=content_brief,
            highlight_payload={},
            home_stats=home_stats,
            away_stats=away_stats,
            home_inputs=home_runtime.inputs,
            away_inputs=away_runtime.inputs,
            simulation_settings=settings,
            player_performances=player_performances,
        )
        return MatchResult(
            match_id=result.match_id,
            league_id=result.league_id,
            fixture_id=result.fixture_id,
            round_number=result.round_number,
            home_club_id=result.home_club_id,
            away_club_id=result.away_club_id,
            home_club_name=result.home_club_name,
            away_club_name=result.away_club_name,
            home_goals=result.home_goals,
            away_goals=result.away_goals,
            winner_club_id=result.winner_club_id,
            upset=result.upset,
            man_of_the_match=result.man_of_the_match,
            storyline=result.storyline,
            events=result.events,
            commentary_prompt=result.commentary_prompt,
            pundit_prompt=result.pundit_prompt,
            viral_score=result.viral_score,
            content_brief=result.content_brief,
            highlight_payload=self._highlight_payload(result=result),
            home_stats=result.home_stats,
            away_stats=result.away_stats,
            home_inputs=result.home_inputs,
            away_inputs=result.away_inputs,
            simulation_settings=result.simulation_settings,
            player_performances=result.player_performances,
        )

    def _viral_score(
        self,
        *,
        home_goals: int,
        away_goals: int,
        storyline: StorylineBundle,
        upset: bool,
        events: Sequence[MatchEvent],
        home_stats: MatchTeamStats,
        away_stats: MatchTeamStats,
    ) -> int:
        score = 38 + ((home_goals + away_goals) * 6) + storyline.viral_boost
        score += int((home_stats.xg + away_stats.xg) * 5)
        if upset:
            score += 14
        if home_goals == away_goals:
            score += 5
        if events and events[-1].event_type == "goal" and events[-1].minute >= 80:
            score += 10
        score += sum(1 for event in events if event.event_type == "red_card") * 5
        return int(_clamp(score, 35, 99))

    def _highlight_payload(self, *, result: MatchResult) -> dict[str, object]:
        last_goal = next((event for event in reversed(result.events) if event.event_type == "goal"), None)
        focus_event = last_goal or (result.events[-1] if result.events else None)
        winning_team_name = (
            result.home_club_name
            if result.winner_club_id == result.home_club_id
            else result.away_club_name
            if result.winner_club_id == result.away_club_id
            else result.home_club_name
        )
        opponent_name = result.away_club_name if winning_team_name == result.home_club_name else result.home_club_name
        title = f"{winning_team_name} ignite {result.storyline.headline.lower()}"
        if result.winner_club_id is None:
            title = f"{result.home_club_name} and {result.away_club_name} trade believable chaos"
        caption_subject = focus_event.player_name if focus_event is not None else result.man_of_the_match
        return {
            "clip_id": f"clip_{result.match_id}",
            "match_id": result.match_id,
            "title": title,
            "event_type": _result_event_type(result),
            "team_name": winning_team_name,
            "opponent_name": opponent_name,
            "player_name": caption_subject,
            "minute": focus_event.minute if focus_event is not None else 90,
            "viral_score": result.viral_score,
            "duration": min(32, 18 + len(result.events) + (4 if result.storyline.rivalry else 0)),
            "video_path": f"generated/{result.match_id}/raw.mp4",
            "polished_video_path": f"generated/{result.match_id}/polished.mp4",
            "raw_caption": f"{caption_subject} shifts the match state in {result.home_club_name} vs {result.away_club_name}",
            "polished_caption": f"{title.title()} after a {result.home_goals}-{result.away_goals} finish",
            "publish_polished": True,
            "metadata": {
                "story_tags": list(result.storyline.tags),
                "commentary_prompt": result.commentary_prompt,
                "pundit_prompt": result.pundit_prompt,
                "man_of_the_match": result.man_of_the_match,
                "home_stats": result.home_stats.as_dict(),
                "away_stats": result.away_stats.as_dict(),
            },
        }
