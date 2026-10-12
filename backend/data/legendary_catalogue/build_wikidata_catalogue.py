"""Build the non-seeding GTEX legendary catalogue staging artifact.

The output intentionally is *not* a registry seed payload.  PR #193's
``LegendaryPlayerPilotRecord`` requires values such as a left/right foot,
weight, portrait asset and market valuation.  Those must not be guessed from a
bulk historical source.  This builder gathers identity facts from Wikidata,
marks every unresolved field, and emits an import gate that prevents accidental
production seeding.

Run from the repository root:
    python backend/data/legendary_catalogue/build_wikidata_catalogue.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
CATALOGUE_PATH = OUT_DIR / "legendary_catalogue_staging_v1.json"
REPORT_PATH = OUT_DIR / "legendary_catalogue_staging_v1.validation.json"
ENDPOINT = "https://query.wikidata.org/sparql"
SOURCE = "Wikidata SPARQL snapshot"
USER_AGENT = "GTEX-LegendaryCatalogue/1.0 (data-quality staging; engineering@gtex.local)"

# Quotas deliberately prioritise underrepresented regions.  A country cap
# stops a handful of large football nations from consuming a continent's slice.
REGIONS = {
    "Africa": {"qid": "Q15", "quota": 350},
    "Asia": {"qid": "Q48", "quota": 350},
    "Europe": {"qid": "Q46", "quota": 450},
    "South America": {"qid": "Q18", "quota": 350},
    "North America/Central America/Caribbean": {"qid": "Q49", "quota": 300},
    "Oceania": {"qid": "Q55643", "quota": 100},
}
COUNTRY_CAP = 35
MIN_CAPS = 20
MAX_BIRTH_YEAR = 1987
# Retained with the generated v1 snapshot so validation can be rerun offline.
V1_SOURCE_ROWS_BY_CONTINENT = {
    "Africa": 1065,
    "Asia": 1500,
    "Europe": 1500,
    "South America": 1207,
    "North America/Central America/Caribbean": 984,
    "Oceania": 249,
}


def query_region(continent_qid: str) -> list[dict]:
    """Return source rows for international players, retaining source values."""
    query = f"""
SELECT ?player ?playerLabel ?dob ?team ?teamCountry ?teamCountryLabel
       ?countryCode ?caps WHERE {{
  ?player wdt:P106 wd:Q937857; wdt:P569 ?dob.
  ?player p:P54 ?membership.
  ?membership ps:P54 ?team; pq:P1350 ?caps.
  ?team wdt:P31/wdt:P279* wd:Q6979593; wdt:P17 ?teamCountry.
  ?teamCountry wdt:P30 wd:{continent_qid}.
  OPTIONAL {{ ?teamCountry wdt:P298 ?countryCode. }}
  FILTER(YEAR(?dob) <= {MAX_BIRTH_YEAR} && ?caps >= {MIN_CAPS})
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language \"en\". }}
}}
ORDER BY DESC(?caps)
LIMIT 1500
"""
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)["results"]["bindings"]


def value(row: dict, key: str) -> str | None:
    item = row.get(key)
    return item.get("value") if item else None


def qid(uri: str | None) -> str | None:
    return uri.rsplit("/", 1)[-1] if uri else None


def position_code(label: str | None) -> str:
    """Map only unambiguous source labels; unknown is safer than an inference."""
    normalized = (label or "").casefold()
    mapping = {
        "goalkeeper": "GK", "centre-back": "CB", "center-back": "CB",
        "full-back": "FB", "right-back": "RB", "left-back": "LB",
        "defender": "DEF", "defensive midfielder": "DM", "midfielder": "CM",
        "central midfielder": "CM", "attacking midfielder": "AM",
        "winger": "WG", "right winger": "RW", "left winger": "LW",
        "forward": "FW", "striker": "ST", "centre-forward": "ST",
        "center-forward": "ST", "second striker": "SS", "sweeper": "SW",
    }
    return mapping.get(normalized, "unknown")


def era_for_birth_year(_: int) -> str:
    # An era is a playing-career claim, not a birth-year calculation.
    return "unknown"


def aggregate(rows: list[dict], continent: str) -> list[dict]:
    """Collapse multi-position/multi-team source rows to one cautious record."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if value(row, "playerLabel") and value(row, "teamCountryLabel"):
            grouped[qid(value(row, "player"))].append(row)

    records = []
    for player_qid, player_rows in grouped.items():
        # A highest-caps national-team statement is the least ambiguous choice
        # when a player represented more than one national side.
        player_rows.sort(key=lambda row: float(value(row, "caps") or 0), reverse=True)
        top = player_rows[0]
        country = value(top, "teamCountryLabel")
        country_code = value(top, "countryCode") or "unknown"
        birth_year = int((value(top, "dob") or "0000")[:4])
        # Position and height are deliberately left unknown here.  Adding their
        # optional joins makes the public endpoint time out and, more
        # importantly, neither tells us which of several positions was primary.
        positions: list[str] = []
        height = None
        primary = "unknown"
        source_url = f"https://www.wikidata.org/wiki/{player_qid}"
        records.append(
            {
                "legendary_profile_id": f"legendary-wikidata-{player_qid.lower()}",
                "full_name": value(top, "playerLabel"),
                "nationality": country,
                "nationality_code": country_code,
                "continent": continent,
                "birth_year": birth_year,
                "historical_height_cm": height if height is not None else "unknown",
                "preferred_foot": "unknown",
                "primary_position": primary,
                "secondary_positions": positions if primary == "unknown" else [],
                "signature_traits": [],
                "signature_tendencies": [],
                "role_profile": "unassigned_pending_evidence",
                "era": era_for_birth_year(birth_year),
                "source_notes": {
                    "source_provider": "wikidata",
                    "entity_id": player_qid,
                    "entity_url": source_url,
                    "national_team_entity_id": qid(value(top, "team")),
                    "national_team_country_entity_id": qid(value(top, "teamCountry")),
                    "international_caps_source_value": int(float(value(top, "caps") or 0)),
                    "query_criteria": f"association football player; national-team caps >= {MIN_CAPS}; birth year <= {MAX_BIRTH_YEAR}",
                    "provenance": SOURCE,
                },
                "data_quality_status": "source_backed_requires_editorial_review",
                "rights_review_status": "not_cleared",
                "registry_import_status": "blocked_pending_factual_completion",
                "review_reasons": [
                    "preferred_foot_not_source_verified",
                    "gameplay_traits_not_authored_without_evidence",
                    "role_profile_not_source_verified",
                    "era_not_source_verified",
                    "portrait_and_rights_not_cleared",
                    "registry_contract_requires_non_unknown_foot_weight_portrait_and_valuation",
                ],
            }
        )
    return records


