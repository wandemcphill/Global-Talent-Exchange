from app.club_growth.staff_role_policy import (
    ROLE_FIRST_TEAM_MANAGER,
    ROLE_GENERAL_MANAGER,
    ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
    ROLE_MEDICAL,
    ROLE_YOUTH_COACH,
    evaluate_staff_role,
    normalise_staff_role,
)


def test_manager_is_a_club_appointment_for_coaches_and_retired_regens() -> None:
    assert evaluate_staff_role(
        role_key="manager",
        staff_type="coach",
    ).allowed
    assert evaluate_staff_role(
        role_key=ROLE_FIRST_TEAM_MANAGER,
        staff_type="",
        retired_regen=True,
    ).allowed


def test_head_coach_alias_maps_to_manager_appointment() -> None:
    assert normalise_staff_role("Head Coach") == ROLE_FIRST_TEAM_MANAGER


def test_general_manager_is_distinct_and_requires_operations_or_transfer_capability() -> None:
    assert normalise_staff_role("GM") == ROLE_GENERAL_MANAGER
    assert normalise_staff_role("General Manager") == ROLE_GENERAL_MANAGER
    assert normalise_staff_role("manager") == ROLE_FIRST_TEAM_MANAGER
    assert ROLE_GENERAL_MANAGER != ROLE_FIRST_TEAM_MANAGER

    assert evaluate_staff_role(
        role_key=ROLE_GENERAL_MANAGER,
        staff_type="general_manager",
    ).allowed
    assert evaluate_staff_role(
        role_key=ROLE_GENERAL_MANAGER,
        staff_type="gm",
    ).allowed
    assert evaluate_staff_role(
        role_key="gm",
        staff_type="manager",
        specialisations={"financial_acumen", "negotiation"},
    ).allowed
    decision = evaluate_staff_role(
        role_key="general_manager",
        staff_type="manager",
        specialisations={"tactics", "morale"},
    )
    assert not decision.allowed
    assert decision.reason == "general_manager_requires_operations_or_transfer_capability"


def test_head_of_youth_development_is_distinct_and_requires_academy_capability() -> None:
    assert normalise_staff_role("HOYD") == ROLE_HEAD_OF_YOUTH_DEVELOPMENT
    assert normalise_staff_role("Head of Youth Development") == ROLE_HEAD_OF_YOUTH_DEVELOPMENT
    assert evaluate_staff_role(
        role_key=ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        staff_type="academy_director",
    ).allowed
    assert evaluate_staff_role(
        role_key=ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        staff_type="hoyd",
    ).allowed
    assert evaluate_staff_role(
        role_key="hoyd",
        staff_type="coach",
        specialisations={"talent_identification", "regen_development"},
    ).allowed
    decision = evaluate_staff_role(
        role_key=ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        staff_type="coach",
        specialisations={"fitness", "morale"},
    )
    assert not decision.allowed
    assert decision.reason == "head_of_youth_development_requires_academy_capability"


def test_medical_role_requires_explicit_qualification() -> None:
    decision = evaluate_staff_role(
        role_key=ROLE_MEDICAL,
        staff_type="coach",
        retired_regen=True,
    )
    assert not decision.allowed
    assert decision.reason == "medical_role_requires_explicit_qualification"


def test_youth_coach_requires_coaching_capability() -> None:
    assert evaluate_staff_role(
        role_key=ROLE_YOUTH_COACH,
        staff_type="coach",
    ).allowed
    assert not evaluate_staff_role(
        role_key=ROLE_YOUTH_COACH,
        staff_type="scout",
    ).allowed


def test_personal_manager_is_non_salary_profile_identity() -> None:
    decision = evaluate_staff_role(
        role_key=ROLE_FIRST_TEAM_MANAGER,
        staff_type="manager",
        personal_manager=True,
    )
    assert decision.allowed
    assert not decision.consumes_salary
