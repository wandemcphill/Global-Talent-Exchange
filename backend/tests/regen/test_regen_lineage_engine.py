from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.config import get_settings
from app.services.club_finance_service import ClubOpsStore
from app.services.regen_service import (
    LineageCandidate,
    RegenClubContext,
    RegenGenerationEngine,
    RegenService,
)


def _settings_with(**overrides):
    settings = get_settings()
    regen_generation = replace(settings.regen_generation, **overrides)
    return replace(settings, regen_generation=regen_generation)


def _club_context():
    return RegenClubContext(
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        urbanicity="urban",
    )


def test_lineage_generation_coherence():
    settings = _settings_with(
        lineage_base_probability=1.0,
        lineage_legend_probability=1.0,
        lineage_owner_probability=0.0,
        lineage_retired_regen_probability=0.0,
        lineage_hometown_probability=0.0,
        twin_probability=0.0,
    )
    engine = RegenGenerationEngine(settings)
    lineage_pool = (
        LineageCandidate(
            legend_type="real_legend",
            ref_id="legend-okocha",
            display_name="Jay Okocha",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        ),
    )
    generated = engine.generate_academy_intake(
        club_id="club-legend",
        season_label="2025/2026",
        club_context=_club_context(),
        intake_size=3,
        lineage_pool=lineage_pool,
    )
    lineage_count = sum(1 for regen in generated.regens if regen.metadata.get("lineage"))
    assert lineage_count == 1


def test_lineage_geography_consistency():
    settings = _settings_with(
        lineage_base_probability=1.0,
        lineage_legend_probability=1.0,
        lineage_owner_probability=0.0,
        lineage_retired_regen_probability=0.0,
        lineage_hometown_probability=0.0,
        twin_probability=0.0,
    )
    engine = RegenGenerationEngine(settings)
    lineage_pool = (
        LineageCandidate(
            legend_type="real_legend",
            ref_id="legend-ng",
            display_name="Nigerian Legend",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        ),
        LineageCandidate(
            legend_type="real_legend",
            ref_id="legend-it",
            display_name="Italian Legend",
            country_code="IT",
            region_name="Lazio",
            city_name="Rome",
        ),
    )
    generated = engine.generate_academy_intake(
        club_id="club-ng",
        season_label="2025/2026",
        club_context=_club_context(),
        intake_size=1,
        lineage_pool=lineage_pool,
    )
    regen = generated.regens[0]
    assert regen.birth_country_code == "NG"
    assert regen.metadata.get("lineage", {}).get("lineage_country_code") == "NG"


def test_owner_son_paid_request_flow_and_customization():
    settings = _settings_with(
        lineage_base_probability=0.0,
        twin_probability=0.0,
    )
    store = ClubOpsStore()
    service = RegenService(store=store, settings=settings, engine=RegenGenerationEngine(settings))
    request = service.request_owner_son(
        club_id="club-owner",
        owner_user_id="user-1",
        customization={
            "name": "Ayo Adekunle",
            "position": "ST",
            "favorite_foot": "left",
            "height_cm": 188,
            "hairstyle": "braids",
        },
    )
    batch = service.generate_academy_intake(
        club_id="club-owner",
        club_context=_club_context(),
        season_label="2025/2026",
        intake_size=2,
        owner_son_request_id=request.request_id,
    )
    assert request not in store.owner_son_pending_requests_by_club["club-owner"]
    assert request in store.owner_son_fulfilled_requests_by_club["club-owner"]
    regens = service.list_regens("club-owner")
    owner_regens = [regen for regen in regens if regen.metadata.get("lineage")]
    assert owner_regens
    owner_regen = owner_regens[0]
    assert owner_regen.display_name.startswith("Ayo Adekunle")
    assert owner_regen.primary_position == "ST"
    lineage = owner_regen.metadata.get("lineage", {})
    assert lineage.get("is_owner_son") is True
    customization = lineage.get("customization", {})
    assert customization.get("favorite_foot") == "left"
    assert customization.get("height_cm") == 188
    assert customization.get("hairstyle") == "braids"
    assert owner_regen.metadata.get("visual_profile", {}).get("hair_profile") == "braids"
    assert batch.intake_size == 2


def test_owner_son_lifetime_cap_enforced():
    settings = _settings_with(
        lineage_base_probability=0.0,
        twin_probability=0.0,
        owner_son_lifetime_cap=1,
    )
    store = ClubOpsStore()
    service = RegenService(store=store, settings=settings, engine=RegenGenerationEngine(settings))
    request = service.request_owner_son(
        club_id="club-cap",
        owner_user_id="owner-cap",
        customization={"name": "Cap Player"},
    )
    store.owner_son_lifetime_counts_by_user["owner-cap"] = 1
    with pytest.raises(ValueError, match="owner_son_lifetime_cap_reached"):
        service.generate_academy_intake(
            club_id="club-cap",
            club_context=_club_context(),
            season_label="2025/2026",
            intake_size=2,
            owner_son_request_id=request.request_id,
        )


def test_celebrity_lineage_requires_license():
    settings = _settings_with(
        lineage_base_probability=1.0,
        lineage_legend_probability=1.0,
        lineage_owner_probability=0.0,
        lineage_retired_regen_probability=0.0,
        lineage_hometown_probability=0.0,
        twin_probability=0.0,
    )
    engine = RegenGenerationEngine(settings)
    candidate = LineageCandidate(
        legend_type="real_legend",
        ref_id="celeb-1",
        display_name="Celebrity Star",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        is_celebrity=True,
        is_licensed=False,
    )
    allowed = engine._lineage_candidate_allowed(candidate, "club-celeb", _club_context())
    assert allowed is False


def test_twins_generated_when_probability_hits():
    settings = _settings_with(
        lineage_base_probability=0.0,
        twin_probability=1.0,
    )
    engine = RegenGenerationEngine(settings)
    generated = engine.generate_academy_intake(
        club_id="club-twins",
        season_label="2025/2026",
        club_context=_club_context(),
        intake_size=3,
    )
    twins = [regen for regen in generated.regens if regen.metadata.get("twins_group_key")]
    assert len(twins) == 2
    assert twins[0].metadata.get("twins_group_key") == twins[1].metadata.get("twins_group_key")
    assert twins[0].is_special_lineage is True
    assert twins[1].is_special_lineage is True


def test_twins_not_generated_when_probability_zero():
    settings = _settings_with(
        lineage_base_probability=0.0,
        twin_probability=0.0,
    )
    engine = RegenGenerationEngine(settings)
    generated = engine.generate_academy_intake(
        club_id="club-no-twins",
        season_label="2025/2026",
        club_context=_club_context(),
        intake_size=3,
    )
    assert not any(regen.metadata.get("twins_group_key") for regen in generated.regens)
