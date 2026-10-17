from __future__ import annotations

import json
from pathlib import Path

from app.legend_catalogue.enrichment import EnrichmentBundle


BATCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "legendary_catalogue"
    / "enrichment"
    / "batch_002_abedi_pele_20260917.json"
)


def test_abedi_pele_footedness_is_left_with_two_foot_capability_preserved() -> None:
    bundle = EnrichmentBundle.model_validate_json(BATCH_PATH.read_text(encoding="utf-8"))
    assert len(bundle.patches) == 1

    patch = bundle.patches[0]
    assert patch.source_id == "wikidata:Q336916"
    assert patch.preferred_foot == "left"

    dumped = json.loads(patch.model_dump_json())
    assert dumped["metadata"]["two_foot_capability"] is True
    assert dumped["editorial_status"] == "enriched"
    assert dumped["catalogue_status"] == "staged"
    assert dumped["rights_status"] == "unknown"
    assert patch.portrait_metadata is None
    assert patch.technical_profile is None
    assert patch.physical_profile is None
    assert patch.mental_profile is None
    assert patch.era is None
    assert patch.signature_traits is None
    assert patch.signature_role is None
    assert "deferred" in (patch.source_notes or "")
    assert any("preferred_foot" in evidence.claim_types for evidence in patch.football_evidence or [])
