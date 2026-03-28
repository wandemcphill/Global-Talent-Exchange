from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import random
from typing import Iterable


_CITY_NAMES = (
    "Lagos",
    "Abuja",
    "Kano",
    "Port Harcourt",
    "Ibadan",
    "Benin",
    "Enugu",
    "Jos",
    "Kaduna",
    "Ilorin",
    "Uyo",
    "Owerri",
    "Abeokuta",
    "Calabar",
    "Asaba",
    "Akure",
    "Maiduguri",
    "Warri",
    "Onitsha",
    "Lokoja",
)
_CLUB_SUFFIXES = (
    "Titans",
    "Storm",
    "Warriors",
    "Dynamos",
    "Giants",
    "Falcons",
    "Rovers",
    "Athletic",
    "Comets",
    "Guardians",
    "Phoenix",
    "Alliance",
)
_STYLES = ("attacking", "defensive", "balanced", "counter", "pressing")
_POSITIONS = (
    "GK",
    "RB",
    "LB",
    "CB",
    "CB",
    "DM",
    "CM",
    "CM",
    "RW",
    "LW",
    "ST",
    "GK",
    "RB",
    "LB",
    "CB",
    "DM",
    "CM",
    "AM",
    "RW",
    "LW",
    "ST",
    "CB",
    "CM",
)
_FIRST_NAMES = (
    "Ayo",
    "Musa",
    "Chinedu",
    "Tunde",
    "Kelechi",
    "Ibrahim",
    "Samuel",
    "Daniel",
    "Emeka",
    "Sodiq",
    "Femi",
    "Tari",
    "Bassey",
    "Amina",
    "Ifeanyi",
    "Bola",
    "Mofe",
    "Amara",
    "Tobi",
    "Eno",
)
_LAST_NAMES = (
    "Bello",
    "Okafor",
    "Balogun",
    "Adeleke",
    "Umar",
    "Eze",
    "Adeyemi",
    "Nwosu",
    "Danjuma",
    "Ojo",
    "Ighalo",
    "Ekong",
    "Onyeka",
    "Sule",
    "Anyanwu",
    "Etim",
    "Akpan",
    "Afolabi",
    "Garba",
    "Idowu",
)
_NATIONALITIES = (
    "Nigeria",
    "Ghana",
    "Cameroon",
    "Ivory Coast",
    "Senegal",
    "Benin",
    "Togo",
)
_TRAITS = (
    "clinical finisher",
    "set-piece threat",
    "box-to-box engine",
    "ball-playing defender",
    "press resistant",
    "crowd favorite",
    "captain material",
    "academy jewel",
    "transition runner",
    "big-game performer",
)
_STYLE_MODIFIERS = {
    "attacking": (4, 1, -1),
    "defensive": (-1, 1, 4),
    "balanced": (1, 1, 1),
    "counter": (2, 0, 2),
    "pressing": (2, 3, 0),
}


def _average(values: Iterable[int]) -> int:
    items = tuple(values)
    if not items:
        return 0
    return int(round(sum(items) / len(items)))


def _digest_id(*parts: object, prefix: str) -> str:
    seed = "|".join(str(part).strip().lower() for part in parts if str(part).strip())
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


@dataclass(frozen=True, slots=True)
class GeneratedPlayer:
    player_id: str
    club_id: str
    name: str
    position: str
    rating: int
    potential: int
    age: int
    nationality: str
    traits: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GeneratedClub:
    club_id: str
    name: str
    city: str
    style: str
    fanbase: int
    colors: tuple[str, str]
    roster: tuple[GeneratedPlayer, ...]

    @property
    def overall_rating(self) -> int:
        starting_eleven = tuple(sorted((player.rating for player in self.roster), reverse=True)[:11])
        return _average(starting_eleven)

    @property
    def attack_rating(self) -> int:
        positions = {"ST", "RW", "LW", "AM", "CM"}
        base = _average(player.rating for player in self.roster if player.position in positions)
        return max(40, base + _STYLE_MODIFIERS[self.style][0])

    @property
    def midfield_rating(self) -> int:
        positions = {"DM", "CM", "AM"}
        base = _average(player.rating for player in self.roster if player.position in positions)
        return max(40, base + _STYLE_MODIFIERS[self.style][1])

    @property
    def defense_rating(self) -> int:
        positions = {"GK", "RB", "LB", "CB", "DM"}
        base = _average(player.rating for player in self.roster if player.position in positions)
        return max(40, base + _STYLE_MODIFIERS[self.style][2])

    @property
    def star_player(self) -> GeneratedPlayer:
        return max(self.roster, key=lambda player: (player.rating, player.potential, -player.age))

    def as_dict(self) -> dict[str, object]:
        return {
            "club_id": self.club_id,
            "name": self.name,
            "city": self.city,
            "style": self.style,
            "fanbase": self.fanbase,
            "colors": list(self.colors),
            "overall_rating": self.overall_rating,
            "attack_rating": self.attack_rating,
            "midfield_rating": self.midfield_rating,
            "defense_rating": self.defense_rating,
            "star_player": self.star_player.as_dict(),
            "roster": [player.as_dict() for player in self.roster],
        }


