from collections import Counter

from app.owner_console.regen_staff_catalog import (
    FEMALE_ROLES,
    REGEN_STAFF_COUNT,
    build_regen_staff_catalog,
    portrait_filename,
)


def test_regen_staff_pool_is_thousands_and_not_all_elite():
    staff = build_regen_staff_catalog()
    assert len(staff) == REGEN_STAFF_COUNT == 17000
    assert len({person["id"] for person in staff}) == 17000

    ratings = [person["rating"] for person in staff]
    assert min(ratings) >= 60
    assert max(ratings) <= 91
    assert sum(1 for rating in ratings if rating <= 70) > len(staff) * 0.45
    assert sum(1 for rating in ratings if rating >= 85) < len(staff) * 0.08

    roles = Counter(person["role"] for person in staff)
    assert roles["general_manager"] == 3100
    assert roles["first_team_manager"] == 3300
    assert roles["medical_director"] == 3100
    assert roles["head_of_youth_development"] == 4550
    assert roles["chief_scout"] == 2950


def test_few_women_include_heads_of_youth_development():
    staff = build_regen_staff_catalog()
    women = [person for person in staff if person["gender"] == "female"]
    assert {person["role"] for person in women} <= FEMALE_ROLES
    assert "head_of_youth_development" in {person["role"] for person in women}
    for role in FEMALE_ROLES:
        role_women = [person for person in women if person["role"] == role]
        role_total = sum(1 for person in staff if person["role"] == role)
        assert 0 < len(role_women) < role_total * 0.12


def test_every_regen_has_a_mature_portrait_from_the_face_bank():
    staff = build_regen_staff_catalog()
    for index, person in enumerate(staff):
        expected = portrait_filename(person["face_group"], person["gender"], index)
        assert person["portrait_url"] == f"/staff-portraits/{expected}"
        assert person["origin"] == "regen_staff"
        assert 34 <= person["age"] <= 56
    first_page = [person["portrait_url"] for person in staff[:40]]
    assert len(set(first_page)) == 40
