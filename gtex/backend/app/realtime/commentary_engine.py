from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import random
from threading import RLock
from typing import Any, Iterable

DEFAULT_STYLE = "broadcast"

STYLE_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "broadcast": {
        "goal": [
            "GOAL! {player} finds the net in the {minute_ordinal} minute!",
            "GOAL! {player} strikes in the {minute_ordinal} minute!",
            "{player} with a thunderbolt in the {minute_ordinal} minute! The net ripples!",
            "Clinical finish from {player} in the {minute_ordinal} minute! That's brilliance!",
        ],
        "miss": [
            "{player} misses! That was a golden chance in the {minute_ordinal} minute!",
            "So close! The crowd gasps as it flies wide in the {minute_ordinal} minute!",
            "{player} can't keep the effort down in the {minute_ordinal} minute!",
        ],
        "save": [
            "What a save by {player} in the {minute_ordinal} minute!",
            "{player} stands tall to deny the chance in the {minute_ordinal} minute!",
            "{player} gets down quickly and keeps it out in the {minute_ordinal} minute!",
        ],
        "pass": [
            "{player} threads a clever pass in the {minute_ordinal} minute.",
            "Sharp vision from {player} with that pass in the {minute_ordinal} minute.",
            "{player} opens the defense with a measured pass in the {minute_ordinal} minute.",
        ],
        "foul": [
            "The whistle goes as {player} commits the foul in the {minute_ordinal} minute.",
            "{player} is late to the challenge and it's a foul in the {minute_ordinal} minute.",
            "Referee stops play for a foul by {player} in the {minute_ordinal} minute.",
        ],
        "kickoff": [
            "Kickoff. {home_team} get this one started against {away_team}.",
            "We're underway as {home_team} face {away_team}.",
        ],
        "halftime": [
            "Halftime. {home_team} {home_score}-{away_score} {away_team}.",
            "The first half closes with {home_team} {home_score}-{away_score} {away_team}.",
        ],
        "fulltime": [
            "Fulltime. {home_team} {home_score}-{away_score} {away_team}.",
            "That's the final whistle: {home_team} {home_score}-{away_score} {away_team}.",
        ],
        "generic": [
            "{team} keep the move alive in the {minute_ordinal} minute.",
            "Another telling moment arrives in the {minute_ordinal} minute.",
            "The match swings again in the {minute_ordinal} minute.",
        ],
    },
    "hype": {
        "goal": [
            "GOAL! {player} ignites the stadium in the {minute_ordinal} minute!",
            "Pandemonium! {player} buries it in the {minute_ordinal} minute!",
            "{player} explodes onto the scoresheet in the {minute_ordinal} minute!",
        ],
        "miss": [
            "Agony! {player} lets one slip in the {minute_ordinal} minute!",
            "The stadium gasps as {player} misses in the {minute_ordinal} minute!",
            "{player} was inches away in the {minute_ordinal} minute!",
        ],
        "save": [
            "Heroics from {player} in the {minute_ordinal} minute!",
            "{player} throws everything at it and makes the save!",
            "An unbelievable stop from {player} in the {minute_ordinal} minute!",
        ],
        "pass": [
            "{player} slices the defense open with a dazzling pass!",
            "That pass from {player} tears the shape apart!",
            "{player} spots the run and unlocks everything!",
        ],
        "foul": [
            "{player} crashes into the challenge and the referee has seen enough!",
            "Tempers flare as {player} brings the move down!",
            "{player} leaves one on the opponent and the whistle follows!",
        ],
        "generic": [
            "The intensity keeps climbing in this match!",
            "Another surge of drama races through the stadium!",
        ],
    },
    "analyst": {
        "goal": [
            "{player} converts the chance in the {minute_ordinal} minute and changes the game state.",
            "{player} turns pressure into a goal in the {minute_ordinal} minute.",
            "{player} finishes the sequence efficiently in the {minute_ordinal} minute.",
        ],
        "miss": [
            "{player} fails to convert a promising opening in the {minute_ordinal} minute.",
            "That miss from {player} will register as a wasted opportunity.",
            "{player} cannot capitalize in the {minute_ordinal} minute.",
        ],
        "save": [
            "{player} preserves the structure with an important save.",
            "{player} protects the scoreline with a controlled stop.",
            "{player} reads the action early and secures the save.",
        ],
        "pass": [
            "{player} advances the attack with a progressive pass.",
            "{player} improves the angle with a well-timed pass.",
            "{player} moves the block with a precise forward pass.",
        ],
        "foul": [
            "{player} stops the phase and concedes the foul.",
            "The foul from {player} interrupts the attacking rhythm.",
            "{player} accepts the foul to halt the sequence.",
        ],
        "kickoff": [
            "Kickoff marks the start of the tactical contest between {home_team} and {away_team}.",
        ],
        "halftime": [
            "The interval arrives with {home_team} {home_score}-{away_score} {away_team}.",
        ],
        "fulltime": [
            "The match closes at {home_team} {home_score}-{away_score} {away_team}.",
        ],
        "generic": [
            "The phase changes and the tactical picture shifts again.",
            "Another sequence alters the control profile of the match.",
        ],
    },
}


