from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from io import TextIOWrapper
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from zipfile import ZipFile

from app.ingestion.normalizers import normalize_country_name
from app.providers.import_models import RealPlayerSourceItem
from app.schemas.real_player_ingestion import RealPlayerSeedInput

SECOND_ZIP_SOURCE_NAME = "transfermarkt_2nd_zip"
SECOND_ZIP_REQUIRED_FILES = (
    "players.csv",
    "clubs.csv",
    "competitions.csv",
    "countries.csv",
)
FREE_AGENT_PLACEHOLDER = "Free Agent"
UNATTACHED_PLACEHOLDER = "Unattached"
# First-pass players.csv -> GTEX staging contract for the 2nd.zip dataset.
PLAYER_SOURCE_TO_GTEX_FIELD_MAP = {
    "external_player_id": "player_id",
    "slug": "player_code",
    "code": "player_code",
    "full_name": "name",
    "first_name": "first_name",
    "last_name": "last_name",
    "date_of_birth": "date_of_birth",
    "nationality": "country_of_citizenship",
    "country_of_birth": "country_of_birth",
    "city_of_birth": "city_of_birth",
    "preferred_foot": "foot",
    "height_cm": "height_in_cm",
    "primary_position_group": "position",
    "primary_position": "sub_position",
    "current_club_id": "current_club_id",
    "current_club_name": "current_club_name",
    "domestic_competition_id": "current_club_domestic_competition_id",
    "current_market_value_eur": "market_value_in_eur",
    "peak_market_value_eur": "highest_market_value_in_eur",
    "image_url": "image_url",
    "source_url": "url",
    "last_season": "last_season",
    "is_real_player": True,
}

_NULLISH_VALUES = {"", "null", "none", "nan", "n/a", "na"}
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_POSITION_GROUP_ALIASES = {
    "attack": "Attack",
    "attacker": "Attack",
    "midfield": "Midfield",
    "defender": "Defender",
    "goalkeeper": "Goalkeeper",
    "missing": None,
}
_POSITION_ALIASES = {
    "goalkeeper": "Goalkeeper",
    "centre_back": "Centre-Back",
    "center_back": "Centre-Back",
    "left_back": "Left-Back",
    "right_back": "Right-Back",
    "central_midfield": "Central Midfield",
    "defensive_midfield": "Defensive Midfield",
    "attacking_midfield": "Attacking Midfield",
    "left_winger": "Left Winger",
    "right_winger": "Right Winger",
    "left_midfield": "Left Midfield",
    "right_midfield": "Right Midfield",
    "second_striker": "Second Striker",
    "centre_forward": "Centre-Forward",
    "center_forward": "Centre-Forward",
}
_PREFERRED_FOOT_ALIASES = {
    "left": "left",
    "left_foot": "left",
    "left_footed": "left",
    "right": "right",
    "right_foot": "right",
    "right_footed": "right",
    "both": "both",
    "both_feet": "both",
    "two_footed": "both",
    "ambidextrous": "both",
    "either": "both",
}


SecondZipRow = dict[str, str | None]


class TransfermarktSecondZipError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TransfermarktSecondZipPlayerContract:
    external_player_id: str
    slug: str | None
    code: str | None
    full_name: str
    first_name: str | None
    last_name: str | None
    date_of_birth: date | None
    nationality: str | None
    country_of_birth: str | None
    city_of_birth: str | None
    preferred_foot: str | None
    height_cm: int | None
    primary_position_group: str | None
    primary_position: str | None
    current_club_id: str | None
    current_club_name: str | None
    domestic_competition_id: str | None
    current_market_value_eur: int | None
    peak_market_value_eur: int | None
    image_url: str | None
    source_url: str | None
    last_season: int | None
    is_real_player: bool = True
    source_name: str = SECOND_ZIP_SOURCE_NAME
    source_file: str = "players.csv"
    raw_payload: dict[str, str | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TransfermarktSecondZipReferenceMatch:
    entity_type: str
    status: str
    provider_external_id: str | None
    label: str | None
    matched_field: str | None = None
    source_file: str | None = None
    fallback_used: bool = False
    notes: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "status": self.status,
            "provider_external_id": self.provider_external_id,
            "provider_reference_key": self.provider_external_id,
            "label": self.label,
            "display_name": self.label,
            "matched_field": self.matched_field,
            "source_file": self.source_file,
            "fallback_used": self.fallback_used,
            "notes": self.notes,
            **({"metadata": dict(self.metadata_json)} if self.metadata_json else {}),
        }


