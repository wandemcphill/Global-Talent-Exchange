from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.ingestion.models import Club, Competition
from app.ingestion.normalizers import slugify
from app.ingestion.real_player_canonical_mapping_service import RealPlayerCanonicalMappingService
from app.models.real_player_reference_mapping import RealPlayerUnresolvedReference


@dataclass(frozen=True, slots=True)
class FootballsquadsCompetitionSeed:
    provider_external_id: str
    canonical_name: str
    competition_type: str = "league"
    format_type: str = "real_world"
    is_major: bool = True
    is_tradable: bool = True
    current_season_external_id: str | None = None

    @property
    def provider_reference_key(self) -> str:
        return slugify(self.provider_external_id)

    @property
    def slug(self) -> str:
        return slugify(self.canonical_name)


@dataclass(frozen=True, slots=True)
class FootballsquadsClubSeed:
    provider_external_id: str
    canonical_name: str
    competition_provider_external_id: str
    short_name: str | None = None
    is_tradable: bool = True

    @property
    def provider_reference_key(self) -> str:
        return slugify(self.provider_external_id)

    @property
    def slug(self) -> str:
        return slugify(self.canonical_name)


@dataclass(frozen=True, slots=True)
class FootballsquadsBackfillItem:
    entity_type: str
    provider_reference_key: str
    provider_external_id: str | None
    raw_label: str | None
    canonical_name: str | None = None
    reason_code: str | None = None
    unresolved_status: str | None = None

    @property
    def label(self) -> str:
        return self.raw_label or self.provider_reference_key

    def to_dict(self) -> dict[str, str | None]:
        return {
            "entity_type": self.entity_type,
            "provider_reference_key": self.provider_reference_key,
            "provider_external_id": self.provider_external_id,
            "raw_label": self.raw_label,
            "canonical_name": self.canonical_name,
            "reason_code": self.reason_code,
            "unresolved_status": self.unresolved_status,
        }


