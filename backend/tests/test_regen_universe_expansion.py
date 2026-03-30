from __future__ import annotations

from app.ingestion.models import Country
from app.models.regen_ecosystem import NationalRegenSeed
from app.regen_universe.expansion_service import RegenUniverseExpansionService
from tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def test_preseeded_national_regens_are_balanced_and_globally_tracked() -> None:
    session = build_regen_universe_session()
    try:
        seed_two_season_universe(session)
        service = RegenUniverseExpansionService(session)

        seeds = service.seed_preseeded_national_regens(
            country_codes=["NG"],
            seeds_per_country=10,
            include_legendary_regens=True,
            preseed_batch="test_batch",
        )
        rerun = service.seed_preseeded_national_regens(
            country_codes=["NG"],
            seeds_per_country=10,
            include_legendary_regens=True,
            preseed_batch="test_batch",
        )
        tracking = service.build_regen_tracking()
        listed = service.list_preseeded_national_regens(country_code="NG", limit=20)

        assert len(seeds) == 10
        assert rerun == []
        assert [item["primary_position"] for item in seeds] == [
            "GK",
            "CB",
            "RB",
            "LB",
            "DM",
            "CM",
            "AM",
            "RW",
            "LW",
            "ST",
        ]
        assert seeds[0]["rarity_tier"] == "legendary"
        assert len([item for item in listed if item["seed_type"] == "legendary_regen"]) == 1
        assert tracking["total_seeded_players"] == 10
        assert tracking["global_peak_rating"] >= max(item["potential_rating"] for item in seeds)
        nigeria_bucket = next(
            item for item in tracking["country_distribution"] if item["metadata"]["country_code"] == "NG"
        )
        assert nigeria_bucket["count"] == 10
    finally:
        session.close()


def test_preseeded_national_regens_fallback_to_short_country_code_when_source_codes_are_missing() -> None:
    session = build_regen_universe_session()
    try:
        country = Country(
            id="9df3949b-a863-4720-bdf1-974409b536e1",
            source_provider="test",
            provider_external_id="country-bq",
            name="Bonaire",
            alpha2_code=None,
            alpha3_code=None,
            fifa_code=None,
            confederation_code="CONCACAF",
            market_region="caribbean",
            is_enabled_for_universe=True,
        )
        session.add(country)
        session.commit()

        service = RegenUniverseExpansionService(session)
        seeds = service.seed_preseeded_national_regens(
            seeds_per_country=4,
            include_legendary_regens=False,
            preseed_batch="uuid_fallback",
        )

        assert len(seeds) == 4
        assert {item["country_name"] for item in seeds} == {"Bonaire"}
        assert {item["country_code"] for item in seeds} == {"C2682C06"}
        assert all(len(item["country_code"]) <= 8 for item in seeds)
    finally:
        session.close()


def test_preseeded_national_regens_reuse_existing_country_code_for_legacy_seed_rows() -> None:
    session = build_regen_universe_session()
    try:
        country = Country(
            id="9df3949b-a863-4720-bdf1-974409b536e1",
            source_provider="test",
            provider_external_id="country-bq",
            name="Bonaire",
            alpha2_code=None,
            alpha3_code=None,
            fifa_code=None,
            confederation_code="CONCACAF",
            market_region="caribbean",
            is_enabled_for_universe=True,
        )
        session.add(country)
        for index, position in enumerate(("GK", "CB", "RB", "LB"), start=1):
            session.add(
                NationalRegenSeed(
                    seed_key=f"legacy_batch:LEGACY1:{index}:{position}",
                    display_name=f"Legacy Seed {index}",
                    country_code="LEGACY1",
                    country_name="Bonaire",
                    confederation_code="CONCACAF",
                    seed_type="preseeded_national_pool",
                    generation_index=1,
                    primary_position=position,
                    secondary_positions_json=[],
                    current_rating=70 + index,
                    potential_rating=80 + index,
                    growth_curve=0.5,
                    personality_seed_json={},
                    rarity_tier="common",
                    status="available",
                    preseed_batch="legacy_batch",
                    metadata_json={},
                )
            )
        session.commit()

        service = RegenUniverseExpansionService(session)
        rerun = service.seed_preseeded_national_regens(
            seeds_per_country=4,
            include_legendary_regens=False,
            preseed_batch="legacy_batch",
        )

        assert rerun == []
    finally:
        session.close()
