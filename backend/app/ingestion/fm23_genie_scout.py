"""Read-only conversion boundary for FM23 Genie Scout founding-universe CSVs.

The CSV is evidence for a GTEX snapshot, not a runtime dependency.  This
module translates its intentionally small, semicolon-delimited export into the
existing real-player bulk-import shape.  In particular, it does *not* create
``PlayerContract`` records: real-player shares are tradeable assets and their
real-world club is display provenance only.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

FM23_GENIE_SCOUT_PROVIDER = "fm23_club_legends_v0"
FM23_GENIE_SCOUT_SCHEMA_VERSION = "gtex.fm23-genie-scout.v1"
DEFAULT_SNAPSHOT_AT = datetime(2022, 6, 27, tzinfo=UTC)


class Fm23GenieScoutImportError(ValueError):
    pass


def build_manifest(
    source_path: str | Path,
    *,
    snapshot_at: datetime = DEFAULT_SNAPSHOT_AT,
    provider_name: str = FM23_GENIE_SCOUT_PROVIDER,
) -> dict[str, Any]:
    """Build a deterministic bulk-import manifest without changing the CSV."""
    path = Path(source_path).expanduser().resolve()
    raw_bytes = path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(_decode_source(raw_bytes)), delimiter=";"))
    _require_headers(rows)

    occurrence_counts: dict[str, int] = {}
    players: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        identity_material = "|".join(_text(row.get(key)) for key in ("Name", "Nation", "Position", "Club", "Age"))
        occurrence = occurrence_counts.get(identity_material, 0) + 1
        occurrence_counts[identity_material] = occurrence
        players.append(
            _to_player_row(
                row,
                row_number=row_number,
                provider_name=provider_name,
                snapshot_at=snapshot_at,
                occurrence=occurrence,
            )
        )

    # This is deliberately the *canonical* ``RealPlayerIngestionRequest``
    # shape.  The bulk-ops service validates manifests strictly, so importer
    # provenance belongs in the versioned batch fields rather than untyped
    # top-level metadata.
    return {
        "mode": "curated_seed",
        "ingestion_batch_id": f"{provider_name}-{snapshot_at.date().isoformat()}",
        "ingestion_source_version": (
            f"{FM23_GENIE_SCOUT_SCHEMA_VERSION}:" f"{path.name}:sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
        ),
        "as_of": snapshot_at.astimezone(UTC).isoformat(),
        "players": players,
    }


def write_manifest(
    source_path: str | Path,
    output_path: str | Path,
    *,
    snapshot_at: datetime = DEFAULT_SNAPSHOT_AT,
    provider_name: str = FM23_GENIE_SCOUT_PROVIDER,
) -> dict[str, Any]:
    manifest = build_manifest(source_path, snapshot_at=snapshot_at, provider_name=provider_name)
    destination = Path(output_path).expanduser().resolve()
    destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _to_player_row(
    row: dict[str, str | None],
    *,
    row_number: int,
    provider_name: str,
    snapshot_at: datetime,
    occurrence: int,
) -> dict[str, Any]:
    name = _canonical_name(_required(row, "Name", row_number))
    nationality = _first_nationality(_text(row.get("Nation")))
    position, secondary_positions = _positions(_text(row.get("Position")))
    age = _integer(row.get("Age"), minimum=13, maximum=60, label="Age", row_number=row_number)
    club = _none_if_dash(_text(row.get("Club")))
    best_rating = _rating(row.get("Best Rating"), row_number=row_number)
    potential = _rating(row.get("Best Pot Rating"), row_number=row_number)
    source_key_payload = {
        "name": name,
        "nationality": nationality,
        "position": position,
        "club": club,
        "age": age,
        "occurrence": occurrence,
    }
    source_key = (
        "fm23gs-"
        + hashlib.sha256(
            json.dumps(source_key_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:24]
    )
    value = _money(row.get("Value"))
    sale_value = _money(row.get("Sale Value"))

    return {
        "source_name": provider_name,
        "source_player_key": source_key,
        "canonical_name": name,
        "display_name": name,
        "nationality": nationality or None,
        "age": age,
        "primary_position": position or None,
        "secondary_positions": secondary_positions,
        "current_real_world_club": club,
        "current_market_reference_value": value if value is not None else sale_value,
        "market_reference_currency": "EUR",
        "overall_rating": best_rating,
        "potential": max(best_rating, potential) if best_rating is not None and potential is not None else potential,
    }


def _require_headers(rows: list[dict[str, str | None]]) -> None:
    if not rows:
        raise Fm23GenieScoutImportError("FM23 Genie Scout CSV did not contain player rows.")
    required = {"Name", "Nation", "Position", "Club", "Age", "Best Rating", "Best Pot Rating"}
    missing = required - set(rows[0])
    if missing:
        raise Fm23GenieScoutImportError(
            f"FM23 Genie Scout CSV is missing required columns: {', '.join(sorted(missing))}."
        )


def _decode_source(raw_bytes: bytes) -> str:
    """Accept both current UTF-8 and Genie Scout's Windows CSV export."""
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Genie Scout 23 on Windows emits ANSI/Windows-1252 for some exports.
        # Decode it explicitly rather than using replacement characters: names
        # such as Pelé are part of the import identity.
        try:
            return raw_bytes.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise Fm23GenieScoutImportError(
                f"FM23 Genie Scout CSV could not be decoded as UTF-8 or Windows-1252: {exc}"
            ) from exc


def _required(row: dict[str, str | None], key: str, row_number: int) -> str:
    value = _text(row.get(key))
    if not value:
        raise Fm23GenieScoutImportError(f"Row {row_number} has no {key}.")
    return value


def _text(value: object) -> str:
    return str(value or "").strip()


def _canonical_name(value: str) -> str:
    # Genie Scout commonly emits "Surname, Given" while some records already
    # use a display name.  Canonicalise only the unequivocal comma form.
    if value.count(",") == 1:
        surname, given = (part.strip() for part in value.split(",", 1))
        if surname and given:
            return f"{given} {surname}"
    return value


def _first_nationality(value: str) -> str:
    return value.split(" / ", 1)[0].strip()


def _positions(value: str) -> tuple[str, list[str]]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    return (values[0] if values else "", values[1:])


def _none_if_dash(value: str) -> str | None:
    return value if value and value != "-" else None


def _integer(value: object, *, minimum: int, maximum: int, label: str, row_number: int) -> int:
    try:
        parsed = int(_text(value))
    except ValueError as exc:
        raise Fm23GenieScoutImportError(f"Row {row_number} has invalid {label}: {value!r}.") from exc
    if not minimum <= parsed <= maximum:
        raise Fm23GenieScoutImportError(f"Row {row_number} has out-of-range {label}: {parsed}.")
    return parsed


def _rating(value: object, *, row_number: int) -> int | None:
    text = _text(value)
    if not text:
        return None
    match = re.match(r"^(\d+(?:\.\d+)?)%", text)
    if match is None:
        raise Fm23GenieScoutImportError(f"Row {row_number} has invalid Genie Scout rating: {value!r}.")
    return max(1, min(99, round(float(match.group(1)))))


def _money(value: object) -> int | None:
    text = _text(value).replace(",", "")
    if not text or text == "-1":
        return None
    try:
        return max(0, int(text))
    except ValueError:
        return None


__all__ = [
    "DEFAULT_SNAPSHOT_AT",
    "FM23_GENIE_SCOUT_PROVIDER",
    "FM23_GENIE_SCOUT_SCHEMA_VERSION",
    "Fm23GenieScoutImportError",
    "build_manifest",
    "write_manifest",
]
