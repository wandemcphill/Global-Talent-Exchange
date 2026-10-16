from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Sequence

from services.universe.generator import GeneratedClub


def _fixture_id(round_number: int, leg: int, home_club_id: str, away_club_id: str) -> str:
    digest = hashlib.sha1(f"{round_number}|{leg}|{home_club_id}|{away_club_id}".encode("utf-8")).hexdigest()[:12]
    return f"fix_{digest}"


@dataclass(frozen=True, slots=True)
class Fixture:
    fixture_id: str
    round_number: int
    leg: int
    home_club_id: str
    away_club_id: str
    home_club_name: str
    away_club_name: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def generate_fixtures(clubs: Sequence[GeneratedClub], *, home_and_away: bool = True) -> list[Fixture]:
    if len(clubs) < 2:
        return []
    rotation: list[GeneratedClub | None] = list(clubs)
    if len(rotation) % 2 == 1:
        rotation.append(None)
    round_count = len(rotation) - 1
    pairings_by_round: list[list[tuple[GeneratedClub, GeneratedClub]]] = []
    for round_index in range(round_count):
        pairings: list[tuple[GeneratedClub, GeneratedClub]] = []
        for index in range(len(rotation) // 2):
            left = rotation[index]
            right = rotation[-(index + 1)]
            if left is None or right is None:
                continue
            home, away = (left, right) if (round_index + index) % 2 == 0 else (right, left)
            pairings.append((home, away))
        pairings_by_round.append(pairings)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    fixtures: list[Fixture] = []
    for round_number, pairings in enumerate(pairings_by_round, start=1):
        for home, away in pairings:
            fixtures.append(
                Fixture(
                    fixture_id=_fixture_id(round_number, 1, home.club_id, away.club_id),
                    round_number=round_number,
                    leg=1,
                    home_club_id=home.club_id,
                    away_club_id=away.club_id,
                    home_club_name=home.name,
                    away_club_name=away.name,
                )
            )
    if not home_and_away:
        return fixtures
    second_leg_offset = len(pairings_by_round)
    for round_number, pairings in enumerate(pairings_by_round, start=1):
        for home, away in pairings:
            fixtures.append(
                Fixture(
                    fixture_id=_fixture_id(round_number + second_leg_offset, 2, away.club_id, home.club_id),
                    round_number=round_number + second_leg_offset,
                    leg=2,
                    home_club_id=away.club_id,
                    away_club_id=home.club_id,
                    home_club_name=away.name,
                    away_club_name=home.name,
                )
            )
    return fixtures


def fixtures_by_round(fixtures: Sequence[Fixture]) -> dict[int, list[Fixture]]:
    grouped: dict[int, list[Fixture]] = {}
    for fixture in fixtures:
        grouped.setdefault(fixture.round_number, []).append(fixture)
    return grouped
