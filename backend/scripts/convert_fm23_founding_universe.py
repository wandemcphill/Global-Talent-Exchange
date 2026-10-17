from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Mapping

EXPECTED_COLUMNS = (
    "Name",
    "Nation",
    "Position",
    "Club",
    "Age",
    "Wage",
    "Value",
    "Sale Value",
    "Best Rating",
    "Best Pot Rating",
)
SOURCE_NAME = "football_manager"
DEFAULT_SOURCE_VERSION = "fm23-founding-universe-v0"


def _read_text(path: Path, encoding: str) -> str:
    raw = path.read_bytes()
    if encoding != "auto":
        return raw.decode(encoding)
    for candidate in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(candidate)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode FM23 CSV '{path}'.")


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").split()).strip()


def _parse_int(value: object) -> int | None:
    cleaned = _clean_text(value).replace(",", "")
    if cleaned in {"", "-", "N/A", "n/a"}:
        return None
    return int(cleaned) if re.fullmatch(r"-?\d+", cleaned) else None


def _parse_rating(value: object) -> dict[str, object]:
    raw = _clean_text(value)
    percent_match = re.search(r"(-?\d+(?:\.\d+)?)%", raw)
    role_match = re.search(r"\(([^)]+)\)", raw)
    return {
        "raw": raw or None,
        "percent": float(percent_match.group(1)) if percent_match else None,
        "role": role_match.group(1).strip() if role_match else None,
    }


def _normalized_row(row: Mapping[str, str]) -> dict[str, str]:
    return {key: _clean_text(row.get(key, "")) for key in EXPECTED_COLUMNS}


def _identity_signature(row: Mapping[str, str]) -> str:
    normalized = _normalized_row(row)
    return "\x1f".join(normalized[key] for key in ("Name", "Nation", "Position", "Club", "Age"))


def _full_row_signature(row: Mapping[str, str]) -> str:
    normalized = _normalized_row(row)
    payload = "\x1f".join(normalized[key] for key in EXPECTED_COLUMNS).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_player_key(row: Mapping[str, str]) -> str:
    payload = _identity_signature(row).encode("utf-8")
    return f"fm23:{hashlib.sha256(payload).hexdigest()[:24]}"


def convert(
    source_path: Path,
    output_path: Path,
    *,
    source_version: str,
    encoding: str = "auto",
) -> dict[str, object]:
    source_bytes = source_path.read_bytes()
    fingerprint = hashlib.sha256(source_bytes).hexdigest()
    text = _read_text(source_path, encoding)
    reader = csv.DictReader(text.splitlines(), delimiter=";", quotechar='"')
    if reader.fieldnames is None:
        raise ValueError("FM23 CSV has no header row.")

    headers = tuple(_clean_text(value) for value in reader.fieldnames)
    if headers != EXPECTED_COLUMNS:
        raise ValueError("Unexpected FM23 basic-export headers. " f"Expected {EXPECTED_COLUMNS}, received {headers}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen_identity_signatures: set[str] = set()
    seen_full_signatures: set[str] = set()
    duplicate_rows = 0
    identity_collision_count = 0
    emitted_rows = 0
    nations = Counter()
    clubs = Counter()

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for source_row_number, raw_row in enumerate(reader, start=2):
            normalized = _normalized_row(raw_row)
            if not normalized["Name"]:
                raise ValueError(f"Row {source_row_number} has no player name.")

            full_signature = _full_row_signature(raw_row)
            identity_signature = _identity_signature(raw_row)
            if full_signature in seen_full_signatures:
                duplicate_rows += 1
                continue
            seen_full_signatures.add(full_signature)

            if identity_signature in seen_identity_signatures:
                identity_collision_count += 1
                raise ValueError(
                    "Non-identical FM23 rows share the same provisional identity tuple "
                    f"at source row {source_row_number}: {identity_signature!r}. "
                    "The export has no UID, so the import must fail closed "
                    "instead of guessing."
                )
            seen_identity_signatures.add(identity_signature)

            nation = normalized["Nation"] or None
            club = normalized["Club"] or None
            position = normalized["Position"] or None
            if nation:
                nations[nation] += 1
            if club:
                clubs[club] += 1

            item = {
                "source_name": SOURCE_NAME,
                "source_player_key": _source_player_key(raw_row),
                "canonical_name": normalized["Name"],
                "display_name": normalized["Name"],
                "nationality": nation,
                "source_metadata": {
                    "kind": "fm23_founding_universe_snapshot",
                    "source_version": source_version,
                    "source_file_name": source_path.name,
                    "source_file_sha256": fingerprint,
                    "source_row_number": source_row_number,
                    "fm23_age": _parse_int(normalized["Age"]),
                    "fm23_wage": _parse_int(normalized["Wage"]),
                    "fm23_value": _parse_int(normalized["Value"]),
                    "fm23_sale_value": _parse_int(normalized["Sale Value"]),
                    "fm23_position": position,
                    "fm23_nation": nation,
                    "fm23_club": club,
                    "fm23_best_rating": _parse_rating(normalized["Best Rating"]),
                    "fm23_best_potential_rating": _parse_rating(normalized["Best Pot Rating"]),
                    "semantics": {
                        "age": "FM-universe age; not canonical real-world age",
                        "value": ("FM game value; not authoritative real-world " "market reference"),
                        "sale_value": ("FM game sale value; not authoritative real-world " "market reference"),
                        "rating": ("FM-derived game rating; not a GTEX canonical " "real-world rating"),
                    },
                },
                "is_verified_real_player": False,
            }
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            emitted_rows += 1

    return {
        "source_file": str(source_path),
        "source_file_sha256": fingerprint,
        "source_version": source_version,
        "source_format": "FM23 basic semicolon CSV",
        "source_name": SOURCE_NAME,
        "source_row_count": emitted_rows + duplicate_rows,
        "emitted_row_count": emitted_rows,
        "exact_duplicate_rows_collapsed": duplicate_rows,
        "identity_collision_count": identity_collision_count,
        "unique_nation_values": len(nations),
        "unique_club_values": len(clubs),
        "output_file": str(output_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Convert an FM23 basic export into GTEX founding-universe staging JSONL."),
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-version", default=DEFAULT_SOURCE_VERSION)
    parser.add_argument("--encoding", default="auto")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = convert(
        args.input,
        args.output,
        source_version=args.source_version,
        encoding=args.encoding,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