@dataclass(frozen=True, slots=True)
class FootballsquadsCanonicalBackfillReport:
    resolved_items: tuple[FootballsquadsBackfillItem, ...]
    remaining_unresolved_items: tuple[FootballsquadsBackfillItem, ...]

    @property
    def resolved_count(self) -> int:
        return len(self.resolved_items)

    @property
    def remaining_unresolved_count(self) -> int:
        return len(self.remaining_unresolved_items)

    @property
    def resolved_competitions(self) -> tuple[FootballsquadsBackfillItem, ...]:
        return tuple(item for item in self.resolved_items if item.entity_type == "competition")

    @property
    def resolved_clubs(self) -> tuple[FootballsquadsBackfillItem, ...]:
        return tuple(item for item in self.resolved_items if item.entity_type == "club")

    @property
    def resolved_counts_by_entity_type(self) -> dict[str, int]:
        return dict(sorted(Counter(item.entity_type for item in self.resolved_items).items()))

    @property
    def remaining_unresolved_counts_by_entity_type(self) -> dict[str, int]:
        return dict(sorted(Counter(item.entity_type for item in self.remaining_unresolved_items).items()))

    @property
    def remaining_unresolved_categories(self) -> dict[str, int]:
        return dict(
            sorted(
                Counter(
                    f"{item.entity_type}:{item.reason_code or 'unknown'}"
                    for item in self.remaining_unresolved_items
                ).items()
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "resolved_count": self.resolved_count,
            "remaining_unresolved_count": self.remaining_unresolved_count,
            "resolved_counts_by_entity_type": self.resolved_counts_by_entity_type,
            "remaining_unresolved_counts_by_entity_type": self.remaining_unresolved_counts_by_entity_type,
            "remaining_unresolved_categories": self.remaining_unresolved_categories,
            "resolved_items": [item.to_dict() for item in self.resolved_items],
            "remaining_unresolved_items": [item.to_dict() for item in self.remaining_unresolved_items],
            "resolved_competitions": [item.label for item in self.resolved_competitions],
            "resolved_clubs": [item.label for item in self.resolved_clubs],
            "remaining_unresolved": [item.label for item in self.remaining_unresolved_items],
        }


FOOTBALLSQUADS_SOURCE_NAME = "footballsquads"

FOOTBALLSQUADS_COMPETITION_SEEDS: tuple[FootballsquadsCompetitionSeed, ...] = (
    FootballsquadsCompetitionSeed(
        provider_external_id="engprem-2023-2024",
        canonical_name="Premier League",
        current_season_external_id="engprem-2023-2024",
    ),
)

FOOTBALLSQUADS_CLUB_SEEDS: tuple[FootballsquadsClubSeed, ...] = (
    FootballsquadsClubSeed(provider_external_id="engprem:arsenal", canonical_name="Arsenal", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:avilla", canonical_name="Aston Villa", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:bourne", canonical_name="Bournemouth", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:brentf", canonical_name="Brentford", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:brighton", canonical_name="Brighton & Hove Albion", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:burnley", canonical_name="Burnley", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:chelsea", canonical_name="Chelsea", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:cpalace", canonical_name="Crystal Palace", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:everton", canonical_name="Everton", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:fulham", canonical_name="Fulham", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:liverpool", canonical_name="Liverpool", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:luton", canonical_name="Luton Town", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:mancity", canonical_name="Manchester City", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:manutd", canonical_name="Manchester United", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:newcas", canonical_name="Newcastle United", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:nottmf", canonical_name="Nottingham Forest", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:sheffu", canonical_name="Sheffield United", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:tottenha", canonical_name="Tottenham Hotspur", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:westham", canonical_name="West Ham United", competition_provider_external_id="engprem-2023-2024"),
    FootballsquadsClubSeed(provider_external_id="engprem:wolves", canonical_name="Wolverhampton Wanderers", competition_provider_external_id="engprem-2023-2024"),
)

_COMPETITION_SEEDS_BY_EXTERNAL_ID = {
    seed.provider_external_id: seed
    for seed in FOOTBALLSQUADS_COMPETITION_SEEDS
}
_COMPETITION_SEEDS_BY_REFERENCE_KEY = {
    seed.provider_reference_key: seed
    for seed in FOOTBALLSQUADS_COMPETITION_SEEDS
}
_CLUB_SEEDS_BY_EXTERNAL_ID = {
    seed.provider_external_id: seed
    for seed in FOOTBALLSQUADS_CLUB_SEEDS
}
_CLUB_SEEDS_BY_REFERENCE_KEY = {
    seed.provider_reference_key: seed
    for seed in FOOTBALLSQUADS_CLUB_SEEDS
}


@dataclass(slots=True)
class FootballsquadsCanonicalBackfillService:
    settings: Settings = field(default_factory=get_settings)
    source_name: str = FOOTBALLSQUADS_SOURCE_NAME
    mapping_service: RealPlayerCanonicalMappingService = field(init=False)

    def __post_init__(self) -> None:
        self.mapping_service = RealPlayerCanonicalMappingService(
            settings=self.settings,
            auto_create_missing_entities=False,
        )

    def run(
        self,
        session: Session,
        *,
        as_of: datetime | None = None,
    ) -> FootballsquadsCanonicalBackfillReport:
        as_of = as_of or datetime.now(UTC)
        open_rows = list(
            session.scalars(
                select(RealPlayerUnresolvedReference).where(
                    RealPlayerUnresolvedReference.source_name == self.source_name,
                    RealPlayerUnresolvedReference.entity_type.in_(("competition", "club")),
                    RealPlayerUnresolvedReference.status != "resolved",
                )
            )
        )
        resolved_items: list[FootballsquadsBackfillItem] = []
        remaining_unresolved_items: list[FootballsquadsBackfillItem] = []
        competition_cache: dict[str, Competition] = {}

        for row in sorted(
            (item for item in open_rows if item.entity_type == "competition"),
            key=lambda item: item.provider_reference_key,
        ):
            seed = self._competition_seed_for(row)
            if seed is None:
                remaining_unresolved_items.append(self._report_item(row))
                continue
            competition = self._upsert_competition(session, seed, as_of=as_of)
            competition_cache[seed.provider_external_id] = competition
            resolution = self.mapping_service.resolve_competition(
                session,
                source_name=self.source_name,
                provider_external_id=row.provider_external_id or seed.provider_external_id,
                name=row.raw_label or seed.canonical_name,
                as_of=as_of,
            )
            if resolution.status != "resolved" or resolution.canonical_competition_id != competition.id:
                raise RuntimeError(
                    f"Expected resolved footballsquads competition mapping for {row.provider_reference_key}."
                )
            resolved_items.append(
                self._report_item(
                    row,
                    canonical_name=competition.name,
                )
            )

        for row in sorted(
            (item for item in open_rows if item.entity_type == "club"),
            key=lambda item: item.provider_reference_key,
        ):
            seed = self._club_seed_for(row)
            if seed is None:
                remaining_unresolved_items.append(self._report_item(row))
                continue
            competition = competition_cache.get(seed.competition_provider_external_id)
            if competition is None:
                competition_seed = _COMPETITION_SEEDS_BY_EXTERNAL_ID.get(seed.competition_provider_external_id)
                if competition_seed is None:
                    remaining_unresolved_items.append(self._report_item(row))
                    continue
                competition = self._upsert_competition(session, competition_seed, as_of=as_of)
                competition_cache[seed.competition_provider_external_id] = competition
            club = self._upsert_club(session, seed, competition=competition, as_of=as_of)
            resolution = self.mapping_service.resolve_club(
                session,
                source_name=self.source_name,
                provider_external_id=row.provider_external_id or seed.provider_external_id,
                name=row.raw_label or seed.canonical_name,
                competition=competition,
                competition_external_id=competition.provider_external_id,
                competition_name=competition.name,
                as_of=as_of,
            )
            if resolution.status != "resolved" or resolution.canonical_club_id != club.id:
                raise RuntimeError(
                    f"Expected resolved footballsquads club mapping for {row.provider_reference_key}."
                )
            resolved_items.append(
                self._report_item(
                    row,
                    canonical_name=club.name,
                )
            )

        resolved_items.sort(key=lambda item: (item.entity_type, item.provider_reference_key))
        remaining_unresolved_items.sort(key=lambda item: (item.entity_type, item.provider_reference_key))
        return FootballsquadsCanonicalBackfillReport(
            resolved_items=tuple(resolved_items),
            remaining_unresolved_items=tuple(remaining_unresolved_items),
        )

    def _competition_seed_for(
        self,
        row: RealPlayerUnresolvedReference,
    ) -> FootballsquadsCompetitionSeed | None:
        if row.provider_external_id and row.provider_external_id in _COMPETITION_SEEDS_BY_EXTERNAL_ID:
            return _COMPETITION_SEEDS_BY_EXTERNAL_ID[row.provider_external_id]
        return _COMPETITION_SEEDS_BY_REFERENCE_KEY.get(row.provider_reference_key)

    def _club_seed_for(
        self,
        row: RealPlayerUnresolvedReference,
    ) -> FootballsquadsClubSeed | None:
        if row.provider_external_id and row.provider_external_id in _CLUB_SEEDS_BY_EXTERNAL_ID:
            return _CLUB_SEEDS_BY_EXTERNAL_ID[row.provider_external_id]
        return _CLUB_SEEDS_BY_REFERENCE_KEY.get(row.provider_reference_key)

    def _upsert_competition(
        self,
        session: Session,
        seed: FootballsquadsCompetitionSeed,
        *,
        as_of: datetime,
    ) -> Competition:
        competition = session.scalar(
            select(Competition).where(
                Competition.source_provider == self.source_name,
                Competition.provider_external_id == seed.provider_external_id,
            )
        )
        if competition is None:
            competition = Competition(
                source_provider=self.source_name,
                provider_external_id=seed.provider_external_id,
                name=seed.canonical_name,
                slug=seed.slug,
                competition_type=seed.competition_type,
                format_type=seed.format_type,
                is_major=seed.is_major,
                is_tradable=seed.is_tradable,
                current_season_external_id=seed.current_season_external_id,
                last_synced_at=as_of,
            )
            session.add(competition)
        else:
            competition.name = seed.canonical_name
            competition.slug = seed.slug
            competition.competition_type = seed.competition_type
            competition.format_type = seed.format_type
            competition.is_major = seed.is_major
            competition.is_tradable = seed.is_tradable
            competition.current_season_external_id = seed.current_season_external_id
            competition.last_synced_at = as_of
        session.flush()
        return competition

    def _upsert_club(
        self,
        session: Session,
        seed: FootballsquadsClubSeed,
        *,
        competition: Competition,
        as_of: datetime,
    ) -> Club:
        club = session.scalar(
            select(Club).where(
                Club.source_provider == self.source_name,
                Club.provider_external_id == seed.provider_external_id,
            )
        )
        if club is None:
            club = Club(
                source_provider=self.source_name,
                provider_external_id=seed.provider_external_id,
                current_competition=competition,
                name=seed.canonical_name,
                slug=seed.slug,
                short_name=seed.short_name or seed.canonical_name,
                is_tradable=seed.is_tradable,
                last_synced_at=as_of,
            )
            session.add(club)
        else:
            club.current_competition = competition
            club.name = seed.canonical_name
            club.slug = seed.slug
            club.short_name = seed.short_name or seed.canonical_name
            club.is_tradable = seed.is_tradable
            club.last_synced_at = as_of
        session.flush()
        return club

    def _report_item(
        self,
        row: RealPlayerUnresolvedReference,
        *,
        canonical_name: str | None = None,
    ) -> FootballsquadsBackfillItem:
        return FootballsquadsBackfillItem(
            entity_type=row.entity_type,
            provider_reference_key=row.provider_reference_key,
            provider_external_id=row.provider_external_id,
            raw_label=row.raw_label,
            canonical_name=canonical_name,
            reason_code=row.reason_code,
            unresolved_status=row.status,
        )


__all__ = [
    "FOOTBALLSQUADS_SOURCE_NAME",
    "FootballsquadsBackfillItem",
    "FootballsquadsCanonicalBackfillReport",
    "FootballsquadsCanonicalBackfillService",
    "FootballsquadsClubSeed",
    "FootballsquadsCompetitionSeed",
]
