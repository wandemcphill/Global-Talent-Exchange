"""A new club is in Foundation. The name on the card is the stored division."""

from app.owner_console.living_institution import division_name


def test_division_names_follow_the_pyramid():
    assert division_name(None) == "Foundation"
    assert division_name("foundation") == "Foundation"
    assert division_name("division_3") == "3rd division"
    assert division_name("division_2") == "2nd division"
    assert division_name("division_1") == "1st division"
