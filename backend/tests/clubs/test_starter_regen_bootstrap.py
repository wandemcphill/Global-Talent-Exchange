from __future__ import annotations

from sqlalchemy import select

from backend.app.ingestion.models import Player
from backend.app.models.player_cards import PlayerCard, PlayerCardHolding
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.regen import RegenGenerationEvent, RegenOriginMetadata, RegenProfile
from backend.app.schemas.club_requests import ClubCreateRequest
from backend.app.services.club_branding_service import ClubBrandingService


def test_create_club_bootstraps_two_starter_regens(session) -> None:
    club = ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Harbor FC",
                "short_name": "HFC",
                "slug": "harbor-fc",
                "primary_color": "#114477",
                "secondary_color": "#ffffff",
                "accent_color": "#ff9900",
                "country_code": "NG",
                "region_name": "Lagos",
                "city_name": "Lagos",
                "visibility": "public",
            }
        ),
    )

    regen_profiles = session.scalars(
        select(RegenProfile).where(RegenProfile.generated_for_club_id == club.id).order_by(RegenProfile.regen_id)
    ).all()
    players = session.scalars(select(Player).where(Player.current_club_profile_id == club.id)).all()
    cards = session.scalars(
        select(PlayerCard).join(RegenProfile, RegenProfile.linked_unique_card_id == PlayerCard.id).where(
            RegenProfile.generated_for_club_id == club.id
        )
    ).all()
    holdings = session.scalars(
        select(PlayerCardHolding).join(PlayerCard, PlayerCard.id == PlayerCardHolding.player_card_id).where(
            PlayerCardHolding.owner_user_id == "user-owner"
        )
    ).all()
    origins = session.scalars(
        select(RegenOriginMetadata)
        .join(RegenProfile, RegenProfile.id == RegenOriginMetadata.regen_profile_id)
        .where(RegenProfile.generated_for_club_id == club.id)
    ).all()
    contracts = session.scalars(select(PlayerContract).where(PlayerContract.club_id == club.id)).all()
    careers = session.scalars(select(PlayerCareerEntry).where(PlayerCareerEntry.club_id == club.id)).all()
    events = session.scalars(select(RegenGenerationEvent).where(RegenGenerationEvent.club_id == club.id)).all()

    assert len(regen_profiles) == 2
    assert len(players) == 2
    assert len(cards) == 2
    assert len(holdings) == 2
    assert len(origins) == 2
    assert len(contracts) == 2
    assert len(careers) == 2
    assert len(events) == 2
    assert all(profile.generation_source == "new_club" for profile in regen_profiles)
    assert all(profile.birth_city == "Lagos" for profile in regen_profiles)
    assert len({profile.linked_unique_card_id for profile in regen_profiles}) == 2
    assert all(origin.ethnolinguistic_profile == "yoruba" for origin in origins)
    assert all("decision_traits" in (profile.metadata_json or {}) for profile in regen_profiles)
    assert all(
        {
            "ambition",
            "loyalty",
            "professionalism",
            "greed",
            "patience",
            "hometown_affinity",
            "trophy_hunger",
            "media_appetite",
            "temperament",
            "adaptability",
        }.issubset(set((profile.metadata_json or {}).get("decision_traits", {}).keys()))
        for profile in regen_profiles
    )
