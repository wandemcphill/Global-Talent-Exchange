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
