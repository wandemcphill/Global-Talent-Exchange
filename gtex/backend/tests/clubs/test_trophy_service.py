from __future__ import annotations

from app.common.enums.trophy_type import TrophyType
from app.schemas.club_requests import ClubCreateRequest
from app.services.club_branding_service import ClubBrandingService
from app.services.club_dynasty_service import ClubDynastyService
from app.services.club_reputation_service import ClubReputationService
from app.services.club_trophy_service import ClubTrophyService


def _create_club(session) -> str:
    club = ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Cabinet FC",
                "short_name": "CFC",
                "slug": "cabinet-fc",
                "primary_color": "#002244",
                "secondary_color": "#ddeeff",
                "accent_color": "#ccaa33",
                "visibility": "public",
            }
        ),
    )
    return club.id


def test_awarding_trophies_updates_cabinet_reputation_and_dynasty(session) -> None:
    club_id = _create_club(session)
    service = ClubTrophyService(session)

    service.award_trophy(
        club_id=club_id,
        trophy_type=TrophyType.LEAGUE_TITLE,
        trophy_name="League Crown",
        competition_source="senior_league",
        season_label="Season 1",
        featured=True,
    )
    service.award_trophy(
        club_id=club_id,
        trophy_type=TrophyType.FAIR_PLAY_AWARD,
        trophy_name="Fair Play Star",
        competition_source="senior_league",
        season_label="Season 1",
    )

    cabinet, trophies = service.get_trophy_cabinet(club_id)
    reputation = ClubReputationService(session).get_reputation(club_id)
    dynasty, _ = ClubDynastyService(session).get_dynasty(club_id)

    assert cabinet.total_trophies == 2
    assert len(trophies) == 2
    assert trophies[0].trophy_name == "Fair Play Star"
    assert reputation.current_score == 140 + 70
    assert dynasty.dynasty_score > 0
    assert dynasty.creator_legacy_points > 0
