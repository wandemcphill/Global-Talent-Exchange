from __future__ import annotations

from copy import deepcopy
import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from app.ingestion.real_player_identity_normalizer import normalize_real_player_identity
from app.schemas.real_player_ingestion import RealPlayerSeedInput
from app.providers.import_models import RealPlayerSourceItem


class RealPlayerImportSourceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RealPlayerImportRowFailure:
    row_number: int
    error_message: str
    source_player_key: str | None = None
    canonical_name: str | None = None


@dataclass(frozen=True, slots=True)
class RealPlayerImportSourceBatch:
    start_offset: int
    raw_row_count: int
    items: tuple[RealPlayerSourceItem, ...]
    failures: tuple[RealPlayerImportRowFailure, ...]
    next_cursor: str | None
    exhausted: bool

    @property
    def end_offset(self) -> int:
        return self.start_offset + self.raw_row_count


@dataclass(frozen=True, slots=True)
class RealPlayerImportSourceFile:
    provider_name: str
    path: Path
    source_format: str
    source_version: str | None
    source_fingerprint: str
    raw_rows: tuple[dict[str, Any], ...]

    @property
    def total_rows(self) -> int:
        return len(self.raw_rows)

    @classmethod
    def load(
        cls,
        *,
        provider_name: str,
        source_path: str | Path,
        source_format: str | None = None,
    ) -> "RealPlayerImportSourceFile":
        path = Path(source_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise RealPlayerImportSourceError(f"Import source '{path}' was not found.")

        raw_bytes = path.read_bytes()
        resolved_format = _normalize_source_format(source_format, path)
        if resolved_format == "csv":
            raw_rows = _load_csv_rows(raw_bytes)
            source_version = None
        elif resolved_format == "json":
            raw_rows, source_version = _load_json_rows(raw_bytes)
        elif resolved_format == "jsonl":
            raw_rows = _load_jsonl_rows(raw_bytes)
            source_version = None
        else:
            raise RealPlayerImportSourceError(
                f"Unsupported source format '{resolved_format}'. Expected csv, json, jsonl, or provider_dump."
            )

        return cls(
            provider_name=provider_name,
            path=path,
            source_format=resolved_format,
            source_version=source_version,
            source_fingerprint=hashlib.sha256(raw_bytes).hexdigest(),
            raw_rows=tuple(raw_rows),
        )

    def iter_batches(
        self,
        *,
        start_cursor: str | None,
        batch_size: int,
    ) -> Iterable[RealPlayerImportSourceBatch]:
        start_offset = _parse_cursor(start_cursor)
        if start_offset >= self.total_rows:
            return

        for batch_start in range(start_offset, self.total_rows, batch_size):
            raw_batch = self.raw_rows[batch_start : batch_start + batch_size]
            items: list[RealPlayerSourceItem] = []
            failures: list[RealPlayerImportRowFailure] = []
            for row_number, raw_row in enumerate(raw_batch, start=batch_start + 1):
                try:
                    items.append(
                        _normalize_row(
                            provider_name=self.provider_name,
                            raw_row=raw_row,
                            row_number=row_number,
                        )
                    )
                except RealPlayerImportSourceError as exc:
                    failures.append(
                        RealPlayerImportRowFailure(
                            row_number=row_number,
                            error_message=str(exc),
                            source_player_key=_extract_text(raw_row, "source_player_key", "sourcePlayerKey", "player_id", "playerId", "id"),
                            canonical_name=_extract_text(
                                raw_row,
                                "canonical_name",
                                "canonicalName",
                                "full_name",
                                "fullName",
                                "name",
                            ),
                        )
                    )

            next_offset = batch_start + len(raw_batch)
            exhausted = next_offset >= self.total_rows
            yield RealPlayerImportSourceBatch(
                start_offset=batch_start,
                raw_row_count=len(raw_batch),
                items=tuple(items),
                failures=tuple(failures),
                next_cursor=None if exhausted else str(next_offset),
                exhausted=exhausted,
            )


def _normalize_source_format(source_format: str | None, path: Path) -> str:
    if source_format:
        normalized = source_format.strip().lower()
    else:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            normalized = "csv"
        elif suffix in {".json", ".dump"}:
            normalized = "json"
        elif suffix in {".jsonl", ".ndjson"}:
            normalized = "jsonl"
        else:
            raise RealPlayerImportSourceError(
                f"Could not infer source format from '{path.name}'. Specify csv, json, jsonl, or provider_dump explicitly."
            )
    if normalized == "provider_dump":
        return "json"
    return normalized


def _load_csv_rows(raw_bytes: bytes) -> Sequence[dict[str, Any]]:
    text = raw_bytes.decode("utf-8-sig")
    return tuple(dict(row) for row in csv.DictReader(io.StringIO(text)))


def _load_json_rows(raw_bytes: bytes) -> tuple[Sequence[dict[str, Any]], str | None]:
    try:
        payload = json.loads(raw_bytes.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RealPlayerImportSourceError(f"JSON import source could not be parsed: {exc}") from exc
    rows, source_version = _extract_json_rows(payload)
    if not rows:
        raise RealPlayerImportSourceError("JSON import source did not contain any player rows.")
    return rows, source_version


def _load_jsonl_rows(raw_bytes: bytes) -> Sequence[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw_bytes.decode("utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RealPlayerImportSourceError(f"JSONL import source line {line_number} could not be parsed: {exc}") from exc
        if not isinstance(payload, dict):
            raise RealPlayerImportSourceError(f"JSONL import source line {line_number} is not an object.")
        rows.append(payload)
    return tuple(rows)


def _extract_json_rows(payload: Any) -> tuple[tuple[dict[str, Any], ...], str | None]:
    if isinstance(payload, list):
        rows = tuple(item for item in payload if isinstance(item, dict))
        if len(rows) != len(payload):
            raise RealPlayerImportSourceError("JSON import source row arrays must contain only objects.")
        return rows, None
    if not isinstance(payload, dict):
        raise RealPlayerImportSourceError("JSON import source must be an object or an array of objects.")

    source_version = _extract_text(payload, "source_version", "sourceVersion", "dataset_version", "datasetVersion", "version")
    for key in ("players", "items", "records", "rows", "results"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            rows = tuple(item for item in candidate if isinstance(item, dict))
            if len(rows) != len(candidate):
                raise RealPlayerImportSourceError(f"JSON import source key '{key}' must contain only objects.")
            return rows, source_version
        if isinstance(candidate, dict):
            nested_rows, nested_version = _extract_json_rows(candidate)
            if nested_rows:
                return nested_rows, source_version or nested_version

    pages = payload.get("pages")
    if isinstance(pages, list):
        rows: list[dict[str, Any]] = []
        nested_version: str | None = None
        for page in pages:
            page_rows, page_version = _extract_json_rows(page)
            rows.extend(page_rows)
            nested_version = nested_version or page_version
        if rows:
            return tuple(rows), source_version or nested_version

    data = payload.get("data")
    if isinstance(data, dict):
        nested_rows, nested_version = _extract_json_rows(data)
        if nested_rows:
            return nested_rows, source_version or nested_version

    raise RealPlayerImportSourceError("JSON import source did not contain a supported player row collection.")


def _normalize_row(
    *,
    provider_name: str,
    raw_row: Mapping[str, Any],
    row_number: int,
) -> RealPlayerSourceItem:
    full_name = _extract_text(
        raw_row,
        "full_name",
        "fullName",
        "canonical_name",
        "canonicalName",
        "player_name",
        "playerName",
        "name",
    )
    if not full_name:
        raise RealPlayerImportSourceError("Row is missing a player name.")

    raw_payload = deepcopy(dict(raw_row))
    metadata_json = dict(_extract_mapping(raw_row, "metadata_json", "metadata") or {})
    metadata_json["source_row_number"] = row_number

    provider_player_id = _extract_text(
        raw_row,
        "provider_player_id",
        "providerPlayerId",
        "player_id",
        "playerId",
        "external_id",
        "externalId",
        "source_player_key",
        "sourcePlayerKey",
        "id",
    )
    if provider_player_id:
        provider_player_id = _stable_storage_id(
            provider_player_id,
            prefix="provider",
            metadata_json=metadata_json,
            metadata_key="source_provider_player_id",
        )
    else:
        provider_player_id, fallback_kind, fallback_key = _fallback_provider_player_id(
            provider_name=provider_name,
            raw_row=raw_row,
            full_name=full_name,
        )
        metadata_json["fallback_provider_identity_kind"] = fallback_kind
        metadata_json["fallback_provider_identity_key"] = fallback_key

    raw_payload["provider_player_id"] = provider_player_id

    club_mapping = _extract_mapping(raw_row, "currentClub", "current_club", "club", "team")
    competition_mapping = _extract_mapping(raw_row, "currentCompetition", "current_competition", "competition", "league")
    season_mapping = _extract_mapping(raw_row, "season", "currentSeason", "current_season")

    date_of_birth = _parse_date(
        _extract_text(raw_row, "date_of_birth", "dateOfBirth", "birth_date", "birthDate", "dob")
    )
    provider_last_updated_at = _parse_datetime(
        _extract_text(
            raw_row,
            "provider_last_updated_at",
            "providerLastUpdatedAt",
            "last_updated_at",
            "lastUpdated",
            "updated_at",
            "updatedAt",
        )
    )

    return RealPlayerSourceItem(
        provider_player_id=provider_player_id,
        full_name=full_name,
        first_name=_extract_text(raw_row, "first_name", "firstName", "forename"),
        last_name=_extract_text(raw_row, "last_name", "lastName", "surname"),
        short_name=_extract_text(raw_row, "short_name", "shortName", "display_name", "displayName"),
        normalized_name=_extract_text(raw_row, "normalized_name", "normalizedName"),
        display_position=_extract_text(raw_row, "display_position", "displayPosition", "position", "primary_position", "primaryPosition"),
        nationality_name=_extract_text(
            raw_row,
            "nationality_name",
            "nationalityName",
            "nationality",
            "country_name",
            "countryName",
            "country",
        ),
        nationality_code=_extract_text(raw_row, "nationality_code", "nationalityCode", "country_code", "countryCode"),
        date_of_birth=date_of_birth,
        age=_parse_int(_extract_text(raw_row, "age")),
        current_club_id=_extract_text(raw_row, "provider_club_id", "current_club_id", "currentClubId", "club_id", "clubId")
        or _extract_text(club_mapping, "id", "clubId"),
        current_club_name=_extract_text(raw_row, "provider_club_name", "current_club_name", "currentClubName", "club_name", "clubName")
        or _extract_text(club_mapping, "name", "shortName"),
        current_competition_id=_extract_text(
            raw_row,
            "provider_competition_id",
            "current_competition_id",
            "currentCompetitionId",
            "competition_id",
            "competitionId",
            "league_id",
            "leagueId",
        )
        or _extract_text(competition_mapping, "id", "competitionId"),
        current_competition_name=_extract_text(
            raw_row,
            "provider_competition_name",
            "current_competition_name",
            "currentCompetitionName",
            "competition_name",
            "competitionName",
            "league_name",
            "leagueName",
        )
        or _extract_text(competition_mapping, "name", "competitionName"),
        current_season_id=_extract_text(raw_row, "provider_season_id", "season_id", "seasonId")
        or _extract_text(season_mapping, "id", "seasonId"),
        rough_market_value=_parse_float(
            _extract_text(
                raw_row,
                "rough_market_value",
                "roughMarketValue",
                "market_value",
                "marketValue",
                "current_market_reference_value",
                "currentMarketReferenceValue",
            )
        ),
        rough_market_value_currency=_extract_text(
            raw_row,
            "rough_market_value_currency",
            "roughMarketValueCurrency",
            "market_value_currency",
            "marketValueCurrency",
            "market_reference_currency",
            "marketReferenceCurrency",
        ),
        provider_last_updated_at=provider_last_updated_at,
        metadata_json=metadata_json,
        raw_payload=raw_payload,
    )


def _fallback_provider_player_id(
    *,
    provider_name: str,
    raw_row: Mapping[str, Any],
    full_name: str,
) -> tuple[str, str, str]:
    source_player_key = _extract_text(raw_row, "source_player_key", "sourcePlayerKey") or full_name
    seed = RealPlayerSeedInput.model_validate(
        {
            "source_name": provider_name,
            "source_player_key": source_player_key,
            "canonical_name": _extract_text(raw_row, "canonical_name", "canonicalName") or full_name,
            "display_name": _extract_text(raw_row, "display_name", "displayName"),
            "nationality": _extract_text(raw_row, "nationality", "nationality_name", "country"),
            "nationality_code": _extract_text(raw_row, "nationality_code", "nationalityCode", "country_code", "countryCode"),
            "date_of_birth": _extract_text(raw_row, "date_of_birth", "dateOfBirth", "birth_date", "birthDate", "dob"),
            "birth_year": _parse_int(_extract_text(raw_row, "birth_year", "birthYear")),
            "primary_position": _extract_text(raw_row, "primary_position", "primaryPosition", "position", "display_position"),
            "current_real_world_club": _extract_text(raw_row, "current_club_name", "club_name", "provider_club_name")
            or _extract_text(_extract_mapping(raw_row, "currentClub", "current_club", "club", "team"), "name", "shortName"),
            "current_real_world_club_key": _extract_text(raw_row, "current_club_id", "club_id", "provider_club_id")
            or _extract_text(_extract_mapping(raw_row, "currentClub", "current_club", "club", "team"), "id", "clubId"),
            "current_real_world_league": _extract_text(raw_row, "current_competition_name", "competition_name", "league_name")
            or _extract_text(_extract_mapping(raw_row, "currentCompetition", "current_competition", "competition", "league"), "name"),
            "current_real_world_league_key": _extract_text(raw_row, "current_competition_id", "competition_id", "league_id")
            or _extract_text(_extract_mapping(raw_row, "currentCompetition", "current_competition", "competition", "league"), "id", "competitionId"),
        }
    )
    identity = normalize_real_player_identity(seed, as_of=date.today())
    for kind, stable_key in (
        ("exact_identity_key", identity.exact_identity_key),
        ("name_birthyear_club_key", identity.name_birthyear_club_key),
        ("name_birthyear_nationality_key", identity.name_birthyear_nationality_key),
    ):
        if stable_key:
            digest = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
            return f"fallback:{digest}", kind, stable_key
    raise RealPlayerImportSourceError(
        "Row is missing a stable provider player id and could not derive a safe fallback identity key."
    )


def _stable_storage_id(
    value: str,
    *,
    prefix: str,
    metadata_json: dict[str, Any],
    metadata_key: str,
) -> str:
    cleaned = value.strip()
    if len(cleaned) <= 128:
        return cleaned
    metadata_json[metadata_key] = cleaned
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _extract_mapping(payload: Mapping[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return None


def _extract_text(payload: Mapping[str, Any] | None, *keys: str) -> str | None:
    if payload is None:
        return None
    for key in keys:
        value = payload.get(key)
        text = _clean_text(value)
        if text:
            return text
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _parse_cursor(cursor: str | None) -> int:
    if cursor in {None, ""}:
        return 0
    try:
        value = int(cursor)
    except ValueError as exc:
        raise RealPlayerImportSourceError(f"Unsupported import cursor '{cursor}'.") from exc
    return max(value, 0)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = value.strip()
    for candidate in (cleaned, cleaned.replace("/", "-")):
        try:
            return date.fromisoformat(candidate[:10])
        except ValueError:
            continue
    raise RealPlayerImportSourceError(f"Unsupported date value '{value}'.")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    normalized = cleaned.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RealPlayerImportSourceError(f"Unsupported datetime value '{value}'.") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        return int(float(cleaned))
    except ValueError as exc:
        raise RealPlayerImportSourceError(f"Unsupported integer value '{value}'.") from exc


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError as exc:
        raise RealPlayerImportSourceError(f"Unsupported numeric value '{value}'.") from exc


__all__ = [
    "RealPlayerImportRowFailure",
    "RealPlayerImportSourceBatch",
    "RealPlayerImportSourceError",
    "RealPlayerImportSourceFile",
]
