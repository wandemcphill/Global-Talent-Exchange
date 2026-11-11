"""Regional division pyramid.

Clubs share a continent and a division. Each group is cut into seasons of
``LEAGUE_GROUP_SIZE``. A club left alone does not get a fixture list. Promotion
and relegation move one step. Entry is free, so a buy-in cannot decide the division.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.competition_constants import LEAGUE_GROUP_SIZE

DIVISION_LADDER: tuple[str, ...] = (
    "foundation",
    "division_7",
    "division_6",
    "division_5",
    "division_4",
    "division_3",
    "division_2",
    "division_1",
)

# Kept so older callers can read a tier, but every division is free.
# This map must not decide who may enter or how prize coin is funded.
DIVISION_BUY_IN: dict[str, int] = {level: 0 for level in DIVISION_LADDER}

SHORT_CALENDAR_LEVELS = frozenset({"foundation", "division_7"})


@dataclass(frozen=True, slots=True)
class PyramidClub:
    club_id: str
    club_name: str
    division_level: str = "foundation"
    region_code: str = "UNASSIGNED"
    strength_rating: int = 0


@dataclass(frozen=True, slots=True)
class DivisionCohort:
    region_code: str
    division_level: str
    cohort_index: int
    parent_level: str | None
    child_level: str | None
    buy_in_tier: int
    single_round: bool
    clubs: tuple[PyramidClub, ...]
    idle: bool


def normalize_division(level: str | None) -> str:
    normalized = str(level or "foundation").strip().lower()
    if normalized not in DIVISION_LADDER:
        return "foundation"
    return normalized


def normalize_region(region_code: str | None) -> str:
    normalized = str(region_code or "").strip().upper()
    return normalized or "UNASSIGNED"


def parent_level(level: str) -> str | None:
    current = normalize_division(level)
    index = DIVISION_LADDER.index(current)
    if index >= len(DIVISION_LADDER) - 1:
        return None
    return DIVISION_LADDER[index + 1]


def child_level(level: str) -> str | None:
    current = normalize_division(level)
    index = DIVISION_LADDER.index(current)
    if index == 0:
        return None
    return DIVISION_LADDER[index - 1]


def next_division_level(current: str, *, final_position: int, field_size: int) -> str:
    """One step up for the top three, one step down for the bottom three."""
    level = normalize_division(current)
    index = DIVISION_LADDER.index(level)
    if field_size >= 4 and final_position <= 3:
        index = min(index + 1, len(DIVISION_LADDER) - 1)
    elif field_size >= 4 and final_position > field_size - 3 and index > 0:
        index -= 1
    return DIVISION_LADDER[index]


def plan_division_cohorts(
    clubs: tuple[PyramidClub, ...] | list[PyramidClub],
    *,
    group_size: int = LEAGUE_GROUP_SIZE,
) -> tuple[DivisionCohort, ...]:
    grouped: dict[tuple[str, str], list[PyramidClub]] = {}
    for club in clubs:
        level = normalize_division(club.division_level)
        region = normalize_region(club.region_code)
        grouped.setdefault((region, level), []).append(
            PyramidClub(
                club_id=club.club_id,
                club_name=club.club_name,
                division_level=level,
                region_code=region,
                strength_rating=club.strength_rating,
            )
        )
    cohorts: list[DivisionCohort] = []
    size = max(2, group_size)
    for region, level in sorted(grouped):
        members = tuple(sorted(grouped[(region, level)], key=lambda item: item.club_id))
        chunks = [members[start : start + size] for start in range(0, len(members), size)]
        for index, chunk in enumerate(chunks):
            cohorts.append(
                DivisionCohort(
                    region_code=region,
                    division_level=level,
                    cohort_index=index,
                    parent_level=parent_level(level),
                    child_level=child_level(level),
                    buy_in_tier=0,
                    single_round=level in SHORT_CALENDAR_LEVELS,
                    clubs=tuple(chunk),
                    idle=len(chunk) < 2,
                )
            )
    return tuple(cohorts)


def rollover_clubs(
    seasons,
    idle_cohorts: tuple[DivisionCohort, ...] | list[DivisionCohort] = (),
    waiting: tuple[PyramidClub, ...] | list[PyramidClub] = (),
) -> tuple[PyramidClub, ...]:
    """Build next season's clubs from a finished table. Unfinished seasons stay put."""
    rolled: list[PyramidClub] = []
    for season in seasons:
        level = str(getattr(season, "division_level", "") or "")
        if not level:
            continue
        region = normalize_region(getattr(season, "region_code", ""))
        ratings = {club.club_id: club.strength_rating for club in season.clubs}
        if getattr(season, "status", None) != "completed":
            rolled.extend(
                PyramidClub(
                    club_id=club.club_id,
                    club_name=club.club_name,
                    division_level=normalize_division(level),
                    region_code=region,
                    strength_rating=club.strength_rating,
                )
                for club in season.clubs
            )
            continue
        field_size = len(season.standings) or len(season.clubs)
        for row in season.standings:
            rolled.append(
                PyramidClub(
                    club_id=row.club_id,
                    club_name=row.club_name,
                    division_level=next_division_level(
                        level,
                        final_position=int(row.position),
                        field_size=field_size,
                    ),
                    region_code=region,
                    strength_rating=int(ratings.get(row.club_id, 0)),
                )
            )
    for cohort in idle_cohorts:
        rolled.extend(cohort.clubs)
    seen = {club.club_id for club in rolled}
    for club in waiting:
        if club.club_id not in seen:
            rolled.append(club)
            seen.add(club.club_id)
    return tuple(rolled)
