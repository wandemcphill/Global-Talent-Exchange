from __future__ import annotations

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
        tracking = service.build_regen_tracking()
        listed = service.list_preseeded_national_regens(country_code="NG", limit=20)

        assert len(seeds) == 10
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
