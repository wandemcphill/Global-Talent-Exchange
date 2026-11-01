from __future__ import annotations

import json
from pathlib import Path

from app.legend_catalogue.enrichment import EnrichmentBundle

CATALOGUE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "legendary_catalogue" / "legendary_catalogue_staging_v1.json"
)
ENRICHMENT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "legendary_catalogue"
    / "enrichment"
    / "batch_003_legend_nationality_corrections_20261101.json"
)


def test_legendary_catalogue_nationality_corrections() -> None:
    data = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    records = {r["legendary_profile_id"]: r for r in data["records"]}

    # Fabien Barthez -> France (FRA)
    barthez = records.get("legendary-wikidata-q191139")
    assert barthez is not None
    assert barthez["nationality"] == "France"
    assert barthez["nationality_code"] == "FRA"

    # Roger Milla -> Cameroon (CMR)
    milla = records.get("legendary-wikidata-q168540")
    assert milla is not None
    assert milla["nationality"] == "Cameroon"
    assert milla["nationality_code"] == "CMR"

    # Goran Pandev -> North Macedonia (MKD)
    pandev = records.get("legendary-wikidata-q208833")
    assert pandev is not None
    assert pandev["nationality"] in {"North Macedonia", "Macedonia"}
    assert pandev["nationality_code"] == "MKD"

    # Frédéric Kanouté -> Mali (MLI)
    kanoute = records.get("legendary-wikidata-q211516")
    assert kanoute is not None
    assert kanoute["nationality"] == "Mali"
    assert kanoute["nationality_code"] == "MLI"

    # Ian Rush -> Wales (WAL)
    rush = records.get("legendary-wikidata-q233581")
    assert rush is not None
    assert rush["nationality"] == "Wales"
    assert rush["nationality_code"] == "WAL"

    # Kenny Dalglish -> Scotland (SCO)
    dalglish = records.get("legendary-wikidata-q187198")
    assert dalglish is not None
    assert dalglish["nationality"] == "Scotland"
    assert dalglish["nationality_code"] == "SCO"

    # Dwight Yorke -> Trinidad and Tobago (TTO)
    yorke = records.get("legendary-wikidata-q192175")
    assert yorke is not None
    assert yorke["nationality"] == "Trinidad and Tobago"
    assert yorke["nationality_code"] == "TTO"


def test_no_generic_united_kingdom_nationality_in_legendary_staging() -> None:
    data = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    uk_records = [
        r["full_name"]
        for r in data["records"]
        if r.get("nationality") == "United Kingdom" or r.get("nationality_code") == "GBR"
    ]
    assert uk_records == [], f"Found legends with generic UK nationality: {uk_records}"


def test_enrichment_bundle_batch_003_is_valid() -> None:
    bundle = EnrichmentBundle.model_validate_json(ENRICHMENT_PATH.read_text(encoding="utf-8"))
    assert bundle.schema_version == "legendary-enrichment-v1"
    assert len(bundle.patches) == 7

    source_ids = {p.source_id for p in bundle.patches}
    expected_ids = {
        "wikidata:Q191139",  # Barthez
        "wikidata:Q168540",  # Milla
        "wikidata:Q208833",  # Pandev
        "wikidata:Q211516",  # Kanoute
        "wikidata:Q233581",  # Rush
        "wikidata:Q187198",  # Dalglish
        "wikidata:Q192175",  # Yorke
    }
    assert source_ids == expected_ids
