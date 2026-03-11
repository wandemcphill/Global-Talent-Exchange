from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
import random
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, insert, or_, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, load_settings

from .models import (
    Club,
    Competition,
    Country,
    InjuryStatus,
    InternalLeague,
    LiquidityBand,
    MarketSignal,
    Match,
    Player,
    PlayerClubTenure,
    PlayerImageMetadata,
    PlayerMatchStat,
    PlayerSeasonStat,
    PlayerVerification,
    Season,
    SupplyTier,
    TeamStanding,
    VerificationStatus,
)

PHASE_THREE_REFERENCE_DATE = date(2026, 3, 11)
PHASE_THREE_PROVIDER_NAME = "phase3-universe"

CATALOG_INTERNAL_LEAGUES: tuple[dict[str, Any], ...] = (
    {
        "code": "league_a",
        "name": "League A",
        "rank": 1,
        "competition_multiplier": 1.20,
        "visibility_weight": 1.00,
        "description": "Highest-visibility competitions in the tradable universe.",
        "is_active": True,
    },
    {
        "code": "league_b",
        "name": "League B",
        "rank": 2,
        "competition_multiplier": 1.10,
        "visibility_weight": 0.85,
        "description": "Strong professional competitions with meaningful market demand.",
        "is_active": True,
    },
    {
        "code": "league_c",
        "name": "League C",
        "rank": 3,
        "competition_multiplier": 1.05,
        "visibility_weight": 0.70,
        "description": "Broadly tradable competitions with moderate liquidity expectations.",
        "is_active": True,
    },
    {
        "code": "league_d",
        "name": "League D",
        "rank": 4,
        "competition_multiplier": 0.95,
        "visibility_weight": 0.55,
        "description": "Developmental competitions with narrower demand and slower repricing.",
        "is_active": True,
    },
    {
        "code": "league_e",
        "name": "League E",
        "rank": 5,
        "competition_multiplier": 0.85,
        "visibility_weight": 0.40,
        "description": "Long-tail competitions retained for full-universe coverage.",
        "is_active": True,
    },
)

FORMAT_TARGET_SHARES = {
    "domestic_league": 0.78,
    "academy_league": 0.08,
    "reserve_league": 0.08,
    "pathway_league": 0.06,
}

FORMAT_MIN_PLAYERS = {
    "domestic_league": 260,
    "academy_league": 120,
    "reserve_league": 120,
    "pathway_league": 100,
}

CLUBS_PER_COMPETITION = {
    ("domestic_league", 1): 24,
    ("domestic_league", 2): 22,
    ("domestic_league", 3): 20,
    ("domestic_league", 4): 18,
    ("academy_league", None): 16,
    ("reserve_league", None): 16,
    ("pathway_league", None): 14,
}

MIN_PLAYERS_PER_CLUB = {
    "domestic_league": 28,
    "academy_league": 20,
    "reserve_league": 20,
    "pathway_league": 18,
}

FORMAT_DISPLAY_NAMES = {
    "academy_league": "Academy",
    "reserve_league": "Reserve",
    "pathway_league": "Pathway",
}

COMPETITION_WEIGHT_BY_LEVEL = {
    1: 1.45,
    2: 1.20,
    3: 1.02,
    4: 0.82,
}

FORMAT_WEIGHT_MULTIPLIERS = {
    "academy_league": 1.18,
    "reserve_league": 1.05,
    "pathway_league": 0.95,
}

POSITION_ARCHETYPES: tuple[dict[str, Any], ...] = (
    {"position": "Goalkeeper", "normalized": "goalkeeper", "weight": 0.08, "height": (184, 202), "weight_kg": (75, 94)},
    {"position": "Centre-Back", "normalized": "defender", "weight": 0.16, "height": (183, 198), "weight_kg": (73, 92)},
    {"position": "Full-Back", "normalized": "defender", "weight": 0.12, "height": (170, 188), "weight_kg": (64, 82)},
    {"position": "Defensive Midfielder", "normalized": "midfielder", "weight": 0.10, "height": (175, 192), "weight_kg": (68, 86)},
    {"position": "Central Midfielder", "normalized": "midfielder", "weight": 0.16, "height": (172, 190), "weight_kg": (66, 84)},
    {"position": "Attacking Midfielder", "normalized": "midfielder", "weight": 0.08, "height": (168, 186), "weight_kg": (62, 80)},
    {"position": "Winger", "normalized": "forward", "weight": 0.14, "height": (166, 184), "weight_kg": (60, 78)},
    {"position": "Striker", "normalized": "forward", "weight": 0.16, "height": (175, 196), "weight_kg": (68, 88)},
)


@dataclass(frozen=True, slots=True)
class CountrySpec:
    slug: str
    name: str
    alpha2_code: str
    alpha3_code: str
    fifa_code: str
    confederation_code: str
    market_region: str
    name_region: str
    youth_export_weight: float
    senior_tiers: tuple[int, ...]
    priority_youth_export: bool
    include_pathways: bool


@dataclass(frozen=True, slots=True)
class CompetitionSeed:
    id: str
    country_slug: str
    country_name: str
    provider_external_id: str
    name: str
    slug: str
    code: str
    format_type: str
    age_bracket: str
    domestic_level: int | None
    internal_league_code: str
    weight: float


@dataclass(frozen=True, slots=True)
class ClubSeed:
    id: str
    competition_id: str
    competition_external_id: str
    competition_name: str
    country_slug: str
    country_name: str
    provider_external_id: str
    name: str
    short_name: str
    code: str
    format_type: str
    domestic_level: int | None
    internal_league_code: str
    weight: float


@dataclass(frozen=True, slots=True)
class UniverseSeedSummary:
    provider_name: str
    target_player_count: int
    countries_created: int
    competitions_created: int
    seasons_created: int
    clubs_created: int
    players_created: int
    verifications_created: int
    tenures_created: int
    all_players_tradable: bool
    all_players_verified: bool
    duplicate_identity_count: int
    youth_players_under_24: int
    priority_country_players: int
    players_by_age_bucket: dict[str, int]
    players_by_competition_format: dict[str, int]
    players_by_country: dict[str, int]
    players_by_supply_tier: dict[str, int]
    players_by_liquidity_band: dict[str, int]
    mandatory_country_tier_coverage: dict[str, int]
    academy_reserve_pathway_players: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "target_player_count": self.target_player_count,
            "countries_created": self.countries_created,
            "competitions_created": self.competitions_created,
            "seasons_created": self.seasons_created,
            "clubs_created": self.clubs_created,
            "players_created": self.players_created,
            "verifications_created": self.verifications_created,
            "tenures_created": self.tenures_created,
            "all_players_tradable": self.all_players_tradable,
            "all_players_verified": self.all_players_verified,
            "duplicate_identity_count": self.duplicate_identity_count,
            "youth_players_under_24": self.youth_players_under_24,
            "priority_country_players": self.priority_country_players,
            "players_by_age_bucket": self.players_by_age_bucket,
            "players_by_competition_format": self.players_by_competition_format,
            "players_by_country": self.players_by_country,
            "players_by_supply_tier": self.players_by_supply_tier,
            "players_by_liquidity_band": self.players_by_liquidity_band,
            "mandatory_country_tier_coverage": self.mandatory_country_tier_coverage,
            "academy_reserve_pathway_players": self.academy_reserve_pathway_players,
        }


