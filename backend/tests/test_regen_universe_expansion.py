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
        assert [item["age"] for item in seeds[:4]] == [17, 18, 19, 20]
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
            country_codes=["9df3949b-a863-4720-bdf1-974409b536e1"],
            seeds_per_country=4,
            age_min=14,
            age_max=17,
            include_legendary_regens=False,
            preseed_batch="uuid_fallback",
        )

        assert len(seeds) == 4
        assert [item["age"] for item in seeds] == [14, 15, 16, 17]
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
            age_min=14,
            age_max=17,
            include_legendary_regens=False,
            preseed_batch="legacy_batch",
        )

        assert rerun == []
    finally:
        session.close()


def test_preseeded_national_regens_do_not_reuse_colliding_legacy_country_codes() -> None:
    session = build_regen_universe_session()
    try:
        alpha = Country(
            id="11111111-1111-4111-8111-111111111111",
            source_provider="test",
            provider_external_id="country-alpha",
            name="Alpha Isles",
            alpha2_code=None,
            alpha3_code=None,
            fifa_code=None,
            confederation_code="CONCACAF",
            market_region="caribbean",
            is_enabled_for_universe=True,
        )
        beta = Country(
            id="22222222-2222-4222-8222-222222222222",
            source_provider="test",
            provider_external_id="country-beta",
            name="Beta Isles",
            alpha2_code=None,
            alpha3_code=None,
            fifa_code=None,
            confederation_code="CONCACAF",
            market_region="caribbean",
            is_enabled_for_universe=True,
        )
        session.add_all([alpha, beta])
        session.add(
            NationalRegenSeed(
                seed_key="legacy_batch:NL1:1:GK",
                display_name="Alpha Legacy 1",
                country_code="NL1",
                country_name="Alpha Isles",
                confederation_code="CONCACAF",
                seed_type="preseeded_national_pool",
                generation_index=1,
                primary_position="GK",
                secondary_positions_json=[],
                current_rating=71,
                potential_rating=81,
                growth_curve=0.5,
                personality_seed_json={},
                rarity_tier="common",
                status="available",
                preseed_batch="legacy_batch",
                metadata_json={},
            )
        )
        session.add(
            NationalRegenSeed(
                seed_key="legacy_batch:NL1:2:CB",
                display_name="Beta Legacy 1",
                country_code="NL1",
                country_name="Beta Isles",
                confederation_code="CONCACAF",
                seed_type="preseeded_national_pool",
                generation_index=1,
                primary_position="CB",
                secondary_positions_json=["RB"],
                current_rating=72,
                potential_rating=82,
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
        seeds = service.seed_preseeded_national_regens(
            country_codes=[beta.id],
            seeds_per_country=4,
            age_min=14,
            age_max=17,
            include_legendary_regens=False,
            preseed_batch="new_batch",
        )

        assert len(seeds) == 4
        assert all(item["country_name"] == "Beta Isles" for item in seeds)
        assert all(item["country_code"].startswith("C") for item in seeds)
        assert all(item["country_code"] != "NL1" for item in seeds)
    finally:
        session.close()


def test_preseeded_national_regens_fallback_when_natural_country_code_is_claimed_by_another_country() -> None:
    session = build_regen_universe_session()
    try:
        legacy = Country(
            id="33333333-3333-4333-8333-333333333333",
            source_provider="test",
            provider_external_id="country-legacy",
            name="Legacy Owner",
            alpha2_code=None,
            alpha3_code=None,
            fifa_code=None,
            confederation_code="CAF",
            market_region="africa",
            is_enabled_for_universe=True,
        )
        senegal = Country(
            id="44444444-4444-4444-8444-444444444444",
            source_provider="test",
            provider_external_id="country-senegal",
            name="Senegal",
            alpha2_code=None,
            alpha3_code=None,
            fifa_code="SEN1",
            confederation_code="CAF",
            market_region="africa",
            is_enabled_for_universe=True,
        )
        session.add_all([legacy, senegal])
        session.add(
            NationalRegenSeed(
                seed_key="legacy_batch:SEN1:1:GK",
                display_name="Legacy Senegal Code Owner",
                country_code="SEN1",
                country_name="Legacy Owner",
                confederation_code="CAF",
                seed_type="preseeded_national_pool",
                generation_index=1,
                primary_position="GK",
                secondary_positions_json=[],
                current_rating=75,
                potential_rating=85,
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
        seeds = service.seed_preseeded_national_regens(
            country_codes=[senegal.id],
            seeds_per_country=4,
            age_min=14,
            age_max=17,
            include_legendary_regens=False,
            preseed_batch="senegal_batch",
        )

        assert len(seeds) == 4
        assert all(item["country_name"] == "Senegal" for item in seeds)
        assert all(item["country_code"].startswith("C") for item in seeds)
        assert all(item["country_code"] != "SEN1" for item in seeds)
    finally:
        session.close()


def test_preseeded_national_regens_support_extra_u17_batch_sizes() -> None:
    session = build_regen_universe_session()
    try:
        seed_two_season_universe(session)
        service = RegenUniverseExpansionService(session)

        seeds = service.seed_preseeded_national_regens(
            country_codes=["NG"],
            seeds_per_country=24,
            age_min=14,
            age_max=17,
            include_legendary_regens=True,
            preseed_batch="u17_batch",
        )

        assert len(seeds) == 24
        assert [item["age"] for item in seeds[:8]] == [14, 15, 16, 17, 14, 15, 16, 17]
        assert all(14 <= int(item["age"]) <= 17 for item in seeds)
        assert all(item["metadata"]["age_band"] == "14-17" for item in seeds)
        assert all(item["metadata"]["source_generation"] == "preseeded_u17_batch" for item in seeds)
    finally:
        session.close()