class UniverseGenerator:
    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)
        self._used_club_names: set[str] = set()

    def generate_player(
        self,
        *,
        club_id: str,
        index: int,
        position: str | None = None,
    ) -> GeneratedPlayer:
        resolved_position = position or self._random.choice(_POSITIONS)
        age = self._random.randint(17, 34)
        base_rating = self._random.randint(58, 91)
        if resolved_position in {"ST", "RW", "LW", "AM"}:
            base_rating += self._random.randint(0, 3)
        if resolved_position == "GK":
            base_rating += self._random.randint(-1, 2)
        rating = max(50, min(base_rating, 94))
        potential = max(rating + self._random.randint(1, 4), self._random.randint(70, 99))
        first_name = self._random.choice(_FIRST_NAMES)
        last_name = self._random.choice(_LAST_NAMES)
        name = f"{first_name} {last_name}"
        traits = tuple(sorted(self._random.sample(_TRAITS, k=self._random.randint(1, 2))))
        player_id = _digest_id(club_id, name, index, prefix="ply")
        return GeneratedPlayer(
            player_id=player_id,
            club_id=club_id,
            name=name,
            position=resolved_position,
            rating=rating,
            potential=min(potential, 99),
            age=age,
            nationality=self._random.choice(_NATIONALITIES),
            traits=traits,
        )

    def generate_roster(self, *, club_id: str, size: int = 23) -> tuple[GeneratedPlayer, ...]:
        positions = list(_POSITIONS[: max(size, 1)])
        if size > len(positions):
            positions.extend(self._random.choice(_POSITIONS) for _ in range(size - len(positions)))
        return tuple(
            self.generate_player(club_id=club_id, index=index, position=positions[index])
            for index in range(size)
        )

    def generate_club(
        self,
        *,
        name: str | None = None,
        city: str | None = None,
        style: str | None = None,
        squad_size: int = 23,
    ) -> GeneratedClub:
        resolved_name, resolved_city = self._resolve_club_name(name=name, city=city)
        club_id = _digest_id(resolved_name, resolved_city, prefix="club")
        resolved_style = style or self._random.choice(_STYLES)
        colors = self._random.choice(
            (
                ("green", "white"),
                ("blue", "gold"),
                ("red", "black"),
                ("maroon", "cream"),
                ("navy", "silver"),
                ("orange", "charcoal"),
            )
        )
        fanbase = self._random.randint(25_000, 1_200_000)
        roster = self.generate_roster(club_id=club_id, size=squad_size)
        return GeneratedClub(
            club_id=club_id,
            name=resolved_name,
            city=resolved_city,
            style=resolved_style,
            fanbase=fanbase,
            colors=colors,
            roster=roster,
        )

    def generate_clubs(self, count: int = 20, *, squad_size: int = 23) -> list[GeneratedClub]:
        return [self.generate_club(squad_size=squad_size) for _ in range(max(count, 1))]

    def _resolve_club_name(self, *, name: str | None, city: str | None) -> tuple[str, str]:
        if name:
            resolved_name = name.strip()
            resolved_city = city.strip() if city else resolved_name.split(" ", 1)[0]
            self._used_club_names.add(resolved_name.lower())
            return resolved_name, resolved_city
        for _ in range(500):
            resolved_city = city or self._random.choice(_CITY_NAMES)
            resolved_name = f"{resolved_city} {self._random.choice(_CLUB_SUFFIXES)}"
            if resolved_name.lower() not in self._used_club_names:
                self._used_club_names.add(resolved_name.lower())
                return resolved_name, resolved_city
        fallback_city = city or self._random.choice(_CITY_NAMES)
        resolved_name = f"{fallback_city} FC {len(self._used_club_names) + 1}"
        self._used_club_names.add(resolved_name.lower())
        return resolved_name, fallback_city


def generate_club(seed: int | None = None) -> dict[str, object]:
    generator = UniverseGenerator(seed=seed)
    return generator.generate_club().as_dict()


def generate_player(seed: int | None = None) -> dict[str, object]:
    generator = UniverseGenerator(seed=seed)
    club = generator.generate_club()
    return generator.generate_player(club_id=club.club_id, index=0).as_dict()
