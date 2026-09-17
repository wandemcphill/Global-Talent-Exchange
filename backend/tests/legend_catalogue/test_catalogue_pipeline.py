from datetime import date

from app.legend_catalogue.schema import CatalogueBundle, CatalogueRecord, Evidence
from app.legend_catalogue.selection import select_candidates
from app.legend_catalogue.validation import evaluate_release, record_blockers


def _record(**overrides) -> CatalogueRecord:
    payload = {
        "source_id": "wikidata:Q123",
        "full_name": "Example Player",
        "country_code": "NGA",
        "date_of_birth": date(1975, 1, 1),
        "historical_height_cm": 180,
        "position_candidates": ["forward"],
        "primary_position": "ST",
        "preferred_foot": "right",
        "era": "1990s",
        "legendary_classification": "icon",
        "signature_traits": ["composure"],
        "technical_profile": {"finishing": 90},
        "physical_profile": {"stamina": 80},
        "mental_profile": {"composure": 90},
        "source_evidence": [Evidence(provider="wikidata", uri="https://www.wikidata.org/wiki/Q123")],
        "football_evidence": [Evidence(provider="wikidata", uri="https://www.wikidata.org/wiki/Q123")],
        "portrait_metadata": {"is_fictional_non_replicative": True},
        "editorial_status": "approved",
        "rights_status": "approved",
        "catalogue_status": "approved",
    }
    payload.update(overrides)
    return CatalogueRecord.model_validate(payload)


def test_release_gate_requires_exact_target_and_complete_records() -> None:
    bundle = CatalogueBundle(
        generated_at="2026-09-17T00:00:00Z",
        source="test",
        target_count=1,
        records=[_record()],
    )
    result = evaluate_release(bundle)
    assert result.ready is True
    assert result.eligible_count == 1


def test_missing_editorial_data_blocks_release() -> None:
    record = _record(editorial_status="editorial_review", rights_status="pending")
    blockers = record_blockers(record)
    assert "editorial_not_approved" in blockers
    assert "rights_not_approved" in blockers


def test_duplicate_source_ids_are_blocked() -> None:
    bundle = CatalogueBundle(
        generated_at="2026-09-17T00:00:00Z",
        source="test",
        target_count=2,
        records=[_record(), _record()],
    )
    result = evaluate_release(bundle)
    assert result.ready is False
    assert result.duplicate_count == 1


def test_source_portrait_reference_blocks_release() -> None:
    blockers = record_blockers(
        _record(
            portrait_metadata={
                "is_fictional_non_replicative": True,
                "source_image_ref": "https://commons.wikimedia.org/example.jpg",
            }
        )
    )
    assert "portrait_contains_source_image_reference" in blockers


def test_selection_caps_country_and_prefers_known_complete_records() -> None:
    records = [
        _record(source_id="wikidata:Q2", full_name="Unknown Player", country_code=None, date_of_birth=None),
        _record(source_id="wikidata:Q3", full_name="Nigeria B", country_code="NGA"),
        _record(source_id="wikidata:Q4", full_name="Nigeria C", country_code="NGA"),
        _record(source_id="wikidata:Q5", full_name="Ghana A", country_code="GHA"),
    ]

    selected = select_candidates(records, target_count=3, max_per_country=1)

    assert len(selected) == 3
    assert {record.country_code for record in selected} == {"NGA", "GHA", None}
    assert selected[0].country_code == "GHA"


def test_selection_deduplicates_source_ids_deterministically() -> None:
    records = [
        _record(source_id="wikidata:Q1", full_name="Same", technical_profile={}),
        _record(source_id="wikidata:Q1", full_name="Same Better"),
    ]

    selected = select_candidates(records, target_count=1)

    assert len(selected) == 1
    assert selected[0].source_id == "wikidata:Q1"
