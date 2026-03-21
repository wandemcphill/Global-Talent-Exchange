from app.manager_market.seed_catalog import CATALOG_VERSION, build_seed_catalog


def test_seed_catalog_includes_tunde_oni() -> None:
    catalog = build_seed_catalog()
    tunde = next(item for item in catalog if item["name"] == "Tunde Oni")

    assert CATALOG_VERSION >= 5
    assert tunde["mentality"] == "balanced"
    assert tunde["rarity"] == "elite_active"
    assert tunde["club_associations"] == ["Nigeria"]
    assert set(tunde["tactics"]) == {
        "counter_attack",
        "technical_build_up",
        "set_piece_focus",
        "youth_development_system",
    }
    assert set(tunde["traits"]) == {
        "develops_young_players",
        "tactical_flexibility",
        "technical_coaching",
        "quick_substitution",
    }
    assert "3-4-3" in tunde["philosophy"]
    assert "4-1-2-1-2 diamond" in tunde["philosophy"]
    assert "3-4-1-2" in tunde["philosophy"]
    assert "great motivator" in tunde["philosophy"]
    assert "play through the middle" in tunde["philosophy"]
    assert "short passing" in tunde["philosophy"]
