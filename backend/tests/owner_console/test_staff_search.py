from app.owner_console.living_staff_market import (
    fold_staff_text,
    philosophy_fit,
    staff_search_blob,
    staff_search_matches,
)


def test_staff_search_matches_surname_accents_and_apostrophes() -> None:
    ferguson = staff_search_blob("Sir Alex Ferguson", "Scotland", "4-4-2", "first_team_manager")
    chelle = staff_search_blob("Éric Chelle", "Mali", "4-2-3-1")
    mcphill = staff_search_blob("Tunde Mc'Phill", "Nigeria", "3-4-3")

    assert staff_search_matches(ferguson, "ferguson")
    assert staff_search_matches(ferguson, "alex ferguson")
    assert staff_search_matches(ferguson, "scotland")
    assert staff_search_matches(chelle, "eric chelle")
    assert staff_search_matches(mcphill, "mcphill")
    assert staff_search_matches(mcphill, "mc phill")
    assert not staff_search_matches(ferguson, "arteta")
    assert fold_staff_text("Jürgen Klopp") == "jurgen klopp"


def test_philosophy_fit_matches_a_youth_coach_and_skips_a_defensive_one() -> None:
    assert (
        philosophy_fit("youth_development", "Technical Possession", "develops young players")
        == "Fits youth development"
    )
    assert philosophy_fit("superstar", "Compact Block", "defensive") is None