REGIONAL_NAME_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "europe": {
        "first": (
            "Adrien", "Alessio", "Ander", "Arno", "Bastien", "Carlos", "Dario", "Elias", "Enzo", "Fabio",
            "Gabriel", "Giorgio", "Hugo", "Iker", "Jules", "Kylian", "Liam", "Lorenzo", "Lucas", "Marco",
            "Matteo", "Milan", "Nico", "Noah", "Pablo", "Rayan", "Sacha", "Sergio", "Theo", "Tiago",
            "Tom", "Victor", "Yanis", "Youssef", "Aurel", "Bruno", "Cedric", "Diego", "Emil", "Florin",
            "Gael", "Henri", "Isak", "Jonas", "Levi", "Nils", "Oscar", "Remy", "Robin", "Xavier",
        ),
        "last": (
            "Almeida", "Barros", "Blanco", "Bonnard", "Castro", "Conte", "Costa", "Delgado", "Duarte", "Estevez",
            "Fernandes", "Fischer", "Garcia", "Garnier", "Gonzalez", "Guerin", "Hansen", "Iglesias", "Jimenez", "Keller",
            "Lacroix", "Larsen", "Lopez", "Martinez", "Mendes", "Moreau", "Navarro", "Nielsen", "Ortega", "Pereira",
            "Petit", "Ramos", "Ribeiro", "Romero", "Santos", "Silva", "Torres", "Valentin", "Vaz", "Weber",
            "Arias", "Belmonte", "Calvo", "Dupont", "Herrera", "Leclerc", "Marin", "Meunier", "Rossi", "Soler",
        ),
        "second": (
            "Antunes", "Bernard", "Campos", "Dias", "Ferreira", "Franco", "Gil", "Gimenez", "Lopes", "Mora",
            "Oliveira", "Pinto", "Reis", "Saavedra", "Sousa", "Teixeira", "Vieira", "Azevedo", "Baptiste", "Carvalho",
            "Dominguez", "Gomes", "Hidalgo", "Muller", "Neves", "Pascal", "Ruiz", "Sanabria", "Tavares", "Varela",
        ),
    },
    "south_america": {
        "first": (
            "Agustin", "Brayan", "Cristian", "Davi", "Eduardo", "Facundo", "Felipe", "Franco", "Gael", "Ignacio",
            "Joao", "Juan", "Kevin", "Lautaro", "Mateo", "Matias", "Miguel", "Nicolas", "Pedro", "Rafael",
            "Santiago", "Thiago", "Valentin", "Yeferson", "Alan", "Breno", "Caio", "Diego", "Emerson", "Fabricio",
            "Gustavo", "Joaquin", "Leonardo", "Luciano", "Martin", "Ramiro", "Samuel", "Tomas", "Victor", "William",
        ),
        "last": (
            "Acosta", "Benitez", "Caceres", "Cardoso", "Correa", "Da Silva", "Ferreira", "Gutierrez", "Lopez", "Martinez",
            "Medina", "Moraes", "Morales", "Nunez", "Oliveira", "Paredes", "Pereira", "Quintero", "Ramos", "Rojas",
            "Romero", "Sanchez", "Santana", "Souza", "Suarez", "Vargas", "Velasquez", "Araujo", "Barrios", "Castillo",
            "Duarte", "Espinoza", "Farias", "Mendez", "Palacios", "Rios", "Tavares", "Vega", "Villalba", "Zarate",
        ),
        "second": (
            "Alves", "Campos", "Costa", "Dias", "Dominguez", "Fernandez", "Garcia", "Lima", "Matos", "Ortiz",
            "Pinto", "Rivera", "Rocha", "Salazar", "Santos", "Sosa", "Torres", "Valdez", "Arenas", "Bustos",
            "Figueroa", "Montoya", "Peralta", "Pizarro", "Rendon", "Saravia", "Tovar", "Villanueva", "Amaya", "Cabral",
        ),
    },
    "africa": {
        "first": (
            "Abdou", "Abel", "Adama", "Amadou", "Aymen", "Baba", "Cheikh", "El Mehdi", "Fadel", "Hakim",
            "Idrissa", "Ismael", "Junior", "Khalil", "Lamine", "Mamadou", "Moussa", "Nabil", "Oumar", "Sadio",
            "Sekou", "Souleymane", "Tariq", "Yacine", "Youssef", "Zinedine", "Aymane", "Bakary", "Firas", "Hamza",
            "Issa", "Karim", "Marouane", "Nassim", "Ousmane", "Rayan", "Salim", "Walid", "Zakaria", "Mory",
        ),
        "last": (
            "Ait El Haj", "Bakayoko", "Balde", "Camara", "Coulibaly", "Dia", "Diakhite", "Diarra", "Diallo", "Fofana",
            "Kaba", "Keita", "Kone", "Mendy", "Ndiaye", "Ouedraogo", "Sarr", "Sylla", "Traore", "Yago",
            "Yattara", "Zoungrana", "Abdellaoui", "Belkacem", "Bennani", "Cherki", "El Idrissi", "Haddad", "Mansouri", "Ouattara",
            "Sow", "Toure", "Bayo", "Kouyate", "Niang", "Sissoko", "Yeboah", "Amoah", "Boateng", "Anane",
        ),
        "second": (
            "Abakar", "Agyeman", "Bamba", "Cisse", "Dieng", "Doucoure", "Konate", "Koulibaly", "Maiga", "Marega",
            "Sangare", "Sanogo", "Tapsoba", "Yaya", "Zaouani", "Alaoui", "Benali", "Chakir", "Ezzine", "Tahiri",
            "Akanji", "Djibo", "Kabore", "Lopy", "Magassa", "Moukoko", "Ouazane", "Tijani", "Touray", "Zongo",
        ),
    },
    "north_america": {
        "first": (
            "Adrian", "Alex", "Anthony", "Bryan", "Caleb", "Diego", "Ethan", "Gabriel", "Isaac", "Jaden",
            "Julian", "Kevin", "Leo", "Luis", "Mateo", "Noel", "Oscar", "Rayan", "Santiago", "Sebastian",
            "Tyler", "Xavier", "Yahir", "Zion", "Andre", "Damian", "Elian", "Javier", "Jordan", "Mason",
        ),
        "last": (
            "Alvarez", "Castillo", "Cruz", "Dominguez", "Flores", "Garza", "Hernandez", "Lopez", "Martinez", "Moreno",
            "Navarro", "Ortega", "Pena", "Ramirez", "Rivera", "Ruiz", "Salinas", "Torres", "Valdez", "Vega",
            "Walker", "Ward", "Brooks", "Coleman", "Diaz", "Escobar", "Guerra", "Morales", "Solis", "Vasquez",
        ),
        "second": (
            "Benitez", "Campos", "Delgado", "Esquivel", "Figueroa", "Gonzalez", "Jimenez", "Luna", "Mendez", "Palacios",
            "Quinones", "Serrano", "Tovar", "Valencia", "Zamora", "Arias", "Barreto", "Carbajal", "Fuentes", "Ponce",
        ),
    },
    "asia": {
        "first": (
            "Akira", "Daichi", "Haruto", "Hiro", "Itsuki", "Jun", "Kai", "Kaito", "Kenji", "Min-Jun",
            "Ren", "Riku", "Ryo", "Sho", "Sora", "Taiga", "Takuya", "Yuto", "Yuma", "Zhen",
        ),
        "last": (
            "Abe", "Fujita", "Hayashi", "Ishikawa", "Ito", "Kobayashi", "Matsuda", "Mori", "Nakamura", "Saito",
            "Suzuki", "Takeda", "Tanaka", "Watanabe", "Yamada", "Yamamoto", "Yoshida", "Aoki", "Endo", "Kato",
        ),
        "second": (
            "Kimura", "Kondo", "Maeda", "Nakajima", "Noguchi", "Okada", "Sakurai", "Shibata", "Uchida", "Yamaguchi",
        ),
    },
}


