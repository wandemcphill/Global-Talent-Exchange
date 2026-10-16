from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .schema import CatalogueRecord, Evidence

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "GTEX-Legendary-Catalogue/1.0 (catalogue research tool)"


@dataclass(frozen=True, slots=True)
class WikidataRow:
    item: str
    label: str
    dob: str | None
    sport_country: str | None
    sport_country_iso3: str | None
    citizenship: str | None
    citizenship_iso3: str | None
    height: str | None
    position: str | None
    position_label: str | None
    foot_label: str | None
    image: str | None


QUERY = """
SELECT ?item ?itemLabel ?dob ?sportCountry ?sportCountryIso3 ?citizenship ?citizenshipIso3
       ?height ?position ?positionLabel ?footLabel ?image WHERE {
  ?item wdt:P106/wdt:P279* wd:Q937857;
        wdt:P569 ?dob.
  FILTER(YEAR(?dob) <= 2000)
  OPTIONAL { ?item wdt:P1532 ?sportCountry. }
  OPTIONAL { ?sportCountry wdt:P298 ?sportCountryIso3. }
  OPTIONAL { ?item wdt:P27 ?citizenship. }
  OPTIONAL { ?citizenship wdt:P298 ?citizenshipIso3. }
  OPTIONAL { ?item wdt:P2048 ?height. }
  OPTIONAL { ?item wdt:P413 ?position. }
  OPTIONAL { ?item wdt:P8006 ?foot. }
  OPTIONAL { ?item wdt:P18 ?image. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_rows(*, page_size: int = 500, max_pages: int = 20, pause_seconds: float = 1.0) -> list[WikidataRow]:
    rows: list[WikidataRow] = []
    for page in range(max_pages):
        paged_query = f"{QUERY}\nLIMIT {page_size}\nOFFSET {page * page_size}"
        params = urlencode({"query": paged_query, "format": "json"})
        request = Request(
            f"{ENDPOINT}?{params}",
            headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
        )
        with urlopen(request, timeout=90) as response:
            payload = json.load(response)
        bindings = payload.get("results", {}).get("bindings", [])
        if not bindings:
            break
        for binding in bindings:

            def value(key: str) -> str | None:
                item = binding.get(key)
                return item.get("value") if item else None

            rows.append(
                WikidataRow(
                    item=value("item") or "",
                    label=value("itemLabel") or "",
                    dob=value("dob"),
                    sport_country=value("sportCountry"),
                    sport_country_iso3=value("sportCountryIso3"),
                    citizenship=value("citizenship"),
                    citizenship_iso3=value("citizenshipIso3"),
                    height=value("height"),
                    position=value("position"),
                    position_label=value("positionLabel"),
                    foot_label=value("footLabel"),
                    image=value("image"),
                )
            )
        if len(bindings) < page_size:
            break
        time.sleep(pause_seconds)
    return rows


def rows_to_candidates(rows: list[WikidataRow]) -> list[CatalogueRecord]:
    grouped: dict[str, list[WikidataRow]] = {}
    for row in rows:
        if row.item:
            grouped.setdefault(row.item, []).append(row)

    candidates: list[CatalogueRecord] = []
    for item in sorted(grouped):
        group = grouped[item]
        first = group[0]
        countries: list[str] = []
        positions: list[str] = []
        heights: list[int] = []
        foot_values: set[str] = set()
        image = None
        for row in group:
            for code in (row.sport_country_iso3, row.citizenship_iso3):
                if code and code.upper() not in countries:
                    countries.append(code.upper())
            if row.position_label and row.position_label not in positions:
                positions.append(row.position_label)
            if row.height:
                try:
                    heights.append(round(float(row.height)))
                except ValueError:
                    pass
            foot = (row.foot_label or "").lower()
            if "left-footed" in foot:
                foot_values.add("left")
            elif "right-footed" in foot:
                foot_values.add("right")
            elif "two-footed" in foot:
                foot_values.add("both")
            image = image or row.image

        dob = date.fromisoformat(first.dob[:10]) if first.dob else None
        evidence = Evidence(
            provider="wikidata",
            uri=f"https://www.wikidata.org/wiki/{item.rsplit('/', 1)[-1]}",
            retrieved_at=datetime.now(timezone.utc),
            claim_types=["identity", "date_of_birth", "nationality", "football_position", "height", "footedness"],
        )
        metadata: dict[str, Any] = {
            "wikidata_id": item.rsplit("/", 1)[-1],
            "country_options": countries,
            "position_options": positions,
            "height_options_cm": sorted(set(heights)),
            "source_image_ref": image,
            "candidate_generation": "wikidata",
        }
        foot = next(iter(foot_values)) if len(foot_values) == 1 else None
        candidates.append(
            CatalogueRecord(
                source_id=f"wikidata:{item.rsplit('/', 1)[-1]}",
                full_name=first.label,
                country_code=countries[0] if len(countries) == 1 else None,
                date_of_birth=dob,
                historical_height_cm=heights[0] if len(set(heights)) == 1 else None,
                position_candidates=positions,
                preferred_foot=foot,
                source_evidence=[evidence],
                football_evidence=[evidence],
                metadata=metadata,
                blocking_reasons=["requires_editorial_football_enrichment"],
            )
        )
    return candidates
