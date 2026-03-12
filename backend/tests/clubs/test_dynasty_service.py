from __future__ import annotations

from backend.app.common.enums.dynasty_milestone_type import DynastyMilestoneType
from backend.app.schemas.club_requests import ClubCreateRequest
from backend.app.services.club_branding_service import ClubBrandingService
from backend.app.services.club_dynasty_service import ClubDynastyService


def _create_club(session) -> str:
    club = ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Dynasty FC",
                "short_name": "DFC",
                "slug": "dynasty-fc",
                "primary_color": "#330000",
                "secondary_color": "#eeeeee",
                "accent_color": "#ffcc00",
                "visibility": "public",
            }
        ),
    )
    return club.id


def test_dynasty_service_unlocks_long_horizon_milestones(session) -> None:
    club_id = _create_club(session)
    service = ClubDynastyService(session)

    for season in range(1, 6):
        service.record_season_outcome(
            club_id=club_id,
            season_label=f"Season {season}",
            participated=True,
            top_finish=season <= 3,
            trophy_won=season in {2, 3},
            community_prestige_delta=30,
            loyalty_points_delta=20,
            creator_legacy_delta=25,
        )

    progress, milestones = service.get_dynasty(club_id)
    unlocked = {item.milestone_type for item in milestones if item.is_unlocked}

    assert progress.seasons_completed == 5
    assert progress.participation_streak == 5
    assert progress.dynasty_score > 0
    assert progress.dynasty_title in {"Rising Legacy", "Established Dynasty", "Elite Dynasty", "Legendary Legacy"}
    assert DynastyMilestoneType.SEASONS_COMPLETED in unlocked
    assert DynastyMilestoneType.TOP_FINISH_STREAK in unlocked
    assert DynastyMilestoneType.PARTICIPATION_STREAK in unlocked
    assert DynastyMilestoneType.COMMUNITY_PRESTIGE in unlocked
    assert DynastyMilestoneType.CLUB_LOYALTY in unlocked
    assert DynastyMilestoneType.CREATOR_LEGACY in unlocked