COUNTRY_SPECS: tuple[CountrySpec, ...] = (
    CountrySpec("france", "France", "FR", "FRA", "FRA", "UEFA", "europe", "europe", 1.40, (1, 2, 3, 4), True, True),
    CountrySpec("spain", "Spain", "ES", "ESP", "ESP", "UEFA", "europe", "europe", 1.36, (1, 2, 3, 4), True, True),
    CountrySpec("belgium", "Belgium", "BE", "BEL", "BEL", "UEFA", "europe", "europe", 1.28, (1, 2, 3), True, True),
    CountrySpec("england", "England", "EN", "ENG", "ENG", "UEFA", "europe", "europe", 1.24, (1, 2, 3), True, True),
    CountrySpec("germany", "Germany", "DE", "DEU", "GER", "UEFA", "europe", "europe", 1.22, (1, 2, 3), True, True),
    CountrySpec("italy", "Italy", "IT", "ITA", "ITA", "UEFA", "europe", "europe", 1.18, (1, 2, 3), True, True),
    CountrySpec("portugal", "Portugal", "PT", "PRT", "POR", "UEFA", "europe", "europe", 1.25, (1, 2), True, True),
    CountrySpec("netherlands", "Netherlands", "NL", "NLD", "NED", "UEFA", "europe", "europe", 1.24, (1, 2), True, True),
    CountrySpec("croatia", "Croatia", "HR", "HRV", "CRO", "UEFA", "europe", "europe", 1.10, (1,), True, False),
    CountrySpec("serbia", "Serbia", "RS", "SRB", "SRB", "UEFA", "europe", "europe", 1.08, (1,), True, False),
    CountrySpec("denmark", "Denmark", "DK", "DNK", "DEN", "UEFA", "europe", "europe", 1.06, (1,), True, False),
    CountrySpec("brazil", "Brazil", "BR", "BRA", "BRA", "CONMEBOL", "south_america", "south_america", 1.30, (1, 2), True, True),
    CountrySpec("argentina", "Argentina", "AR", "ARG", "ARG", "CONMEBOL", "south_america", "south_america", 1.24, (1, 2), True, True),
    CountrySpec("colombia", "Colombia", "CO", "COL", "COL", "CONMEBOL", "south_america", "south_america", 1.12, (1,), True, False),
    CountrySpec("uruguay", "Uruguay", "UY", "URY", "URU", "CONMEBOL", "south_america", "south_america", 1.10, (1,), True, False),
    CountrySpec("nigeria", "Nigeria", "NG", "NGA", "NGA", "CAF", "africa", "africa", 1.18, (1,), True, True),
    CountrySpec("senegal", "Senegal", "SN", "SEN", "SEN", "CAF", "africa", "africa", 1.16, (1,), True, True),
    CountrySpec("ghana", "Ghana", "GH", "GHA", "GHA", "CAF", "africa", "africa", 1.14, (1,), True, True),
    CountrySpec("ivory-coast", "Ivory Coast", "CI", "CIV", "CIV", "CAF", "africa", "africa", 1.14, (1,), True, True),
    CountrySpec("morocco", "Morocco", "MA", "MAR", "MAR", "CAF", "africa", "africa", 1.10, (1,), True, True),
    CountrySpec("austria", "Austria", "AT", "AUT", "AUT", "UEFA", "europe", "europe", 0.84, (1,), False, False),
    CountrySpec("switzerland", "Switzerland", "CH", "CHE", "SUI", "UEFA", "europe", "europe", 0.82, (1,), False, False),
    CountrySpec("norway", "Norway", "NO", "NOR", "NOR", "UEFA", "europe", "europe", 0.80, (1,), False, False),
    CountrySpec("sweden", "Sweden", "SE", "SWE", "SWE", "UEFA", "europe", "europe", 0.78, (1,), False, False),
    CountrySpec("usa", "United States", "US", "USA", "USA", "CONCACAF", "north_america", "north_america", 0.76, (1,), False, False),
    CountrySpec("mexico", "Mexico", "MX", "MEX", "MEX", "CONCACAF", "north_america", "north_america", 0.74, (1,), False, False),
    CountrySpec("japan", "Japan", "JP", "JPN", "JPN", "AFC", "asia", "asia", 0.70, (1,), False, False),
    CountrySpec("turkey", "Turkey", "TR", "TUR", "TUR", "UEFA", "europe", "europe", 0.72, (1,), False, False),
    CountrySpec("czechia", "Czechia", "CZ", "CZE", "CZE", "UEFA", "europe", "europe", 0.74, (1,), False, False),
)