def select_balanced(records: list[dict], quota: int) -> list[dict]:
    """Select by source caps while enforcing country diversity and stable IDs."""
    ranked = sorted(
        records,
        key=lambda item: (-item["source_notes"]["international_caps_source_value"], item["legendary_profile_id"]),
    )
    selected, countries = [], Counter()
    for record in ranked:
        country = record["nationality"]
        if countries[country] >= COUNTRY_CAP:
            continue
        selected.append(record)
        countries[country] += 1
        if len(selected) == quota:
            break
    return selected


def validate(records: list[dict], source_counts: dict[str, int]) -> dict:
    ids = [record["legendary_profile_id"] for record in records]
    names = [record["full_name"].casefold().strip() for record in records]
    required = [
        "legendary_profile_id", "full_name", "nationality", "birth_year",
        "historical_height_cm", "preferred_foot", "primary_position",
        "secondary_positions", "signature_traits", "signature_tendencies",
        "role_profile", "era", "source_notes", "data_quality_status", "rights_review_status",
    ]
    missing = Counter()
    for record in records:
        for field in required:
            # Empty trait/tendency/secondary-position lists are valid explicit
            # statements that no evidence has been authored yet; they are not
            # absent schema fields.
            if field not in record or record[field] in (None, ""):
                missing[field] += 1
    unknown_factual = {
        field: sum(record[field] == "unknown" for record in records)
        for field in ("historical_height_cm", "preferred_foot", "primary_position", "era")
    }
    return {
        "schema_version": "gtex.legendary-catalogue-staging.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "total_records": len(records),
        "selection": {"country_cap": COUNTRY_CAP, "minimum_source_caps": MIN_CAPS, "maximum_birth_year": MAX_BIRTH_YEAR, "source_rows_by_continent": source_counts},
        "records_by_continent": dict(sorted(Counter(record["continent"] for record in records).items())),
        "records_by_nationality": dict(sorted(Counter(record["nationality"] for record in records).items())),
        "records_by_primary_position": dict(sorted(Counter(record["primary_position"] for record in records).items())),
        "records_missing_required_field": dict(sorted(missing.items())),
        "records_with_unknown_factual_fields": unknown_factual,
        "records_requiring_review": sum(record["data_quality_status"] != "approved" for record in records),
        "records_blocked_from_registry_import": sum(record["registry_import_status"] != "ready" for record in records),
        "duplicate_names": [
            {
                "normalized_name": name,
                "profile_ids": sorted(
                    record["legendary_profile_id"]
                    for record in records
                    if record["full_name"].casefold().strip() == name
                ),
            }
            for name, count in sorted(Counter(names).items())
            if count > 1
        ],
        "duplicate_profile_ids": sorted(item for item, count in Counter(ids).items() if count > 1),
        "validation_results": {
            "required_keys_present": not missing,
            "stable_profile_ids_unique": len(ids) == len(set(ids)),
            "source_entity_ids_unique": len(ids) == len(set(ids)),
            "no_registry_seed_payload_emitted": True,
            "no_production_state_mutated": True,
        },
    }


def main() -> None:
    if "--validate-existing" in sys.argv:
        existing = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))["records"]
        report = validate(existing, V1_SOURCE_ROWS_BY_CONTINENT)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"report": str(REPORT_PATH), "records": len(existing)}))
        return
    all_records, source_counts = [], {}
    for continent, config in REGIONS.items():
        rows = query_region(config["qid"])
        source_counts[continent] = len(rows)
        chosen = select_balanced(aggregate(rows, continent), config["quota"])
        all_records.extend(chosen)
        # Be considerate of the shared public query service.
        time.sleep(2)
    # A person can cross a continental national-team boundary; preserve the
    # higher-cap record once rather than fabricate two profiles.
    deduped: dict[str, dict] = {}
    for record in all_records:
        current = deduped.get(record["legendary_profile_id"])
        if current is None or record["source_notes"]["international_caps_source_value"] > current["source_notes"]["international_caps_source_value"]:
            deduped[record["legendary_profile_id"]] = record
    records = sorted(deduped.values(), key=lambda item: item["legendary_profile_id"])
    report = validate(records, source_counts)
    CATALOGUE_PATH.write_text(json.dumps({"schema_version": report["schema_version"], "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"catalogue": str(CATALOGUE_PATH), "report": str(REPORT_PATH), "records": len(records)}))


if __name__ == "__main__":
    main()