def ordinal(value: int) -> str:
    absolute = abs(int(value))
    if 10 <= absolute % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(absolute % 10, "th")
    return f"{value}{suffix}"


@dataclass(slots=True)
class CommentaryEngine:
    rng: random.Random = field(default_factory=random.Random)
    recent_window: int = 3
    _recent_templates: dict[tuple[str, str, str], deque[str]] = field(default_factory=lambda: defaultdict(deque))
    _lock: RLock = field(default_factory=RLock)

    def styles(self) -> tuple[str, ...]:
        return tuple(STYLE_TEMPLATES.keys())

    def render(self, event: dict[str, Any], *, match_id: str, style: str = DEFAULT_STYLE) -> str:
        resolved_style = self.resolve_style(style)
        event_type = self._normalize_event_type(event.get("type"))
        templates = STYLE_TEMPLATES.get(resolved_style, {}).get(event_type)
        if not templates:
            templates = STYLE_TEMPLATES.get(resolved_style, {}).get("generic", [])
        if not templates:
            templates = STYLE_TEMPLATES[DEFAULT_STYLE]["generic"]

        template = self._choose_template(match_id=match_id, style=resolved_style, event_type=event_type, templates=templates)
        context = self._build_context(event)
        return template.format(**context)

    def render_variations(self, event: dict[str, Any], *, match_id: str) -> dict[str, str]:
        return {
            style: self.render(event, match_id=match_id, style=style)
            for style in self.styles()
        }

    @staticmethod
    def resolve_style(style: str | None) -> str:
        candidate = str(style or DEFAULT_STYLE).strip().lower()
        return candidate if candidate in STYLE_TEMPLATES else DEFAULT_STYLE

    def _choose_template(
        self,
        *,
        match_id: str,
        style: str,
        event_type: str,
        templates: Iterable[str],
    ) -> str:
        options = list(templates)
        if len(options) == 1:
            return options[0]

        key = (match_id, style, event_type)
        with self._lock:
            recent = self._recent_templates[key]
            available = [option for option in options if option not in recent] or options
            selected = self.rng.choice(available)
            recent.append(selected)
            while len(recent) > self.recent_window:
                recent.popleft()
            return selected

    @staticmethod
    def _normalize_event_type(value: Any) -> str:
        candidate = str(value or "generic").strip().lower()
        aliases = {
            "goalkeeper_save": "save",
            "double_save": "save",
            "penalty_missed": "save",
            "penalty_miss": "miss",
            "penalty_scored": "goal",
            "penalty_goal": "goal",
            "missed_chance": "miss",
            "missed_big_chance": "miss",
            "shot_on_target": "generic",
            "shot": "generic",
            "dangerous_attack": "generic",
            "counter_attack": "generic",
            "possession_swing": "generic",
            "substitution": "generic",
            "substitution_impact": "generic",
            "tactical_swing": "generic",
            "tactical_change": "generic",
            "offside": "generic",
            "injury": "generic",
            "yellow_card": "foul",
            "red_card": "foul",
            "tactical_foul": "foul",
            "woodwork": "miss",
        }
        return aliases.get(candidate, candidate)

    @staticmethod
    def _build_context(event: dict[str, Any]) -> dict[str, Any]:
        minute = int(event.get("minute") or 0)
        player = str(event.get("player") or event.get("secondary_player") or "A player")
        team = str(event.get("team") or event.get("club_name") or "the side")
        home_team = str(event.get("home_team") or "Home")
        away_team = str(event.get("away_team") or "Away")
        return {
            "minute": minute,
            "minute_ordinal": ordinal(minute),
            "player": player,
            "secondary_player": str(event.get("secondary_player") or "the opponent"),
            "team": team,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": int(event.get("home_score") or 0),
            "away_score": int(event.get("away_score") or 0),
        }


__all__ = ["CommentaryEngine", "DEFAULT_STYLE", "STYLE_TEMPLATES", "ordinal"]