class VerifiedPlayerUniverseSeeder:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        reference_date: date = PHASE_THREE_REFERENCE_DATE,
    ) -> None:
        self.session = session
        self.settings = settings or load_settings()
        self.reference_date = reference_date

    def seed(
        self,
        *,
        target_player_count: int | None = None,
        provider_name: str = PHASE_THREE_PROVIDER_NAME,
        random_seed: int = 20260311,
        replace_provider_data: bool = True,
        batch_size: int = 5_000,
    ) -> UniverseSeedSummary:
        resolved_target = target_player_count or self.settings.player_universe_weighting.target_player_count
        if resolved_target <= 0:
            raise ValueError("target_player_count must be greater than zero.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        if replace_provider_data:
            self._purge_provider_slice(provider_name)

        catalog_state = self._ensure_reference_catalogs()
        timestamp = datetime.now(timezone.utc)
        rng = random.Random(random_seed)

        countries = self._build_country_rows(provider_name=provider_name, timestamp=timestamp)
        self.session.execute(insert(Country), countries)
        country_by_slug = {
            spec.slug: row
            for spec, row in zip(COUNTRY_SPECS, countries, strict=True)
        }

        competitions = self._build_competitions(
            provider_name=provider_name,
            timestamp=timestamp,
            country_by_slug=country_by_slug,
            catalog_state=catalog_state,
        )
        self.session.execute(insert(Competition), competitions)
        competition_seeds = {
            row["provider_external_id"]: CompetitionSeed(
                id=row["id"],
                country_slug=row["metadata_country_slug"],
                country_name=row["metadata_country_name"],
                provider_external_id=row["provider_external_id"],
                name=row["name"],
                slug=row["slug"],
                code=row["code"],
                format_type=row["format_type"],
                age_bracket=row["age_bracket"],
                domestic_level=row["domestic_level"],
                internal_league_code=row["metadata_internal_league_code"],
                weight=row["metadata_weight"],
            )
            for row in competitions
        }

        seasons = self._build_seasons(
            provider_name=provider_name,
            timestamp=timestamp,
            competitions=tuple(competition_seeds.values()),
        )
        self.session.execute(insert(Season), seasons)
        season_by_competition = {row["competition_id"]: row for row in seasons}

        clubs = self._build_clubs(
            provider_name=provider_name,
            timestamp=timestamp,
            competitions=tuple(competition_seeds.values()),
            country_by_slug=country_by_slug,
            catalog_state=catalog_state,
        )
        self.session.execute(insert(Club), clubs)
        clubs_by_competition: dict[str, list[ClubSeed]] = defaultdict(list)
        for row in clubs:
            clubs_by_competition[row["current_competition_id"]].append(
                ClubSeed(
                    id=row["id"],
                    competition_id=row["current_competition_id"],
                    competition_external_id=row["metadata_competition_external_id"],
                    competition_name=row["metadata_competition_name"],
                    country_slug=row["metadata_country_slug"],
                    country_name=row["metadata_country_name"],
                    provider_external_id=row["provider_external_id"],
                    name=row["name"],
                    short_name=row["short_name"] or row["name"],
                    code=row["code"] or row["provider_external_id"][-3:],
                    format_type=row["metadata_format_type"],
                    domestic_level=row["metadata_domestic_level"],
                    internal_league_code=row["metadata_internal_league_code"],
                    weight=row["metadata_weight"],
                )
            )

        competition_allocations = self._allocate_players_by_competition(
            competitions=tuple(competition_seeds.values()),
            target_player_count=resolved_target,
        )
        club_allocations = self._allocate_players_by_club(
            competitions=tuple(competition_seeds.values()),
            clubs_by_competition=clubs_by_competition,
            competition_allocations=competition_allocations,
        )

        summary_counters = {
            "players_by_age_bucket": Counter(),
            "players_by_competition_format": Counter(),
            "players_by_country": Counter(),
            "players_by_supply_tier": Counter(),
            "players_by_liquidity_band": Counter(),
            "mandatory_country_tier_coverage": Counter(),
        }
        used_full_names: set[str] = set()
        total_under_24 = 0
        total_priority_country_players = 0
        pathway_players = 0
        player_batch: list[dict[str, Any]] = []
        verification_batch: list[dict[str, Any]] = []
        tenure_batch: list[dict[str, Any]] = []
        player_sequence = 0
        country_weight_table = self._build_country_weight_table()

        for competition in competition_seeds.values():
            for club in clubs_by_competition[competition.id]:
                club_player_count = club_allocations.get(club.id, 0)
                if club_player_count <= 0:
                    continue
                for _ in range(club_player_count):
                    player_sequence += 1
                    nationality_spec = self._choose_country_for_player(rng=rng, weighted_countries=country_weight_table)
                    player_rows = self._build_player_record(
                        player_index=player_sequence,
                        provider_name=provider_name,
                        timestamp=timestamp,
                        club=club,
                        competition=competition,
                        nationality_spec=nationality_spec,
                        country_by_slug=country_by_slug,
                        season_id=season_by_competition[competition.id]["id"],
                        catalog_state=catalog_state,
                        rng=rng,
                        used_full_names=used_full_names,
                    )
                    player_batch.append(player_rows["player"])
                    verification_batch.append(player_rows["verification"])
                    tenure_batch.append(player_rows["tenure"])

                    age = player_rows["age"]
                    summary_counters["players_by_age_bucket"][self._age_bucket(age)] += 1
                    summary_counters["players_by_competition_format"][competition.format_type] += 1
                    summary_counters["players_by_country"][nationality_spec.name] += 1
                    summary_counters["players_by_supply_tier"][player_rows["supply_tier_code"]] += 1
                    summary_counters["players_by_liquidity_band"][player_rows["liquidity_band_code"]] += 1

                    if age < 24:
                        total_under_24 += 1
                    if nationality_spec.priority_youth_export:
                        total_priority_country_players += 1
                    if competition.format_type in {"academy_league", "reserve_league", "pathway_league"}:
                        pathway_players += 1
                    if competition.country_name in {"France", "Spain", "Belgium", "England", "Germany", "Italy"} and competition.domestic_level is not None:
                        summary_counters["mandatory_country_tier_coverage"][f"{competition.country_name} tier {competition.domestic_level}"] += 1

                    if len(player_batch) >= batch_size:
                        self._flush_player_batches(player_batch, verification_batch, tenure_batch)
                        player_batch = []
                        verification_batch = []
                        tenure_batch = []

        if player_batch:
            self._flush_player_batches(player_batch, verification_batch, tenure_batch)

        if player_sequence != resolved_target:
            raise RuntimeError(f"Seeder generated {player_sequence} players, expected {resolved_target}.")

        return UniverseSeedSummary(
            provider_name=provider_name,
            target_player_count=resolved_target,
            countries_created=len(countries),
            competitions_created=len(competitions),
            seasons_created=len(seasons),
            clubs_created=len(clubs),
            players_created=player_sequence,
            verifications_created=player_sequence,
            tenures_created=player_sequence,
            all_players_tradable=True,
            all_players_verified=True,
            duplicate_identity_count=player_sequence - len(used_full_names),
            youth_players_under_24=total_under_24,
            priority_country_players=total_priority_country_players,
            players_by_age_bucket=dict(sorted(summary_counters["players_by_age_bucket"].items())),
            players_by_competition_format=dict(sorted(summary_counters["players_by_competition_format"].items())),
            players_by_country=dict(summary_counters["players_by_country"].most_common(12)),
            players_by_supply_tier=dict(sorted(summary_counters["players_by_supply_tier"].items())),
            players_by_liquidity_band=dict(sorted(summary_counters["players_by_liquidity_band"].items())),
            mandatory_country_tier_coverage=dict(sorted(summary_counters["mandatory_country_tier_coverage"].items())),
            academy_reserve_pathway_players=pathway_players,
        )

    def _purge_provider_slice(self, provider_name: str) -> None:
        player_ids = select(Player.id).where(Player.source_provider == provider_name)
        club_ids = select(Club.id).where(Club.source_provider == provider_name)
        season_ids = select(Season.id).where(Season.source_provider == provider_name)
        competition_ids = select(Competition.id).where(Competition.source_provider == provider_name)

        self.session.execute(delete(PlayerImageMetadata).where(PlayerImageMetadata.player_id.in_(player_ids)))
        self.session.execute(delete(PlayerVerification).where(PlayerVerification.player_id.in_(player_ids)))
        self.session.execute(delete(PlayerMatchStat).where(PlayerMatchStat.player_id.in_(player_ids)))
        self.session.execute(delete(PlayerSeasonStat).where(PlayerSeasonStat.player_id.in_(player_ids)))
        self.session.execute(delete(InjuryStatus).where(InjuryStatus.player_id.in_(player_ids)))
        self.session.execute(delete(MarketSignal).where(MarketSignal.player_id.in_(player_ids)))
        self.session.execute(delete(PlayerClubTenure).where(PlayerClubTenure.player_id.in_(player_ids)))
        self.session.execute(
            delete(TeamStanding).where(
                or_(TeamStanding.season_id.in_(season_ids), TeamStanding.competition_id.in_(competition_ids))
            )
        )
        self.session.execute(
            delete(Match).where(
                or_(
                    Match.season_id.in_(season_ids),
                    Match.competition_id.in_(competition_ids),
                    Match.home_club_id.in_(club_ids),
                    Match.away_club_id.in_(club_ids),
                )
            )
        )
        self.session.execute(delete(Player).where(Player.source_provider == provider_name))
        self.session.execute(delete(Club).where(Club.source_provider == provider_name))
        self.session.execute(delete(Season).where(Season.source_provider == provider_name))
        self.session.execute(delete(Competition).where(Competition.source_provider == provider_name))
        self.session.execute(delete(Country).where(Country.source_provider == provider_name))
        self.session.flush()

    def _ensure_reference_catalogs(self) -> dict[str, dict[str, str]]:
        timestamp = datetime.now(timezone.utc)
        existing_internal_codes = set(self.session.scalars(select(InternalLeague.code)))
        internal_rows = [
            {"id": str(uuid4()), "created_at": timestamp, "updated_at": timestamp, **row}
            for row in CATALOG_INTERNAL_LEAGUES
            if row["code"] not in existing_internal_codes
        ]
        if internal_rows:
            self.session.execute(insert(InternalLeague), internal_rows)

        existing_supply_codes = set(self.session.scalars(select(SupplyTier.code)))
        supply_rows = []
        for rank, tier in enumerate(self.settings.supply_tiers.tiers, start=1):
            code = tier.name.lower()
            if code in existing_supply_codes:
                continue
            supply_rows.append(
                {
                    "id": str(uuid4()),
                    "code": code,
                    "name": tier.name.title(),
                    "rank": rank,
                    "min_score": tier.min_score,
                    "max_score": tier.max_score,
                    "target_share": tier.target_share,
                    "circulating_supply": tier.circulating_supply,
                    "daily_pack_supply": tier.daily_pack_supply,
                    "season_mint_cap": tier.season_mint_cap,
                    "is_active": True,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
        if supply_rows:
            self.session.execute(insert(SupplyTier), supply_rows)

        existing_liquidity_codes = set(self.session.scalars(select(LiquidityBand.code)))
        liquidity_rows = []
        for rank, band in enumerate(self.settings.liquidity_bands.bands, start=1):
            code = band.name.lower()
            if code in existing_liquidity_codes:
                continue
            liquidity_rows.append(
                {
                    "id": str(uuid4()),
                    "code": code,
                    "name": band.name.title(),
                    "rank": rank,
                    "min_price_credits": band.min_price_credits,
                    "max_price_credits": band.max_price_credits,
                    "max_spread_bps": band.max_spread_bps,
                    "maker_inventory_target": band.maker_inventory_target,
                    "instant_sell_fee_bps": band.instant_sell_fee_bps,
                    "is_active": True,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
        if liquidity_rows:
            self.session.execute(insert(LiquidityBand), liquidity_rows)

        self.session.flush()
        return {
            "internal_leagues": {row.code: row.id for row in self.session.scalars(select(InternalLeague))},
            "supply_tiers": {row.code: row.id for row in self.session.scalars(select(SupplyTier))},
            "liquidity_bands": {row.code: row.id for row in self.session.scalars(select(LiquidityBand))},
        }

    def _build_country_rows(self, *, provider_name: str, timestamp: datetime) -> list[dict[str, Any]]:
        return [
            {
                "id": str(uuid4()),
                "source_provider": provider_name,
                "provider_external_id": f"country:{spec.slug}",
                "name": spec.name,
                "alpha2_code": spec.alpha2_code,
                "alpha3_code": spec.alpha3_code,
                "fifa_code": spec.fifa_code,
                "confederation_code": spec.confederation_code,
                "market_region": spec.market_region,
                "is_enabled_for_universe": True,
                "flag_url": None,
                "last_synced_at": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            for spec in COUNTRY_SPECS
        ]

    def _build_competitions(
        self,
        *,
        provider_name: str,
        timestamp: datetime,
        country_by_slug: dict[str, dict[str, Any]],
        catalog_state: dict[str, dict[str, str]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for spec in COUNTRY_SPECS:
            country_row = country_by_slug[spec.slug]
            for level in spec.senior_tiers:
                internal_code = self._internal_league_code_for_level(level)
                weight = spec.youth_export_weight * COMPETITION_WEIGHT_BY_LEVEL[level]
                rows.append(
                    {
                        "id": str(uuid4()),
                        "source_provider": provider_name,
                        "provider_external_id": f"competition:{spec.slug}:tier:{level}",
                        "country_id": country_row["id"],
                        "internal_league_id": catalog_state["internal_leagues"][internal_code],
                        "name": f"{spec.name} Tier {level}",
                        "slug": f"{spec.slug}-tier-{level}",
                        "code": f"{spec.alpha3_code}{level}",
                        "competition_type": "league",
                        "format_type": "domestic_league",
                        "age_bracket": "senior",
                        "domestic_level": level,
                        "gender": "men",
                        "emblem_url": None,
                        "is_major": level == 1,
                        "is_tradable": True,
                        "competition_strength": round(weight, 3),
                        "current_season_external_id": f"season:{spec.slug}:{spec.slug}-tier-{level}:2025-26",
                        "last_synced_at": timestamp,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                        "metadata_country_slug": spec.slug,
                        "metadata_country_name": spec.name,
                        "metadata_internal_league_code": internal_code,
                        "metadata_weight": weight,
                    }
                )
            if not spec.include_pathways:
                continue
            for format_type, age_bracket, internal_code in (
                ("academy_league", "u19", "league_d"),
                ("reserve_league", "u23", "league_c"),
                ("pathway_league", "u21", "league_d"),
            ):
                weight = spec.youth_export_weight * FORMAT_WEIGHT_MULTIPLIERS[format_type]
                label = FORMAT_DISPLAY_NAMES[format_type]
                rows.append(
                    {
                        "id": str(uuid4()),
                        "source_provider": provider_name,
                        "provider_external_id": f"competition:{spec.slug}:{format_type}",
                        "country_id": country_row["id"],
                        "internal_league_id": catalog_state["internal_leagues"][internal_code],
                        "name": f"{spec.name} {label} Circuit",
                        "slug": f"{spec.slug}-{format_type}",
                        "code": f"{spec.alpha3_code}{label[:3].upper()}",
                        "competition_type": "league",
                        "format_type": format_type,
                        "age_bracket": age_bracket,
                        "domestic_level": None,
                        "gender": "men",
                        "emblem_url": None,
                        "is_major": False,
                        "is_tradable": True,
                        "competition_strength": round(weight, 3),
                        "current_season_external_id": f"season:{spec.slug}:{spec.slug}-{format_type}:2025-26",
                        "last_synced_at": timestamp,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                        "metadata_country_slug": spec.slug,
                        "metadata_country_name": spec.name,
                        "metadata_internal_league_code": internal_code,
                        "metadata_weight": weight,
                    }
                )
        return rows

    def _build_seasons(
        self,
        *,
        provider_name: str,
        timestamp: datetime,
        competitions: tuple[CompetitionSeed, ...],
    ) -> list[dict[str, Any]]:
        start = date(2025, 8, 1)
        end = date(2026, 5, 31)
        opens_at = datetime(2025, 7, 15, tzinfo=timezone.utc)
        closes_at = datetime(2026, 6, 15, tzinfo=timezone.utc)
        rows = []
        for competition in competitions:
            rows.append(
                {
                    "id": str(uuid4()),
                    "source_provider": provider_name,
                    "provider_external_id": f"season:{competition.country_slug}:{competition.slug}:2025-26",
                    "competition_id": competition.id,
                    "label": "2025/26",
                    "year_start": 2025,
                    "year_end": 2026,
                    "start_date": start,
                    "end_date": end,
                    "is_current": True,
                    "current_matchday": 26 if competition.format_type == "domestic_league" else 14,
                    "season_status": "active",
                    "trading_window_opens_at": opens_at,
                    "trading_window_closes_at": closes_at,
                    "data_completeness_score": 0.99,
                    "last_synced_at": timestamp,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
        return rows

    def _build_clubs(
        self,
        *,
        provider_name: str,
        timestamp: datetime,
        competitions: tuple[CompetitionSeed, ...],
        country_by_slug: dict[str, dict[str, Any]],
        catalog_state: dict[str, dict[str, str]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for competition in competitions:
            club_count = CLUBS_PER_COMPETITION.get((competition.format_type, competition.domestic_level))
            if club_count is None:
                club_count = CLUBS_PER_COMPETITION[(competition.format_type, None)]
            for index in range(1, club_count + 1):
                name = self._club_name_for(competition, index)
                rows.append(
                    {
                        "id": str(uuid4()),
                        "source_provider": provider_name,
                        "provider_external_id": f"club:{competition.country_slug}:{competition.provider_external_id.split(':')[-1]}:{index:02d}",
                        "country_id": country_by_slug[competition.country_slug]["id"],
                        "current_competition_id": competition.id,
                        "internal_league_id": catalog_state["internal_leagues"][competition.internal_league_code],
                        "name": name,
                        "slug": name.lower().replace(" ", "-"),
                        "short_name": name.replace(competition.country_name + " ", "")[:80],
                        "code": f"{competition.country_slug[:2].upper()}{index:02d}",
                        "gender": "men",
                        "founded_year": 1980 + (index % 33),
                        "website": None,
                        "venue": f"{competition.country_name} Training Ground {index:02d}",
                        "crest_url": None,
                        "popularity_score": round(min(0.55 + (competition.weight * 0.12) + (index % 5) * 0.03, 0.98), 3),
                        "is_tradable": True,
                        "last_synced_at": timestamp,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                        "metadata_country_slug": competition.country_slug,
                        "metadata_country_name": competition.country_name,
                        "metadata_competition_external_id": competition.provider_external_id,
                        "metadata_competition_name": competition.name,
                        "metadata_format_type": competition.format_type,
                        "metadata_domestic_level": competition.domestic_level,
                        "metadata_internal_league_code": competition.internal_league_code,
                        "metadata_weight": round(competition.weight * (1.00 + (index % 5) * 0.04), 4),
                    }
                )
        return rows

    def _allocate_players_by_competition(
        self,
        *,
        competitions: tuple[CompetitionSeed, ...],
        target_player_count: int,
    ) -> dict[str, int]:
        allocations: dict[str, int] = {}
        grouped: dict[str, list[CompetitionSeed]] = defaultdict(list)
        for competition in competitions:
            grouped[competition.format_type].append(competition)

        remaining_total = target_player_count
        ordered_formats = ("domestic_league", "academy_league", "reserve_league", "pathway_league")
        for position, format_type in enumerate(ordered_formats):
            competitions_in_group = grouped.get(format_type, [])
            if not competitions_in_group:
                continue
            if position == len(ordered_formats) - 1:
                group_target = remaining_total
            else:
                group_target = int(round(target_player_count * FORMAT_TARGET_SHARES[format_type]))
                remaining_total -= group_target
            minimums = self._fit_minimums(group_target, [FORMAT_MIN_PLAYERS[format_type]] * len(competitions_in_group))
            weights = [competition.weight for competition in competitions_in_group]
            counts = self._largest_remainder_allocation(group_target, weights, minimums)
            for competition, count in zip(competitions_in_group, counts, strict=True):
                allocations[competition.id] = count
        if sum(allocations.values()) != target_player_count:
            raise RuntimeError("Competition allocations did not sum to the target player count.")
        return allocations

    def _allocate_players_by_club(
        self,
        *,
        competitions: tuple[CompetitionSeed, ...],
        clubs_by_competition: dict[str, list[ClubSeed]],
        competition_allocations: dict[str, int],
    ) -> dict[str, int]:
        allocations: dict[str, int] = {}
        for competition in competitions:
            clubs = clubs_by_competition[competition.id]
            minimums = self._fit_minimums(
                competition_allocations[competition.id],
                [MIN_PLAYERS_PER_CLUB[competition.format_type]] * len(clubs),
            )
            weights = [club.weight for club in clubs]
            counts = self._largest_remainder_allocation(competition_allocations[competition.id], weights, minimums)
            for club, count in zip(clubs, counts, strict=True):
                allocations[club.id] = count
        return allocations

    def _build_country_weight_table(self) -> tuple[tuple[CountrySpec, float], ...]:
        total_weight = sum(spec.youth_export_weight for spec in COUNTRY_SPECS)
        running_total = 0.0
        table = []
        for spec in COUNTRY_SPECS:
            running_total += spec.youth_export_weight / total_weight
            table.append((spec, running_total))
        return tuple(table)

    def _choose_country_for_player(
        self,
        *,
        rng: random.Random,
        weighted_countries: tuple[tuple[CountrySpec, float], ...],
    ) -> CountrySpec:
        roll = rng.random()
        for spec, threshold in weighted_countries:
            if roll <= threshold:
                return spec
        return weighted_countries[-1][0]

    def _build_player_record(
        self,
        *,
        player_index: int,
        provider_name: str,
        timestamp: datetime,
        club: ClubSeed,
        competition: CompetitionSeed,
        nationality_spec: CountrySpec,
        country_by_slug: dict[str, dict[str, Any]],
        season_id: str,
        catalog_state: dict[str, dict[str, str]],
        rng: random.Random,
        used_full_names: set[str],
    ) -> dict[str, Any]:
        name_parts = self._unique_name_for(index=player_index, region=nationality_spec.name_region, used_full_names=used_full_names)
        position = self._pick_position(rng)
        sampled_age = self._sample_age(rng=rng, format_type=competition.format_type, domestic_level=competition.domestic_level)
        birth_date = self._birth_date_for_age(rng=rng, age=sampled_age)
        age = self._age_at_reference(birth_date)
        height_cm = rng.randint(*position["height"])
        weight_kg = rng.randint(*position["weight_kg"])
        preferred_foot = self._sample_preferred_foot(rng)
        profile_completeness_score = round(min(0.88 + rng.random() * 0.11, 0.995), 3)
        market_value_eur = self._market_value_for(
            rng=rng,
            age=age,
            format_type=competition.format_type,
            domestic_level=competition.domestic_level,
            country_weight=nationality_spec.youth_export_weight,
        )
        player_score = self._player_score_for(
            rng=rng,
            age=age,
            format_type=competition.format_type,
            domestic_level=competition.domestic_level,
            market_value_eur=market_value_eur,
        )
        supply_tier_code = self._supply_tier_for_score(player_score)
        liquidity_band_code = self._liquidity_band_for_market_value(market_value_eur)
        player_id = str(uuid4())
        country_row = country_by_slug[nationality_spec.slug]

        return {
            "age": age,
            "supply_tier_code": supply_tier_code,
            "liquidity_band_code": liquidity_band_code,
            "player": {
                "id": player_id,
                "source_provider": provider_name,
                "provider_external_id": f"player:{player_index:06d}",
                "country_id": country_row["id"],
                "current_club_id": club.id,
                "current_competition_id": competition.id,
                "internal_league_id": catalog_state["internal_leagues"][competition.internal_league_code],
                "supply_tier_id": catalog_state["supply_tiers"][supply_tier_code],
                "liquidity_band_id": catalog_state["liquidity_bands"][liquidity_band_code],
                "full_name": name_parts["full_name"],
                "first_name": name_parts["first_name"],
                "last_name": name_parts["last_name"],
                "short_name": name_parts["short_name"],
                "position": position["position"],
                "normalized_position": position["normalized"],
                "date_of_birth": birth_date,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "preferred_foot": preferred_foot,
                "shirt_number": 1 + ((player_index - 1) % 99),
                "market_value_eur": market_value_eur,
                "profile_completeness_score": profile_completeness_score,
                "is_tradable": True,
                "last_synced_at": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            "verification": {
                "id": str(uuid4()),
                "player_id": player_id,
                "status": VerificationStatus.VERIFIED.value,
                "verification_source": "phase3-import-review",
                "verified_at": timestamp,
                "expires_at": timestamp + timedelta(days=365),
                "confidence_score": 0.995,
                "rights_confirmed": True,
                "reviewer_notes": "Phase 3 synthetic verified universe seed.",
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            "tenure": {
                "id": str(uuid4()),
                "source_provider": provider_name,
                "provider_external_id": f"tenure:{player_index:06d}",
                "player_id": player_id,
                "club_id": club.id,
                "season_id": season_id,
                "start_date": date(2025, 7, 1),
                "end_date": None,
                "squad_number": 1 + ((player_index + 7) % 99),
                "is_current": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        }

    def _flush_player_batches(
        self,
        players: list[dict[str, Any]],
        verifications: list[dict[str, Any]],
        tenures: list[dict[str, Any]],
    ) -> None:
        self.session.execute(insert(Player), players)
        self.session.execute(insert(PlayerVerification), verifications)
        self.session.execute(insert(PlayerClubTenure), tenures)
        self.session.flush()

    @staticmethod
    def _internal_league_code_for_level(level: int) -> str:
        return {1: "league_a", 2: "league_b", 3: "league_c", 4: "league_d"}.get(level, "league_e")

    @staticmethod
    def _club_name_for(competition: CompetitionSeed, index: int) -> str:
        if competition.format_type == "domestic_league" and competition.domestic_level is not None:
            return f"{competition.country_name} Tier {competition.domestic_level} Club {index:02d}"
        return f"{competition.country_name} {FORMAT_DISPLAY_NAMES[competition.format_type]} Squad {index:02d}"

    @staticmethod
    def _largest_remainder_allocation(total: int, weights: list[float], minimums: list[int]) -> list[int]:
        if len(weights) != len(minimums):
            raise ValueError("weights and minimums must have the same length.")
        if sum(minimums) > total:
            raise ValueError("Minimum allocations exceed the requested total.")
        if not weights:
            return []
        remaining = total - sum(minimums)
        if remaining == 0:
            return list(minimums)
        total_weight = sum(weights)
        normalized_weights = weights if total_weight > 0 else [1.0] * len(weights)
        normalized_total = sum(normalized_weights)
        raw_allocations = [(remaining * weight) / normalized_total for weight in normalized_weights]
        floors = [math.floor(value) for value in raw_allocations]
        counts = [minimum + floor for minimum, floor in zip(minimums, floors, strict=True)]
        remainder = remaining - sum(floors)
        order = sorted(
            range(len(raw_allocations)),
            key=lambda index: (raw_allocations[index] - floors[index], normalized_weights[index]),
            reverse=True,
        )
        for index in order[:remainder]:
            counts[index] += 1
        return counts

    @staticmethod
    def _fit_minimums(total: int, minimums: list[int]) -> list[int]:
        if not minimums:
            return []
        minimum_total = sum(minimums)
        if minimum_total <= total:
            return minimums
        if total < len(minimums):
            fitted = [0] * len(minimums)
            for index in range(total):
                fitted[index] = 1
            return fitted
        scaled = [max(1, math.floor(total * (minimum / minimum_total))) for minimum in minimums]
        delta = total - sum(scaled)
        index = 0
        while delta > 0:
            scaled[index % len(scaled)] += 1
            delta -= 1
            index += 1
        while delta < 0:
            current_index = index % len(scaled)
            if scaled[current_index] > 1:
                scaled[current_index] -= 1
                delta += 1
            index += 1
        return scaled

    def _sample_age(self, *, rng: random.Random, format_type: str, domestic_level: int | None) -> int:
        if format_type == "academy_league":
            ranges = ((16, 17, 0.42), (18, 19, 0.46), (20, 21, 0.10), (22, 23, 0.02))
        elif format_type == "reserve_league":
            ranges = ((17, 18, 0.24), (19, 20, 0.34), (21, 22, 0.26), (23, 24, 0.14), (25, 27, 0.02))
        elif format_type == "pathway_league":
            ranges = ((17, 18, 0.22), (19, 20, 0.30), (21, 22, 0.28), (23, 24, 0.16), (25, 27, 0.04))
        elif domestic_level == 1:
            ranges = ((17, 19, 0.16), (20, 21, 0.24), (22, 23, 0.20), (24, 27, 0.24), (28, 31, 0.12), (32, 35, 0.04))
        else:
            ranges = ((17, 19, 0.20), (20, 21, 0.28), (22, 23, 0.22), (24, 27, 0.18), (28, 31, 0.09), (32, 35, 0.03))
        roll = rng.random()
        threshold = 0.0
        for minimum, maximum, share in ranges:
            threshold += share
            if roll <= threshold:
                return rng.randint(minimum, maximum)
        minimum, maximum, _ = ranges[-1]
        return rng.randint(minimum, maximum)

    def _birth_date_for_age(self, *, rng: random.Random, age: int) -> date:
        base_year = self.reference_date.year - age
        month = rng.randint(1, 12)
        day_limit = 28 if month == 2 else 30 if month in {4, 6, 9, 11} else 31
        day = rng.randint(1, day_limit)
        birthday = date(base_year, month, day)
        if birthday > self.reference_date:
            birthday = date(base_year - 1, month, day)
        return birthday

    def _age_at_reference(self, birth_date: date) -> int:
        years = self.reference_date.year - birth_date.year
        if (self.reference_date.month, self.reference_date.day) < (birth_date.month, birth_date.day):
            years -= 1
        return years

    @staticmethod
    def _pick_position(rng: random.Random) -> dict[str, Any]:
        roll = rng.random()
        threshold = 0.0
        for position in POSITION_ARCHETYPES:
            threshold += position["weight"]
            if roll <= threshold:
                return position
        return POSITION_ARCHETYPES[-1]

    @staticmethod
    def _sample_preferred_foot(rng: random.Random) -> str:
        roll = rng.random()
        if roll < 0.62:
            return "right"
        if roll < 0.92:
            return "left"
        return "both"

    @staticmethod
    def _market_value_for(
        *,
        rng: random.Random,
        age: int,
        format_type: str,
        domestic_level: int | None,
        country_weight: float,
    ) -> float:
        level_base = {1: 7_500_000, 2: 3_800_000, 3: 1_950_000, 4: 900_000, None: 1_350_000}
        format_multiplier = {"domestic_league": 1.0, "academy_league": 0.55, "reserve_league": 0.72, "pathway_league": 0.64}[format_type]
        if age <= 18:
            age_multiplier = 1.26
        elif age <= 21:
            age_multiplier = 1.18
        elif age <= 23:
            age_multiplier = 1.08
        elif age <= 27:
            age_multiplier = 1.0
        elif age <= 31:
            age_multiplier = 0.82
        else:
            age_multiplier = 0.60
        base_value = level_base.get(domestic_level, 750_000)
        randomness = 0.72 + rng.random() * 0.88
        market_value = base_value * format_multiplier * age_multiplier * country_weight * randomness
        return round(max(45_000.0, min(market_value, 145_000_000.0)), 2)

    @staticmethod
    def _player_score_for(
        *,
        rng: random.Random,
        age: int,
        format_type: str,
        domestic_level: int | None,
        market_value_eur: float,
    ) -> float:
        market_component = min(market_value_eur / 18_000_000.0, 1.0)
        age_component = 1.0 if age <= 21 else 0.95 if age <= 24 else 0.86 if age <= 29 else 0.72
        format_component = {"domestic_league": 1.0, "academy_league": 0.94, "reserve_league": 0.90, "pathway_league": 0.87}[format_type]
        level_component = {1: 1.0, 2: 0.94, 3: 0.84, 4: 0.74, None: 0.78}[domestic_level]
        noise = 0.90 + rng.random() * 0.16
        return round(min(market_component * age_component * format_component * level_component * noise, 1.0), 4)

    @staticmethod
    def _supply_tier_for_score(score: float) -> str:
        if score >= 0.97:
            return "icon"
        if score >= 0.90:
            return "elite"
        if score >= 0.72:
            return "core"
        if score >= 0.50:
            return "prospect"
        return "discovery"

    @staticmethod
    def _liquidity_band_for_market_value(market_value_eur: float) -> str:
        credits = market_value_eur / 100_000.0
        if credits < 50:
            return "entry"
        if credits < 150:
            return "growth"
        if credits < 400:
            return "premium"
        if credits < 1_000:
            return "bluechip"
        return "marquee"

    def _unique_name_for(self, *, index: int, region: str, used_full_names: set[str]) -> dict[str, str]:
        pools = REGIONAL_NAME_POOLS[region]
        first_names = pools["first"]
        last_names = pools["last"]
        second_last_names = pools["second"]
        local_index = index - 1
        attempt = 0
        while True:
            first_name = first_names[(local_index + attempt) % len(first_names)]
            primary_last = last_names[(local_index // len(first_names) + attempt) % len(last_names)]
            secondary_last = second_last_names[(local_index // (len(first_names) * len(last_names)) + attempt) % len(second_last_names)]
            full_name = f"{first_name} {primary_last} {secondary_last}"
            if full_name not in used_full_names:
                used_full_names.add(full_name)
                return {
                    "full_name": full_name,
                    "first_name": first_name,
                    "last_name": f"{primary_last} {secondary_last}",
                    "short_name": f"{first_name} {primary_last}",
                }
            attempt += 1

    @staticmethod
    def _age_bucket(age: int) -> str:
        if age <= 18:
            return "16-18"
        if age <= 21:
            return "19-21"
        if age <= 23:
            return "22-23"
        if age <= 27:
            return "24-27"
        if age <= 31:
            return "28-31"
        return "32+"
