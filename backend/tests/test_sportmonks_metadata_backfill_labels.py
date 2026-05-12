from __future__ import annotations

from backend.scripts.backfill_sportmonks_player_metadata import _display_competition_name


def test_display_competition_name_disambiguates_same_named_leagues() -> None:
    assert _display_competition_name("Premier League", "Egypt") == "Egypt Premier League"
    assert _display_competition_name("Premier League", "England") == "Premier League"
    assert _display_competition_name("Pro League", "Saudi Arabia") == "Saudi Pro League"
    assert _display_competition_name("Super League", "Switzerland") == "Swiss Super League"


def test_display_competition_name_keeps_specific_names() -> None:
    assert _display_competition_name("Eredivisie", "Netherlands") == "Eredivisie"
    assert _display_competition_name("La Liga", "Spain") == "La Liga"
