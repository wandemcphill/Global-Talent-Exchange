from __future__ import annotations

from app.ingestion.normalizers import (
    normalize_club_name,
    normalize_competition_payload,
    normalize_player_payload,
    normalize_position,
)


def test_competition_normalizer_applies_aliases_and_slug_cleanup() -> None:
    record = normalize_competition_payload(
        "mock",
        {
            "id": "UCL",
            "name": " UEFA Club Championship ",
            "type": "CUP",
            "area": {"id": "EUR", "name": "Europe"},
            "currentSeason": {"id": "UCL-2025"},
        },
    )

    assert record.name == "UEFA Champions League"
    assert record.slug == "uefa-champions-league"
    assert record.current_season_external_id == "UCL-2025"


def test_player_normalizer_handles_position_measurements_and_country_cleanup() -> None:
    player = normalize_player_payload(
        "mock",
        {
            "id": "p-1",
            "name": "  Jane   Winger ",
            "position": "Right Winger",
            "nationality": " usa ",
            "height": "172 cm",
            "weight": "63 kg",
        },
        club_external_id="club-1",
    )

    assert player.full_name == "Jane Winger"
    assert player.normalized_position == "WINGER"
    assert player.country_name == "United States"
    assert player.height_cm == 172
    assert player.weight_kg == 63


def test_simple_alias_helpers_cover_common_club_and_position_variants() -> None:
    assert normalize_club_name("man united") == "Manchester United"
    assert normalize_position("goalkeeper") == "GK"
