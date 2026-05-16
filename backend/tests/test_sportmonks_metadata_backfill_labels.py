from __future__ import annotations

import pytest

from backend.scripts.backfill_sportmonks_player_metadata import (
    _display_competition_name,
    _parse_api_target_fields,
    _parse_priority_leagues,
    _priority_league_match_labels,
)


def test_display_competition_name_disambiguates_same_named_leagues() -> None:
    assert _display_competition_name("Premier League", "Egypt") == "Egypt Premier League"
    assert _display_competition_name("Premier League", "England") == "Premier League"
    assert _display_competition_name("Pro League", "Saudi Arabia") == "Saudi Pro League"
    assert _display_competition_name("Super League", "Switzerland") == "Swiss Super League"


def test_display_competition_name_keeps_specific_names() -> None:
    assert _display_competition_name("Eredivisie", "Netherlands") == "Eredivisie"
    assert _display_competition_name("La Liga", "Spain") == "La Liga"


def test_parse_api_target_fields_expands_metadata_and_photo_aliases() -> None:
    assert _parse_api_target_fields("metadata, photo, image") == (
        "country",
        "club",
        "competition",
        "date_of_birth",
        "photo",
    )
    assert _parse_api_target_fields("nationality;team;league;dob") == (
        "country",
        "club",
        "competition",
        "date_of_birth",
    )


def test_parse_api_target_fields_rejects_unknown_targets() -> None:
    with pytest.raises(Exception):
        _parse_api_target_fields("market_value")


def test_parse_priority_leagues_expands_requested_first_divisions() -> None:
    assert _parse_priority_leagues(
        "english premier league, la liga, italian first division, "
        "french first division, german first division, turkish first division"
    ) == (
        "Premier League",
        "La Liga",
        "Italian Serie A",
        "French Ligue 1",
        "Bundesliga",
        "Super Lig",
    )


def test_priority_league_match_labels_include_provider_variants() -> None:
    assert _priority_league_match_labels(("French Ligue 1", "Super Lig")) == (
        "French Ligue 1",
        "Ligue 1",
        "Super Lig",
        "Süper Lig",
        "Turkish Super Lig",
    )
