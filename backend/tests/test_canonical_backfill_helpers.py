from __future__ import annotations

from app.ingestion.canonical_backfill_helpers import (
    build_provider_reference_key,
    compare_candidate_evidence,
    normalize_footballsquads_provider_key,
    prepare_club_create_plan,
    prepare_country_create_plan,
)
from app.ingestion.models import Club


def test_provider_reference_key_normalization_is_deterministic_for_footballsquads() -> None:
    assert normalize_footballsquads_provider_key(" engprem:arsenal ") == "engprem-arsenal"
    assert normalize_footballsquads_provider_key("engprem/2023-2024") == "engprem-2023-2024"
    assert build_provider_reference_key(
        source_name="footballsquads",
        entity_type="club",
        provider_external_id="engprem:arsenal",
        display_name="Arsenal",
        competition_external_id="engprem-2023-2024",
    ) == "engprem-arsenal"
    assert build_provider_reference_key(
        source_name="curated-feed",
        entity_type="competition",
        display_name="Premier League",
        country_name="England",
    ) == "england-premier-league"


def test_country_and_club_create_plans_capture_idempotent_lookup_keys() -> None:
    country_plan = prepare_country_create_plan(
        source_name="footballsquads",
        provider_external_id="AL",
        display_name="Albania",
        country_code="AL",
    )
    assert country_plan.provider_lookup_key == ("footballsquads", "AL")
    assert country_plan.provider_reference_key == "al"
    assert country_plan.country_code_values == ("AL",)
    assert country_plan.payload["alpha2_code"] == "AL"
    assert country_plan.natural_lookup_keys == (
        ("name", "Albania"),
        ("alpha2_code", "AL"),
    )

    club_plan = prepare_club_create_plan(
        source_name="footballsquads",
        provider_external_id="engprem:arsenal",
        display_name="Arsenal",
        country_id="country-eng",
        competition_id="competition-engprem",
        competition_external_id="engprem-2023-2024",
        competition_display_name="English Premier League 2023/2024",
        extra_fields={
            "short_name": "Arsenal",
            "is_tradable": True,
        },
    )
    assert club_plan.provider_lookup_key == ("footballsquads", "engprem:arsenal")
    assert club_plan.provider_reference_key == "engprem-arsenal"
    assert club_plan.payload == {
        "source_provider": "footballsquads",
        "provider_external_id": "engprem:arsenal",
        "country_id": "country-eng",
        "current_competition_id": "competition-engprem",
        "name": "Arsenal",
        "slug": "arsenal",
        "short_name": "Arsenal",
        "is_tradable": True,
    }
    assert club_plan.natural_lookup_keys == (
        ("name", "Arsenal"),
        ("slug", "arsenal"),
        ("short_name", "Arsenal"),
        ("country_id", "country-eng"),
        ("current_competition_id", "competition-engprem"),
    )


def test_candidate_evidence_surfaces_support_and_context_blocks() -> None:
    plan = prepare_club_create_plan(
        source_name="footballsquads",
        provider_external_id="engprem:arsenal",
        display_name="Arsenal",
        country_id="country-eng",
        competition_id="competition-engprem",
        competition_external_id="engprem-2023-2024",
    )
    matching_candidate = Club(
        id="club-arsenal-ok",
        source_provider="football_data",
        provider_external_id="57",
        country_id="country-eng",
        current_competition_id="competition-engprem",
        name="Arsenal",
        slug="arsenal",
        short_name="Arsenal",
        is_tradable=True,
    )
    blocked_candidate = Club(
        id="club-arsenal-blocked",
        source_provider="football_data",
        provider_external_id="58",
        country_id="country-eng",
        current_competition_id="competition-ucl",
        name="Arsenal",
        slug="arsenal",
        short_name="Arsenal",
        is_tradable=True,
    )

    matching_evidence = compare_candidate_evidence(plan, matching_candidate)
    blocked_evidence = compare_candidate_evidence(plan, blocked_candidate)

    assert matching_evidence.supporting_signals == (
        "normalized_name",
        "slug",
        "short_name",
        "country_context",
        "competition_context",
    )
    assert matching_evidence.blocking_signals == ()
    assert blocked_evidence.supporting_signals == (
        "normalized_name",
        "slug",
        "short_name",
        "country_context",
    )
    assert blocked_evidence.blocking_signals == ("competition_context",)
