from app.owner_console.engine import apply_staff_influence
from app.owner_console.service import onboarding_contract_charge_fan, onboarding_contract_years


def test_contract_charge_is_the_season_salary_times_the_chosen_years() -> None:
    assert onboarding_contract_years(0) == 1
    assert onboarding_contract_years(5) == 5
    assert onboarding_contract_years(9) == 5
    assert onboarding_contract_charge_fan(1000, 1) == 350
    assert onboarding_contract_charge_fan(1000, 3) == 1050


def test_a_hired_rating_becomes_the_role_skill() -> None:
    hoyd = apply_staff_influence(
        {"name": "Rinat Akhmetov", "rating": 98, "is_appointed": True},
        "head_of_youth_development",
    )
    assert hoyd["youth_development"] == 20

    manager = apply_staff_influence(
        {"name": "Tunde Mc'Phill", "rating": 76, "is_appointed": True},
        "first_team_manager",
    )
    assert manager["tactical_flexibility"] == 15
    assert manager["youth_development"] == 13

    general = apply_staff_influence(
        {"name": "Mats Kofi Silva", "rating": 91, "is_appointed": True},
        "general_manager",
    )
    assert general["negotiation"] == 18
    assert general["commercial_acumen"] == 18


def test_academy_names_stay_inside_one_culture() -> None:
    import random

    from app.services.regen_culture_name_pools import C, coherent_person_name

    rng = random.Random(7)
    for _ in range(40):
        full, culture = coherent_person_name(rng, "NG")
        given, surname = full.split(" ", 1)
        given_names, surnames = C[culture]
        assert given in given_names
        assert surname in surnames
        assert culture in {"yoruba", "igbo", "hausa"}


def test_manager_tactics_use_the_same_bonus_as_the_match() -> None:
    from app.owner_console.engine import manager_tactics

    tactics = manager_tactics({"name": "Tunde Mc'Phill", "rating": 76, "manager_id": "tunde"})
    assert tactics["formation"] == "4-2-3-1"
    assert tactics["tactical_flexibility"] == 15
    assert tactics["tactical_match_bonus"] == 6.0


def test_a_staff_skill_is_scaled_onto_the_personality_range() -> None:
    from app.owner_console.autonomous_staff_engine import derive_manager_personality

    profile = derive_manager_personality({"name": "Tunde Mc'Phill", "tactical_flexibility": 15})
    assert profile["tactical_flexibility"] == 75


def test_a_default_seat_does_not_invent_influence() -> None:
    vacant = apply_staff_influence(
        {"name": "", "use_default": True, "is_vacant": True},
        "head_of_youth_development",
    )
    assert "youth_development" not in vacant


def test_player_mood_profile_drives_contract_decisions_and_match_performance() -> None:
    from app.owner_console.engine import player_mood_profile, simulate_match

    thriving = player_mood_profile(82, rating=74, potential=90, age=15, minutes=450)
    assert thriving["mood_state"] == "Thriving"
    assert thriving["contract_willing"] is True
    assert thriving["contract_cost_fan_coin"] == 1000
    assert thriving["performance_shift"] > 0
    assert thriving["effective_match_rating"] > 74

    content = player_mood_profile(65, rating=72, potential=85, age=17, minutes=180)
    assert content["mood_state"] == "Content"
    assert content["contract_willing"] is True
    assert content["contract_cost_fan_coin"] == 1000

    restless = player_mood_profile(48, rating=72, potential=86, age=18, minutes=60)
    assert restless["mood_state"] == "Restless"
    assert restless["contract_willing"] is True
    assert restless["contract_cost_fan_coin"] == 1250
    assert restless["performance_shift"] < 0

    unsettled = player_mood_profile(32, rating=74, potential=90, age=18, minutes=0)
    assert unsettled["mood_state"] == "Unsettled"
    assert unsettled["contract_willing"] is False
    assert unsettled["performance_shift"] < 0
    assert unsettled["effective_match_rating"] < 74

    unsettled_with_pathway = player_mood_profile(
        32,
        rating=74,
        potential=90,
        age=18,
        minutes=0,
        promised_minutes=True,
    )
    assert unsettled_with_pathway["contract_willing"] is True
    assert unsettled_with_pathway["contract_cost_fan_coin"] == 1250

    match_high = simulate_match(
        "mood-match-check",
        {
            "club_id": "club-a",
            "name": "Ekiti FC",
            "strength": 76.0,
            "formation": "4-2-3-1",
            "avg_morale": 85.0,
            "xi_players": [
                {
                    "id": f"p-{idx}",
                    "name": f"Player {idx}",
                    "position": "GK" if idx == 0 else "ST",
                    "rating": 75,
                    "morale": 85,
                }
                for idx in range(11)
            ],
        },
        {
            "club_id": "club-b",
            "name": "Rival FC",
            "strength": 72.0,
            "formation": "4-3-3",
            "avg_morale": 42.0,
            "xi_players": [
                {
                    "id": f"r-{idx}",
                    "name": f"Rival {idx}",
                    "position": "GK" if idx == 0 else "ST",
                    "rating": 72,
                    "morale": 42,
                }
                for idx in range(11)
            ],
        },
    )
    assert "home_goals" in match_high
    assert "away_goals" in match_high


def test_folarin_mcphill_canonical_gsi_and_front_three_positions() -> None:
    from app.players.gsi_service import CANONICAL_GSI_OVERRIDES
    from app.players.position_roles import display_codes, resolve_positions

    assert CANONICAL_GSI_OVERRIDES["folarin mc'phill"] == (74, 90)
    assert CANONICAL_GSI_OVERRIDES["folarin mcphill"] == (74, 90)

    primary, secondaries, reason = resolve_positions(
        name="Folarin Mc'Phill",
        position="ST",
    )
    assert primary == "ST"
    assert secondaries == ["LW", "RW"]
    assert reason == "named"
    assert display_codes(primary, secondaries) == "ST / LW / RW"
