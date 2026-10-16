from __future__ import annotations

from dataclasses import replace
import random

from app.core.config import get_settings
from app.services.club_finance_service import ClubOpsStore
from app.services.regen_service import (
    LineageCandidate,
    OwnerSonContext,
    RegenClubContext,
    RegenGenerationEngine,
    RegenService,
)


def _settings_with(**overrides):
    settings = get_settings()
    regen_config = replace(settings.regen_generation, **overrides)
    return replace(settings, regen_generation=regen_config)


def test_lineage_generation_respects_nationality_and_geo() -> None:
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
            ref_id="legend-ng-1",
            display_name="Samuel Adekunle",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        ),
    )
    club_context = RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos")
    generated = engine.generate_academy_intake(
        club_id="club-lagos",
        season_label="2026/2027",
        club_context=club_context,
        intake_size=1,
        lineage_pool=lineage_pool,
        rng=random.Random(12),
    )
    regen = generated.regens[0]
    assert regen.lineage is not None
    assert regen.lineage.related_legend_type == "real_legend"
    assert regen.birth_country_code == "NG"

    mismatched_pool = (
        LineageCandidate(
            legend_type="real_legend",
            ref_id="legend-it-1",
            display_name="Marco Rossi",
            country_code="IT",
            region_name="Lazio",
            city_name="Rome",
        ),
    )
    generated_mismatch = engine.generate_academy_intake(
        club_id="club-lagos",
        season_label="2027/2028",
        club_context=club_context,
        intake_size=1,
        lineage_pool=mismatched_pool,
        rng=random.Random(7),
    )
    regen_mismatch = generated_mismatch.regens[0]
    assert regen_mismatch.lineage is None
    assert regen_mismatch.is_special_lineage is False


def test_owner_son_lifetime_max() -> None:
    settings = _settings_with(
        lineage_base_probability=1.0,
        lineage_owner_probability=1.0,
        lineage_legend_probability=0.0,
        lineage_retired_regen_probability=0.0,
        lineage_hometown_probability=0.0,
        twin_probability=0.0,
        owner_son_lifetime_cap=3,
    )
    store = ClubOpsStore()
    regen_service = RegenService(store=store, settings=settings)
    club_context = RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos")
    owner_context = OwnerSonContext(
        owner_user_id="user-owner-1",
        club_id="club-lagos",
        club_country_code="NG",
        club_region_name="Lagos",
        club_city_name="Lagos",
    )
    seasons = ("2025/2026", "2026/2027", "2027/2028", "2028/2029")
    for idx, season in enumerate(seasons, start=1):
        regen_service.generate_academy_intake(
            club_id="club-lagos",
            club_context=club_context,
            season_label=season,
            intake_size=2,
            random_seed=idx,
            owner_context=owner_context,
        )
    owner_sons = [
        regen
        for regen in regen_service.list_regens("club-lagos")
        if regen.metadata.get("club_owner_son")
    ]
    assert len(owner_sons) == settings.regen_generation.owner_son_lifetime_cap
    assert store.owner_son_lifetime_counts_by_user["user-owner-1"] == settings.regen_generation.owner_son_lifetime_cap


def test_paid_owner_son_request_flow() -> None:
    settings = _settings_with(
        lineage_base_probability=0.0,
        lineage_owner_probability=0.0,
        twin_probability=0.0,
    )
    store = ClubOpsStore()
    regen_service = RegenService(store=store, settings=settings)
    request = regen_service.request_owner_son(
        club_id="club-lagos",
        owner_user_id="user-owner-2",
        customization={"name": "Chinedu", "position": "ST"},
    )
    expected_cost = (
        settings.regen_generation.owner_son_paid_request_base_cost
        + settings.regen_generation.owner_son_paid_request_name_cost
        + settings.regen_generation.owner_son_paid_request_customization_cost
    )
    assert request.total_cost_coin == expected_cost
    club_context = RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos")
    batch = regen_service.generate_academy_intake(
        club_id="club-lagos",
        club_context=club_context,
        season_label="2029/2030",
        intake_size=2,
        random_seed=8,
        owner_son_request_id=request.request_id,
    )
    assert request in store.owner_son_fulfilled_requests_by_club["club-lagos"]
    assert request not in store.owner_son_pending_requests_by_club["club-lagos"]
    assert any(
        regen.metadata.get("club_owner_son")
        for regen in regen_service.list_regens("club-lagos")
    )


def test_twin_generation_rarity() -> None:
    settings = _settings_with(
        twin_probability=1.0,
        lineage_base_probability=0.0,
        lineage_legend_probability=0.0,
        lineage_owner_probability=0.0,
        lineage_retired_regen_probability=0.0,
        lineage_hometown_probability=0.0,
    )
    engine = RegenGenerationEngine(settings)
    club_context = RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos")
    generated = engine.generate_academy_intake(
        club_id="club-lagos",
        season_label="2030/2031",
        club_context=club_context,
        intake_size=2,
        rng=random.Random(3),
    )
    assert len(generated.regens) == 2
    twins_key = {regen.metadata.get("twins_group_key") for regen in generated.regens}
    assert len(twins_key) == 1
    variants = {regen.metadata.get("twin_variant") for regen in generated.regens}
    assert variants == {"A", "B"}
    seeds = {regen.metadata.get("visual_profile", {}).get("portrait_seed") for regen in generated.regens}
    assert len(seeds) == 1
    assert generated.regens[0].current_ability_range != generated.regens[1].current_ability_range


def test_celebrity_lineage_requires_license() -> None:
    settings = _settings_with(
        lineage_base_probability=1.0,
        lineage_legend_probability=1.0,
        lineage_owner_probability=0.0,
        lineage_retired_regen_probability=0.0,
        lineage_hometown_probability=0.0,
        twin_probability=0.0,
    )
    engine = RegenGenerationEngine(settings)
    club_context = RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos")
    unlicensed_pool = (
        LineageCandidate(
            legend_type="real_legend",
            ref_id="celebrity-1",
            display_name="Celebrity Star",
            country_code="NG",
            is_celebrity=True,
            is_licensed=False,
        ),
    )
    generated = engine.generate_academy_intake(
        club_id="club-lagos",
        season_label="2031/2032",
        club_context=club_context,
        intake_size=1,
        lineage_pool=unlicensed_pool,
        rng=random.Random(4),
    )
    assert generated.regens[0].lineage is None

    licensed_pool = (
        LineageCandidate(
            legend_type="real_legend",
            ref_id="celebrity-2",
            display_name="Celebrity Star",
            country_code="NG",
            is_celebrity=True,
            is_licensed=True,
        ),
    )
    generated_licensed = engine.generate_academy_intake(
        club_id="club-lagos",
        season_label="2032/2033",
        club_context=club_context,
        intake_size=1,
        lineage_pool=licensed_pool,
        rng=random.Random(5),
    )
    assert generated_licensed.regens[0].lineage is not None
