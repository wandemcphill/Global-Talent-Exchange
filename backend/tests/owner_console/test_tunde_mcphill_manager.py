from app.owner_console.engine import EXECUTIVE_STAFF_CATALOG, manager_profile


def test_tunde_mcphill_is_a_locked_first_team_manager() -> None:
    coach = next(item for item in EXECUTIVE_STAFF_CATALOG if item["id"] == "mgr_tunde_mcphill")
    profile = manager_profile({**coach, "manager_id": coach["id"]})

    assert coach["role"] == "first_team_manager"
    assert profile["name"] == "Tunde Mc'Phill"
    assert profile["age"] == 37
    assert profile["gsi"] == 76
    assert profile["potential"] == 88
    assert profile["tactical_preference"] == "balanced"
    assert profile["preferred_formation"] == "3-4-3"
    assert profile["preferred_formations"] == ["3-4-3", "4-3-3", "4-1-2-1-2", "3-5-2", "3-6-1"]
    assert profile["tactics"] == ["3-4-3", "4-3-3", "4-1-2-1-2", "3-5-2", "3-6-1"]
    assert profile["youth_age_max"] == 26
    assert profile["uses_academy_players"] is True
    assert profile["transfer_preference"] == "youth-first"
    assert profile["youth_development"] == 18
    assert "academy_promotion_bias" in profile["catalog_traits"]
