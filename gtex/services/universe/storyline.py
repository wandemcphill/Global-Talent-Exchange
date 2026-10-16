from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from services.universe.generator import GeneratedClub
from services.universe.scheduler import Fixture


@dataclass(frozen=True, slots=True)
class StorylineBundle:
    rivalry: bool
    revenge_match: bool
    underdog: bool
    pressure_match: bool
    title_race: bool
    headline: str
    hook: str
    commentary_angle: str
    pundit_angle: str
    viral_boost: int
    tags: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _club_strength_gap(home: GeneratedClub, away: GeneratedClub) -> int:
    return home.overall_rating - away.overall_rating


def _detect_revenge_match(
    *,
    fixture: Fixture,
    previous_results: Sequence[Mapping[str, object]],
) -> bool:
    for result in reversed(tuple(previous_results)):
        home_id = str(result.get("home_club_id") or "")
        away_id = str(result.get("away_club_id") or "")
        if {home_id, away_id} != {fixture.home_club_id, fixture.away_club_id}:
            continue
        winner_club_id = result.get("winner_club_id")
        margin = abs(int(result.get("home_goals") or 0) - int(result.get("away_goals") or 0))
        if winner_club_id in {fixture.home_club_id, fixture.away_club_id} and margin >= 2:
            return True
    return False


def inject_storylines(
    fixture: Fixture,
    clubs_by_id: Mapping[str, GeneratedClub],
    *,
    previous_results: Sequence[Mapping[str, object]] = (),
    table_positions: Mapping[str, int] | None = None,
) -> StorylineBundle:
    home = clubs_by_id[fixture.home_club_id]
    away = clubs_by_id[fixture.away_club_id]
    gap = _club_strength_gap(home, away)
    weaker = away if gap >= 0 else home
    stronger = home if gap >= 0 else away
    same_city = home.city.lower() == away.city.lower()
    fanbase_collision = abs(home.fanbase - away.fanbase) <= 225_000 and (home.fanbase + away.fanbase) >= 850_000
    rivalry = same_city or fanbase_collision
    revenge_match = _detect_revenge_match(fixture=fixture, previous_results=previous_results)
    underdog = abs(gap) >= 4
    if table_positions:
        title_race = table_positions.get(home.club_id, 99) <= 4 and table_positions.get(away.club_id, 99) <= 4
    else:
        title_race = False
    pressure_match = title_race or home.fanbase >= 700_000 or away.fanbase >= 700_000 or rivalry
    headline_bits: list[str] = []
    tags: list[str] = []
    if rivalry:
        headline_bits.append("rivalry")
        tags.append("rivalry")
    if revenge_match:
        headline_bits.append("revenge")
        tags.append("revenge")
    if underdog:
        headline_bits.append("underdog")
        tags.append("underdog")
    if title_race:
        headline_bits.append("title race")
        tags.append("title-race")
    if not headline_bits:
        headline_bits.append("statement")
        tags.append("statement-game")
    storyline_label = " / ".join(headline_bits)
    headline = f"{home.name} vs {away.name}: {storyline_label.title()} Night"
    if underdog:
        hook = f"{weaker.name} enter as the underdog against {stronger.name}, with one big result enough to flip the narrative."
    elif rivalry:
        hook = f"{home.name} and {away.name} bring a crowd-heavy rivalry into a match that should feel bigger than the table."
    elif title_race:
        hook = f"Both clubs are in the hunt, so dropped points here will immediately change the title picture."
    else:
        hook = f"This is a momentum match for two clubs trying to write the next chapter of the GTEX universe."
    commentary_angle = (
        f"Lean into the {storyline_label} tension, mention {weaker.name if underdog else home.name}, and frame every big chance as a swing in the wider league narrative."
    )
    pundit_angle = (
        f"Debate whether {stronger.name if underdog else home.name} handled the pressure and whether this result changes expectations for the rest of the season."
    )
    viral_boost = 6
    viral_boost += 10 if rivalry else 0
    viral_boost += 8 if revenge_match else 0
    viral_boost += 9 if underdog else 0
    viral_boost += 7 if title_race else 0
    return StorylineBundle(
        rivalry=rivalry,
        revenge_match=revenge_match,
        underdog=underdog,
        pressure_match=pressure_match,
        title_race=title_race,
        headline=headline,
        hook=hook,
        commentary_angle=commentary_angle,
        pundit_angle=pundit_angle,
        viral_boost=viral_boost,
        tags=tuple(tags),
    )


def build_content_brief(
    fixture: Fixture,
    storyline: StorylineBundle,
    *,
    home_club: GeneratedClub,
    away_club: GeneratedClub,
) -> dict[str, object]:
    return {
        "match_id": fixture.fixture_id,
        "headline": storyline.headline,
        "hook": storyline.hook,
        "story_tags": list(storyline.tags),
        "commentary_prompt": storyline.commentary_angle,
        "pundit_prompt": storyline.pundit_angle,
        "narrative_flags": {
            "rivalry": storyline.rivalry,
            "revenge_match": storyline.revenge_match,
            "underdog": storyline.underdog,
            "pressure_match": storyline.pressure_match,
            "title_race": storyline.title_race,
        },
        "clubs": [home_club.as_dict(), away_club.as_dict()],
        "viral_score_boost": storyline.viral_boost,
    }