@dataclass(slots=True)
class TransfermarktSecondZipReader:
    archive_path: str | Path

    def __post_init__(self) -> None:
        self.archive_path = Path(self.archive_path)

    def validate(self) -> None:
        if not self.archive_path.exists():
            raise TransfermarktSecondZipError(f"2nd.zip archive was not found: {self.archive_path}")
        with ZipFile(self.archive_path) as archive:
            members = {item.filename for item in archive.infolist()}
        missing = [name for name in SECOND_ZIP_REQUIRED_FILES if name not in members]
        if missing:
            missing_csvs = ", ".join(missing)
            raise TransfermarktSecondZipError(f"2nd.zip is missing required CSV members: {missing_csvs}")

    def iter_players(self):
        yield from self._iter_rows("players.csv")

    def iter_clubs(self):
        yield from self._iter_rows("clubs.csv")

    def iter_competitions(self):
        yield from self._iter_rows("competitions.csv")

    def iter_countries(self):
        yield from self._iter_rows("countries.csv")

    def iter_player_contracts(self):
        for row in self.iter_players():
            yield map_player_row_to_contract(row)

    def build_reference_catalog(self) -> "TransfermarktSecondZipReferenceCatalog":
        return TransfermarktSecondZipReferenceCatalog.from_reader(self)

    def iter_source_items(self):
        reference_catalog = self.build_reference_catalog()
        for contract in self.iter_player_contracts():
            yield map_player_contract_to_source_item(contract, reference_catalog=reference_catalog)

    def _iter_rows(self, member_name: str):
        self.validate()
        with ZipFile(self.archive_path) as archive:
            try:
                with archive.open(member_name, "r") as handle:
                    with TextIOWrapper(handle, encoding="utf-8-sig", newline="") as text_stream:
                        reader = csv.DictReader(text_stream)
                        for row in reader:
                            yield {
                                normalize_column_name(key): normalize_optional_text(value)
                                for key, value in row.items()
                                if key is not None
                            }
            except KeyError as exc:
                raise TransfermarktSecondZipError(f"Unsupported 2nd.zip member '{member_name}'.") from exc


@dataclass(frozen=True, slots=True)
class TransfermarktSecondZipReferenceCatalog:
    clubs_by_id: dict[str, SecondZipRow]
    competitions_by_id: dict[str, SecondZipRow]
    countries_by_id: dict[str, SecondZipRow]
    countries_by_normalized_name: dict[str, tuple[SecondZipRow, ...]]

    @classmethod
    def from_reader(cls, reader: TransfermarktSecondZipReader) -> "TransfermarktSecondZipReferenceCatalog":
        return cls.from_rows(
            clubs=reader.iter_clubs(),
            competitions=reader.iter_competitions(),
            countries=reader.iter_countries(),
        )

    @classmethod
    def from_rows(
        cls,
        *,
        clubs: Iterable[Mapping[str, Any]],
        competitions: Iterable[Mapping[str, Any]],
        countries: Iterable[Mapping[str, Any]],
    ) -> "TransfermarktSecondZipReferenceCatalog":
        clubs_by_id: dict[str, SecondZipRow] = {}
        competitions_by_id: dict[str, SecondZipRow] = {}
        countries_by_id: dict[str, SecondZipRow] = {}
        countries_by_normalized_name: dict[str, list[SecondZipRow]] = {}

        for row in clubs:
            normalized_row = _normalize_row(row)
            club_id = normalized_row.get("club_id")
            if club_id is not None:
                clubs_by_id[club_id] = normalized_row

        for row in competitions:
            normalized_row = _normalize_row(row)
            competition_id = normalized_row.get("competition_id")
            if competition_id is not None:
                competitions_by_id[competition_id] = normalized_row

        for row in countries:
            normalized_row = _normalize_row(row)
            country_id = normalized_row.get("country_id")
            if country_id is not None:
                countries_by_id[country_id] = normalized_row
            normalized_name = _normalized_country_lookup_key(normalized_row.get("country_name"))
            if normalized_name is None:
                continue
            countries_by_normalized_name.setdefault(normalized_name, []).append(normalized_row)

        return cls(
            clubs_by_id=clubs_by_id,
            competitions_by_id=competitions_by_id,
            countries_by_id=countries_by_id,
            countries_by_normalized_name={key: tuple(value) for key, value in countries_by_normalized_name.items()},
        )


