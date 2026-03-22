from __future__ import annotations

from datetime import UTC, datetime

from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService
from app.schemas.real_player_ingestion import RealPlayerSeedInput


def test_normalization_service_builds_stable_identity_keys_and_cleans_fields() -> None:
    service = RealPlayerNormalizationService()
    payload = RealPlayerSeedInput.model_validate(
        {
            "source_name": "provider-a",
            "source_player_key": "kessie-001",
            "canonical_name": "Franck Kessie",
            "display_name": "Franck Kessie",
            "known_aliases": ["F. Kessie", "Franck Kessie"],
            "nationality": "Cote d'Ivoire",
            "birth_year": 1996,
            "age": 29,
            "dominant_foot": "Left-footed",
            "primary_position": "CM",
            "secondary_positions": ["Attacking Midfielder", "CM", "attacking midfielder"],
            "height_cm": 183,
            "current_real_world_club": "Al Ahli",
            "current_real_world_club_key": "club-123",
            "current_real_world_league": "Saudi Pro League",
            "current_real_world_league_key": "spl-1",
            "competition_level": "top_flight",
        }
    )

    normalized = service.normalize(payload, as_of=datetime(2026, 3, 22, tzinfo=UTC))

    assert normalized.display_name == "Franck Kessie"
    assert normalized.nationality == "Ivory Coast"
    assert normalized.birth_year == 1996
    assert normalized.age_years == 29
    assert normalized.dominant_foot == "left"
    assert normalized.primary_position == "Central Midfielder"
    assert normalized.secondary_positions == ("Attacking Midfielder",)
    assert normalized.identity.normalized_full_name == "franck kessie"
    assert normalized.identity.name_token_signature == "franck|kessie"
    assert normalized.identity.club_reference_key == "al-ahli"
    assert normalized.identity.league_reference_key == "saudi-pro-league"
    assert normalized.identity.exact_identity_key is None
    assert normalized.identity.name_birthyear_club_key == "franck|kessie|1996|club:al-ahli"
    assert normalized.identity.name_birthyear_nationality_key == "franck|kessie|1996|nat:ivory coast"
