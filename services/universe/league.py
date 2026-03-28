from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import random
from typing import Any, Mapping, Sequence

from services.universe.generator import GeneratedClub, UniverseGenerator
from services.universe.scheduler import Fixture
from services.universe.storyline import StorylineBundle, build_content_brief, inject_storylines


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _poisson_sample(rate: float, rng: random.Random) -> int:
    bounded_rate = _clamp(rate, 0.15, 4.8)
    threshold = math.exp(-bounded_rate)
    result = 0
    product = 1.0
    while product > threshold:
        result += 1
        product *= rng.random()
    return max(0, result - 1)


def _weighted_choice(players: Sequence[Any], rng: random.Random) -> Any:
    weights = []
    for player in players:
        position_bonus = {
            "ST": 18,
            "RW": 11,
            "LW": 11,
            "AM": 9,
            "CM": 5,
            "DM": 3,
            "CB": 2,
            "RB": 2,
            "LB": 2,
            "GK": 1,
        }.get(str(player.position), 1)
        weights.append(max(1, int(player.rating) + position_bonus))
    return rng.choices(list(players), weights=weights, k=1)[0]


def _goal_minutes(goal_count: int, rng: random.Random, *, late_bias: bool) -> list[int]:
    minutes: list[int] = []
    while len(minutes) < goal_count:
        minute = int(round(rng.triangular(1, 90, 79 if late_bias else 56)))
        minute = min(max(minute, 1), 90)
        if minute in minutes:
            continue
        minutes.append(minute)
    minutes.sort()
    return minutes


def _result_event_type(result: "MatchResult") -> str:
    if result.home_goals == result.away_goals and result.events:
        return "equalizer"
    if result.events and result.events[-1].minute >= 80 and abs(result.home_goals - result.away_goals) == 1:
        return "winner"
    if result.home_goals + result.away_goals >= 4:
        return "goal"
    return "highlight"


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
class MatchEvent:
    minute: int
    team_id: str
    team_name: str
    player_name: str
    event_type: str
    description: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


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
        }


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


class LeagueEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def simulate_fixture(
        self,
        *,
        league: League,
        fixture: Fixture,
        previous_results: Sequence[Mapping[str, object]] = (),
        table_positions: Mapping[str, int] | None = None,
    ) -> MatchResult:
        clubs_by_id = league.club_map()
        home = clubs_by_id[fixture.home_club_id]
        away = clubs_by_id[fixture.away_club_id]
        storyline = inject_storylines(
            fixture,
            clubs_by_id,
            previous_results=previous_results,
            table_positions=table_positions,
        )
        home_rate, away_rate = self._goal_rates(home=home, away=away, storyline=storyline)
        home_goals = _poisson_sample(home_rate, self._random)
        away_goals = _poisson_sample(away_rate, self._random)
        events: list[MatchEvent] = []
        home_scorers = [player for player in home.roster if player.position != "GK"] or list(home.roster)
        away_scorers = [player for player in away.roster if player.position != "GK"] or list(away.roster)
        for minute in _goal_minutes(home_goals, self._random, late_bias=storyline.pressure_match):
            scorer = _weighted_choice(home_scorers, self._random)
            events.append(
                MatchEvent(
                    minute=minute,
                    team_id=home.club_id,
                    team_name=home.name,
                    player_name=scorer.name,
                    event_type="goal",
                    description=f"{scorer.name} finishes for {home.name}.",
                )
            )
        for minute in _goal_minutes(away_goals, self._random, late_bias=storyline.underdog):
            scorer = _weighted_choice(away_scorers, self._random)
            events.append(
                MatchEvent(
                    minute=minute,
                    team_id=away.club_id,
                    team_name=away.name,
                    player_name=scorer.name,
                    event_type="goal",
                    description=f"{scorer.name} answers for {away.name}.",
                )
            )
        if self._random.random() < (0.12 + (0.10 if storyline.rivalry else 0.0)):
            sent_off_team = home if self._random.random() < 0.5 else away
            defender_pool = [player for player in sent_off_team.roster if player.position in {"CB", "RB", "LB", "DM"}]
            sent_off = _weighted_choice(defender_pool or sent_off_team.roster, self._random)
            events.append(
                MatchEvent(
                    minute=self._random.randint(18, 88),
                    team_id=sent_off_team.club_id,
                    team_name=sent_off_team.name,
                    player_name=sent_off.name,
                    event_type="red_card",
                    description=f"{sent_off.name} sees red as the tension rises.",
                )
            )
        events.sort(key=lambda event: (event.minute, event.team_name, event.player_name))
        winner_club_id = home.club_id if home_goals > away_goals else away.club_id if away_goals > home_goals else None
        favorite = home if home.overall_rating >= away.overall_rating else away
        underdog = away if favorite.club_id == home.club_id else home
        upset = winner_club_id == underdog.club_id and abs(home.overall_rating - away.overall_rating) >= 4
        man_of_the_match = self._pick_man_of_the_match(
            events=events,
            home=home,
            away=away,
            winner_club_id=winner_club_id,
        )
        content_brief = build_content_brief(fixture, storyline, home_club=home, away_club=away)
        match_id = f"match_{fixture.fixture_id}"
        viral_score = self._viral_score(
            home_goals=home_goals,
            away_goals=away_goals,
            storyline=storyline,
            upset=upset,
            events=events,
        )
        commentary_prompt = (
            f"{storyline.commentary_angle} Final score: {home.name} {home_goals}-{away_goals} {away.name}. "
            f"Man of the match: {man_of_the_match}."
        )
        pundit_prompt = (
            f"{storyline.pundit_angle} Use the {home_goals}-{away_goals} scoreline to argue whether this was sustainable or emotional chaos."
        )
        result = MatchResult(
            match_id=match_id,
            league_id=league.league_id,
            fixture_id=fixture.fixture_id,
            round_number=fixture.round_number,
            home_club_id=home.club_id,
            away_club_id=away.club_id,
            home_club_name=home.name,
            away_club_name=away.name,
            home_goals=home_goals,
            away_goals=away_goals,
            winner_club_id=winner_club_id,
            upset=upset,
            man_of_the_match=man_of_the_match,
            storyline=storyline,
            events=tuple(events),
            commentary_prompt=commentary_prompt,
            pundit_prompt=pundit_prompt,
            viral_score=viral_score,
            content_brief=content_brief,
            highlight_payload={},
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
        )

    def simulate_round(
        self,
        *,
        league: League,
        fixtures: Sequence[Fixture],
        previous_results: Sequence[Mapping[str, object]] = (),
    ) -> list[MatchResult]:
        historic_results = [result for result in previous_results if str(result.get("league_id") or "") == league.league_id]
        table_positions: Mapping[str, int] = {}
        if historic_results:
            converted = [
                MatchResult(
                    match_id=str(result["match_id"]),
                    league_id=str(result["league_id"]),
                    fixture_id=str(result["fixture_id"]),
                    round_number=int(result["round_number"]),
                    home_club_id=str(result["home_club_id"]),
                    away_club_id=str(result["away_club_id"]),
                    home_club_name=str(result["home_club_name"]),
                    away_club_name=str(result["away_club_name"]),
                    home_goals=int(result["home_goals"]),
                    away_goals=int(result["away_goals"]),
                    winner_club_id=result.get("winner_club_id"),
                    upset=bool(result.get("upset")),
                    man_of_the_match=str(result["man_of_the_match"]),
                    storyline=StorylineBundle(**dict(result["storyline"])),
                    events=tuple(MatchEvent(**dict(event)) for event in result["events"]),
                    commentary_prompt=str(result["commentary_prompt"]),
                    pundit_prompt=str(result["pundit_prompt"]),
                    viral_score=int(result["viral_score"]),
                    content_brief=dict(result["content_brief"]),
                    highlight_payload=dict(result["highlight_payload"]),
                )
                for result in historic_results
            ]
            table_positions = {row["club_id"]: int(row["position"]) for row in build_table(league=league, results=converted)}
        return [
            self.simulate_fixture(
                league=league,
                fixture=fixture,
                previous_results=previous_results,
                table_positions=table_positions,
            )
            for fixture in fixtures
        ]

    def _goal_rates(
        self,
        *,
        home: GeneratedClub,
        away: GeneratedClub,
        storyline: StorylineBundle,
    ) -> tuple[float, float]:
        home_rate = (
            1.05
            + ((home.attack_rating - away.defense_rating) / 18.0)
            + ((home.midfield_rating - away.midfield_rating) / 32.0)
            + 0.22
        )
        away_rate = (
            0.88
            + ((away.attack_rating - home.defense_rating) / 18.0)
            + ((away.midfield_rating - home.midfield_rating) / 32.0)
        )
        if storyline.rivalry:
            home_rate += 0.12
            away_rate += 0.12
        if storyline.pressure_match:
            home_rate += 0.08
            away_rate += 0.05
        if storyline.underdog:
            if away.overall_rating < home.overall_rating:
                away_rate += 0.10
            else:
                home_rate += 0.10
        return (_clamp(home_rate, 0.25, 4.8), _clamp(away_rate, 0.20, 4.6))

    def _pick_man_of_the_match(
        self,
        *,
        events: Sequence[MatchEvent],
        home: GeneratedClub,
        away: GeneratedClub,
        winner_club_id: str | None,
    ) -> str:
        goal_counts: dict[str, int] = {}
        for event in events:
            if event.event_type != "goal":
                continue
            goal_counts[event.player_name] = goal_counts.get(event.player_name, 0) + 1
        if goal_counts:
            return max(goal_counts, key=lambda name: (goal_counts[name], name))
        if winner_club_id == home.club_id:
            return home.star_player.name
        if winner_club_id == away.club_id:
            return away.star_player.name
        return max((home.star_player, away.star_player), key=lambda player: player.rating).name

    def _viral_score(
        self,
        *,
        home_goals: int,
        away_goals: int,
        storyline: StorylineBundle,
        upset: bool,
        events: Sequence[MatchEvent],
    ) -> int:
        score = 42 + ((home_goals + away_goals) * 6) + storyline.viral_boost
        if upset:
            score += 14
        if home_goals == away_goals:
            score += 5
        if events and events[-1].event_type == "goal" and events[-1].minute >= 80:
            score += 10
        score += sum(1 for event in events if event.event_type == "red_card") * 4
        return int(_clamp(score, 35, 99))

    def _highlight_payload(self, *, result: MatchResult) -> dict[str, object]:
        last_goal = next((event for event in reversed(result.events) if event.event_type == "goal"), None)
        winning_team_name = (
            result.home_club_name
            if result.winner_club_id == result.home_club_id
            else result.away_club_name
            if result.winner_club_id == result.away_club_id
            else result.home_club_name
        )
        opponent_name = result.away_club_name if winning_team_name == result.home_club_name else result.home_club_name
        title = f"{winning_team_name} spark {result.storyline.headline.lower()}"
        if result.winner_club_id is None:
            title = f"{result.home_club_name} and {result.away_club_name} share chaos"
        caption_subject = last_goal.player_name if last_goal is not None else result.man_of_the_match
        return {
            "clip_id": f"clip_{result.match_id}",
            "match_id": result.match_id,
            "title": title,
            "event_type": _result_event_type(result),
            "team_name": winning_team_name,
            "opponent_name": opponent_name,
            "player_name": caption_subject,
            "minute": last_goal.minute if last_goal is not None else 90,
            "viral_score": result.viral_score,
            "duration": min(29, 16 + len(result.events) + (3 if result.storyline.rivalry else 0)),
            "video_path": f"generated/{result.match_id}/raw.mp4",
            "polished_video_path": f"generated/{result.match_id}/polished.mp4",
            "raw_caption": f"{caption_subject} just flipped the script in {result.home_club_name} vs {result.away_club_name}",
            "polished_caption": f"{title.title()} after a {result.home_goals}-{result.away_goals} finish",
            "publish_polished": True,
            "metadata": {
                "story_tags": list(result.storyline.tags),
                "commentary_prompt": result.commentary_prompt,
                "pundit_prompt": result.pundit_prompt,
                "man_of_the_match": result.man_of_the_match,
            },
        }