def normalize_column_name(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = _WHITESPACE_RE.sub(" ", str(value)).strip()
    if not cleaned:
        return None
    if cleaned.casefold() in _NULLISH_VALUES:
        return None
    return cleaned


def parse_source_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(cleaned[:10])
        except ValueError:
            return None


def normalize_preferred_foot(value: Any) -> str | None:
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    normalized = _normalized_key(cleaned)
    alias = _PREFERRED_FOOT_ALIASES.get(normalized)
    if alias is not None:
        return alias
    return cleaned.casefold()


def normalize_position_group(value: Any) -> str | None:
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    normalized = _normalized_key(cleaned)
    if normalized in _POSITION_GROUP_ALIASES:
        return _POSITION_GROUP_ALIASES[normalized]
    return cleaned


def normalize_primary_position(value: Any) -> str | None:
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    normalized = _normalized_key(cleaned)
    if normalized in _POSITION_ALIASES:
        return _POSITION_ALIASES[normalized]
    return cleaned


def normalize_position_fields(position: Any, sub_position: Any) -> tuple[str | None, str | None]:
    return normalize_position_group(position), normalize_primary_position(sub_position)


def map_player_row_to_contract(row: Mapping[str, Any]) -> TransfermarktSecondZipPlayerContract:
    raw_payload = {
        normalize_column_name(str(key)): normalize_optional_text(value) for key, value in row.items() if key is not None
    }
    primary_position_group, primary_position = normalize_position_fields(
        raw_payload.get("position"),
        raw_payload.get("sub_position"),
    )
    player_id = _require_field(raw_payload, "player_id")
    full_name = _require_field(raw_payload, "name")
    player_code = raw_payload.get("player_code")
    return TransfermarktSecondZipPlayerContract(
        external_player_id=player_id,
        slug=player_code,
        code=player_code,
        full_name=full_name,
        first_name=raw_payload.get("first_name"),
        last_name=raw_payload.get("last_name"),
        date_of_birth=parse_source_date(raw_payload.get("date_of_birth")),
        nationality=raw_payload.get("country_of_citizenship"),
        country_of_birth=raw_payload.get("country_of_birth"),
        city_of_birth=raw_payload.get("city_of_birth"),
        preferred_foot=normalize_preferred_foot(raw_payload.get("foot")),
        height_cm=parse_optional_height_cm(raw_payload.get("height_in_cm")),
        primary_position_group=primary_position_group,
        primary_position=primary_position,
        current_club_id=raw_payload.get("current_club_id"),
        current_club_name=raw_payload.get("current_club_name"),
        domestic_competition_id=raw_payload.get("current_club_domestic_competition_id"),
        current_market_value_eur=parse_optional_int(raw_payload.get("market_value_in_eur")),
        peak_market_value_eur=parse_optional_int(raw_payload.get("highest_market_value_in_eur")),
        image_url=raw_payload.get("image_url"),
        source_url=raw_payload.get("url"),
        last_season=parse_optional_int(raw_payload.get("last_season")),
        is_real_player=True,
        raw_payload=raw_payload,
    )


def map_player_contract_to_source_item(
    contract: TransfermarktSecondZipPlayerContract,
    *,
    reference_catalog: TransfermarktSecondZipReferenceCatalog,
) -> RealPlayerSourceItem:
    club_match, club_row = _resolve_club_reference(contract, reference_catalog=reference_catalog)
    competition_match = _resolve_competition_reference(
        contract,
        reference_catalog=reference_catalog,
        club_row=club_row,
    )
    country_match = _resolve_country_reference(contract, reference_catalog=reference_catalog)

    seed_input = RealPlayerSeedInput.model_validate(
        {
            "source_name": contract.source_name,
            "source_player_key": contract.external_player_id,
            "canonical_name": contract.full_name,
            "display_name": contract.full_name,
            "nationality": country_match.label or contract.nationality,
            "nationality_code": country_match.provider_external_id,
            "date_of_birth": contract.date_of_birth,
            "dominant_foot": contract.preferred_foot,
            "primary_position": contract.primary_position,
            "secondary_positions": [],
            "current_real_world_club": club_match.label,
            "current_real_world_club_key": club_match.provider_external_id,
            "current_real_world_league": competition_match.label,
            "current_real_world_league_key": competition_match.provider_external_id,
            "height_cm": contract.height_cm,
            "current_market_reference_value": contract.current_market_value_eur,
            "market_reference_currency": "EUR",
            "photo_url": contract.image_url,
            "is_verified_real_player": True,
        }
    )

    mapping_metadata = {
        "country": country_match.to_dict(),
        "competition": competition_match.to_dict(),
        "club": club_match.to_dict(),
        "fallback_used": any(match.fallback_used for match in (country_match, competition_match, club_match)),
    }
    metadata_json = {
        "source_file": contract.source_file,
        "mapping": mapping_metadata,
        "reference_mapping": mapping_metadata,
        "second_zip": {
            "player_id": contract.external_player_id,
            "player_code": contract.code,
            "current_club_id": contract.current_club_id,
            "domestic_competition_id": contract.domestic_competition_id,
        },
    }
    return RealPlayerSourceItem(
        provider_player_id=contract.external_player_id,
        full_name=contract.full_name,
        first_name=contract.first_name,
        last_name=contract.last_name,
        short_name=contract.code,
        display_position=contract.primary_position or contract.primary_position_group,
        nationality_name=country_match.label or contract.nationality,
        nationality_code=country_match.provider_external_id,
        date_of_birth=contract.date_of_birth,
        current_club_id=club_match.provider_external_id,
        current_club_name=club_match.label,
        current_competition_id=competition_match.provider_external_id,
        current_competition_name=competition_match.label,
        metadata_json=metadata_json,
        raw_payload=seed_input.model_dump(mode="json"),
    )


def map_player_row_to_source_item(
    row: Mapping[str, Any],
    *,
    reference_catalog: TransfermarktSecondZipReferenceCatalog,
) -> RealPlayerSourceItem:
    return map_player_contract_to_source_item(
        map_player_row_to_contract(row),
        reference_catalog=reference_catalog,
    )


def parse_optional_int(value: Any) -> int | None:
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError:
        try:
            return int(float(cleaned))
        except ValueError:
            return None


def parse_optional_height_cm(value: Any) -> int | None:
    parsed = parse_optional_int(value)
    if parsed is None:
        return None
    if parsed < 100 or parsed > 250:
        return None
    return parsed


def _normalized_key(value: str) -> str:
    return _NON_ALNUM_RE.sub("_", value.casefold()).strip("_")


def _normalize_row(row: Mapping[str, Any]) -> SecondZipRow:
    return {
        normalize_column_name(str(key)): normalize_optional_text(value) for key, value in row.items() if key is not None
    }


def _normalized_country_lookup_key(value: Any) -> str | None:
    normalized_name = normalize_country_name(normalize_optional_text(value))
    if normalized_name is None:
        return None
    return normalized_name.casefold()


def _resolve_country_reference(
    contract: TransfermarktSecondZipPlayerContract,
    *,
    reference_catalog: TransfermarktSecondZipReferenceCatalog,
) -> TransfermarktSecondZipReferenceMatch:
    if contract.nationality is None:
        return TransfermarktSecondZipReferenceMatch(
            entity_type="country",
            status="skipped",
            provider_external_id=None,
            label=None,
            notes="players.csv did not include country_of_citizenship.",
        )
    normalized_name = _normalized_country_lookup_key(contract.nationality)
    candidates = (
        reference_catalog.countries_by_normalized_name.get(normalized_name, ()) if normalized_name is not None else ()
    )
    if len(candidates) == 1:
        country_row = candidates[0]
        return TransfermarktSecondZipReferenceMatch(
            entity_type="country",
            status="mapped",
            provider_external_id=country_row.get("country_id"),
            label=country_row.get("country_name") or contract.nationality,
            matched_field="country_name",
            source_file="countries.csv",
            metadata_json={
                "country_code": country_row.get("country_code"),
                "confederation": country_row.get("confederation"),
            },
        )
    if len(candidates) > 1:
        return TransfermarktSecondZipReferenceMatch(
            entity_type="country",
            status="unresolved",
            provider_external_id=None,
            label=contract.nationality,
            matched_field="country_name",
            source_file="countries.csv",
            notes="countries.csv contained multiple rows for the nationality value.",
            metadata_json={
                "candidate_country_ids": [candidate.get("country_id") for candidate in candidates],
            },
        )
    return TransfermarktSecondZipReferenceMatch(
        entity_type="country",
        status="unresolved",
        provider_external_id=None,
        label=contract.nationality,
        matched_field="country_name",
        source_file="countries.csv",
        notes="countries.csv did not contain a strong nationality match.",
    )


def _resolve_competition_reference(
    contract: TransfermarktSecondZipPlayerContract,
    *,
    reference_catalog: TransfermarktSecondZipReferenceCatalog,
    club_row: SecondZipRow | None,
) -> TransfermarktSecondZipReferenceMatch:
    competition_id = contract.domestic_competition_id or (
        club_row.get("domestic_competition_id") if club_row is not None else None
    )
    if competition_id is None:
        return TransfermarktSecondZipReferenceMatch(
            entity_type="competition",
            status="skipped",
            provider_external_id=None,
            label=None,
            notes="No domestic competition id was available on players.csv or clubs.csv.",
        )
    competition_row = reference_catalog.competitions_by_id.get(competition_id)
    if competition_row is not None:
        return TransfermarktSecondZipReferenceMatch(
            entity_type="competition",
            status="mapped",
            provider_external_id=competition_id,
            label=(competition_row.get("name") or competition_row.get("competition_code") or competition_id),
            matched_field=("competition_id" if contract.domestic_competition_id else "clubs.domestic_competition_id"),
            source_file="competitions.csv",
            metadata_json={
                "country_id": competition_row.get("country_id"),
                "country_name": competition_row.get("country_name"),
                "competition_code": competition_row.get("competition_code"),
                "competition_type": competition_row.get("type"),
            },
        )
    return TransfermarktSecondZipReferenceMatch(
        entity_type="competition",
        status="unresolved",
        provider_external_id=competition_id,
        label=competition_id,
        matched_field=("competition_id" if contract.domestic_competition_id else "clubs.domestic_competition_id"),
        source_file="competitions.csv",
        notes="competitions.csv did not contain the domestic competition id.",
    )


def _resolve_club_reference(
    contract: TransfermarktSecondZipPlayerContract,
    *,
    reference_catalog: TransfermarktSecondZipReferenceCatalog,
) -> tuple[TransfermarktSecondZipReferenceMatch, SecondZipRow | None]:
    if contract.current_club_id is not None:
        club_row = reference_catalog.clubs_by_id.get(contract.current_club_id)
        if club_row is not None:
            return (
                TransfermarktSecondZipReferenceMatch(
                    entity_type="club",
                    status="mapped",
                    provider_external_id=contract.current_club_id,
                    label=club_row.get("name") or contract.current_club_name or contract.current_club_id,
                    matched_field="club_id",
                    source_file="clubs.csv",
                    metadata_json={
                        "club_code": club_row.get("club_code"),
                        "domestic_competition_id": club_row.get("domestic_competition_id"),
                    },
                ),
                club_row,
            )
    if contract.current_club_name is not None:
        return (
            TransfermarktSecondZipReferenceMatch(
                entity_type="club",
                status="unresolved",
                provider_external_id=contract.current_club_id,
                label=contract.current_club_name,
                matched_field="current_club_name",
                source_file="players.csv",
                notes="clubs.csv did not contain a strong club id match.",
            ),
            None,
        )
    if contract.current_club_id is not None:
        return (
            TransfermarktSecondZipReferenceMatch(
                entity_type="club",
                status="unresolved",
                provider_external_id=contract.current_club_id,
                label=UNATTACHED_PLACEHOLDER,
                matched_field="current_club_id",
                source_file="players.csv",
                fallback_used=True,
                notes="current_club_name was empty, so GTEX kept the provider id and used an Unattached placeholder.",
            ),
            None,
        )
    return (
        TransfermarktSecondZipReferenceMatch(
            entity_type="club",
            status="fallback",
            provider_external_id=None,
            label=FREE_AGENT_PLACEHOLDER,
            matched_field="current_club_name",
            source_file="players.csv",
            fallback_used=True,
            notes="current_club_name was empty and no provider club id was supplied.",
        ),
        None,
    )


def _require_field(row: Mapping[str, str | None], field_name: str) -> str:
    value = row.get(field_name)
    if value is None:
        raise TransfermarktSecondZipError(f"players.csv row is missing required field '{field_name}'.")
    return value


__all__ = [
    "PLAYER_SOURCE_TO_GTEX_FIELD_MAP",
    "SECOND_ZIP_REQUIRED_FILES",
    "SECOND_ZIP_SOURCE_NAME",
    "FREE_AGENT_PLACEHOLDER",
    "TransfermarktSecondZipError",
    "TransfermarktSecondZipPlayerContract",
    "TransfermarktSecondZipReferenceCatalog",
    "TransfermarktSecondZipReferenceMatch",
    "TransfermarktSecondZipReader",
    "map_player_row_to_contract",
    "map_player_contract_to_source_item",
    "map_player_row_to_source_item",
    "normalize_column_name",
    "normalize_optional_text",
    "normalize_position_fields",
    "normalize_position_group",
    "normalize_preferred_foot",
    "normalize_primary_position",
    "parse_optional_height_cm",
    "parse_optional_int",
    "parse_source_date",
    "UNATTACHED_PLACEHOLDER",
]
