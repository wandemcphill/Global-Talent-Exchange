from __future__ import annotations

import json
from pathlib import Path

from app.legend_catalogue.enrichment import EnrichmentBundle


BATCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "legendary_catalogue"
    / "enrichment"
    / "batch_001_core_legends_20260917.json"
)


def test_core_legends_batch_is_factual_only_and_approval_gated() -> None:
    bundle = EnrichmentBundle.model_validate_json(BATCH_PATH.read_text(encoding="utf-8"))
    assert len(bundle.patches) == 9

    source_ids = [patch.source_id for patch in bundle.patches]
    assert len(source_ids) == len(set(source_ids))
    assert set(source_ids) == {
        "wikidata:Q12897",
        "wikidata:Q17515",
        "wikidata:Q17163",
        "wikidata:Q4457",
        "wikidata:Q1835",
        "wikidata:Q483027",
        "wikidata:Q1255625",
        "wikidata:Q605817",
        "wikidata:Q482931",
    }

    for patch in bundle.patches:
        dumped = json.loads(patch.model_dump_json())
        assert dumped["editorial_status"] == "enriched"
        assert dumped["catalogue_status"] == "staged"
        assert dumped["rights_status"] == "unknown"
        assert patch.portrait_metadata is None
        assert patch.technical_profile is None
        assert patch.physical_profile is None
        assert patch.mental_profile is None
        assert patch.preferred_foot is None
        assert patch.era is None
        assert patch.signature_traits is None
        assert patch.signature_role is None
        assert "deferred" in (patch.source_notes or "")
