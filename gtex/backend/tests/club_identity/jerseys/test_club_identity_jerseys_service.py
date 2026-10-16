from __future__ import annotations

import pytest

from app.club_identity.jerseys.service import ClubIdentityService
from app.club_identity.models.jersey_models import BadgeShape, IconFamily, JerseyType


def test_jersey_creation_generates_full_default_identity(identity_service: ClubIdentityService) -> None:
    profile = identity_service.get_identity("lagos-lions")

    assert profile.club_name == "Lagos Lions"
    assert profile.short_club_code == "LL"
    assert profile.jersey_set.home.jersey_type == JerseyType.HOME
    assert profile.jersey_set.away.jersey_type == JerseyType.AWAY
    assert profile.jersey_set.third.jersey_type == JerseyType.THIRD
    assert profile.jersey_set.goalkeeper.jersey_type == JerseyType.GOALKEEPER


def test_color_validation_rejects_unreadable_home_kit(identity_service: ClubIdentityService) -> None:
    with pytest.raises(ValueError, match="primary and secondary colors are too similar"):
        identity_service.update_jerseys(
            "lagos-lions",
            {
                "home": {
                    "primary_color": "#112233",
                    "secondary_color": "#132435",
                    "accent_color": "#142536",
                }
            },
        )


def test_fallback_generation_preserves_missing_variants(identity_service: ClubIdentityService) -> None:
    jerseys = identity_service.update_jerseys(
        "cape-town-cosmos",
        {
            "home": {
                "pattern_type": "stripes",
                "front_text": "CTC",
            },
            "away": {
                "pattern_type": "hoops",
                "front_text": "CTC",
            },
        },
    )

    assert jerseys.third.front_text.endswith("ALT")
    assert jerseys.goalkeeper.front_text.endswith("GK")


def test_home_and_away_clash_is_rejected(identity_service: ClubIdentityService) -> None:
    with pytest.raises(ValueError, match="Home and away jerseys"):
        identity_service.update_jerseys(
            "accra-arrows",
            {
                "home": {
                    "primary_color": "#FFFFFF",
                    "secondary_color": "#001F3F",
                    "accent_color": "#FF4136",
                },
                "away": {
                    "primary_color": "#FFFFFF",
                    "secondary_color": "#001F3F",
                    "accent_color": "#FF4136",
                    "pattern_type": "solid",
                },
            },
        )


def test_badge_generation_metadata_is_deterministic(identity_service: ClubIdentityService) -> None:
    badge = identity_service.get_badge("nairobi-night")
    repeated_badge = identity_service.get_badge("nairobi-night")

    assert badge == repeated_badge
    assert badge.shape in {BadgeShape.SHIELD, BadgeShape.ROUND, BadgeShape.DIAMOND, BadgeShape.PENNANT}
    assert badge.icon_family in {
        IconFamily.STAR,
        IconFamily.LION,
        IconFamily.EAGLE,
        IconFamily.CROWN,
        IconFamily.OAK,
        IconFamily.BOLT,
    }
    assert badge.initials == "NN"
