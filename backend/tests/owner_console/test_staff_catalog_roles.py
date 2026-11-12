from app.owner_console.staff_catalog_roles import assign_executive_staff_role


def test_director_of_football_job_becomes_general_manager():
    role, rating = assign_executive_staff_role(
        job="Director of Football",
        head_coach=90,
        general_manager=70,
        technical_director=66,
        youth=80,
        scout=40,
        physio=30,
    )
    assert role == "general_manager"
    assert rating == 70


def test_fm23_general_manager_and_technical_director_qualify():
    gm_role, gm_rating = assign_executive_staff_role(
        job="General Manager",
        head_coach=88,
        general_manager=78,
        technical_director=70,
        youth=84,
        scout=40,
        physio=30,
    )
    assert (gm_role, gm_rating) == ("general_manager", 78)

    td_role, td_rating = assign_executive_staff_role(
        job="Technical Director",
        head_coach=86,
        general_manager=62,
        technical_director=84,
        youth=70,
        scout=40,
        physio=30,
    )
    assert (td_role, td_rating) == ("general_manager", 84)


def test_board_director_stays_on_highest_football_rating():
    role, rating = assign_executive_staff_role(
        job="Managing Director",
        head_coach=94,
        general_manager=77,
        technical_director=70,
        youth=60,
        scout=40,
        physio=30,
    )
    assert role == "first_team_manager"
    assert rating == 94


def test_weak_general_manager_can_still_enter_as_a_coach():
    assigned = assign_executive_staff_role(
        job="General Manager",
        head_coach=72,
        general_manager=50,
        technical_director=40,
        youth=55,
        scout=40,
        physio=30,
    )
    assert assigned == ("first_team_manager", 72)
