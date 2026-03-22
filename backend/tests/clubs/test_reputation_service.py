from __future__ import annotations

from app.schemas.club_requests import ClubCreateRequest
from app.services.club_branding_service import ClubBrandingService
from app.services.club_reputation_event_service import ClubReputationEventService
from app.services.club_reputation_service import ClubReputationService


def _create_club(session) -> str:
    club = ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Heritage FC",
                "short_name": "HFC",
                "slug": "heritage-fc",
                "primary_color": "#111111",
                "secondary_color": "#eeeeee",
                "accent_color": "#cc9900",
                "visibility": "public",
            }
        ),
    )
    return club.id


def test_reputation_service_accumulates_deterministic_scores_and_maps_to_established_tier(session) -> None:
    club_id = _create_club(session)
    event_service = ClubReputationEventService(session)
    event_service.record_achievement(
        club_id=club_id,
        achievement_key="competition_win",
        source="league_results",
        quantity=4,
        auto_commit=False,
    )
    event_service.record_achievement(
        club_id=club_id,
        achievement_key="community_growth",
        source="share_codes",
        quantity=10,
        auto_commit=False,
    )
    session.commit()

    reputation = ClubReputationService(session).get_reputation(club_id)

    assert reputation.current_score == (4 * 90) + (10 * 30)
    assert reputation.tier.value == "established"
    assert reputation.breakdown.competition_wins == 360
    assert reputation.breakdown.community_growth == 300


def test_reputation_service_rolls_up_season_snapshot(session) -> None:
    club_id = _create_club(session)
    ClubReputationEventService(session).record_achievement(
        club_id=club_id,
        achievement_key="competition_participation",
        source="league_entry",
        season=1,
        quantity=2,
        auto_commit=False,
    )
    ClubReputationEventService(session).record_achievement(
        club_id=club_id,
        achievement_key="fair_play",
        source="discipline",
        season=1,
        quantity=1,
        auto_commit=False,
    )
    session.commit()

    snapshot = ClubReputationService(session).rollup_snapshot(
        club_id=club_id,
        season=1,
        badges=["fair-play"],
        milestones=["season-one"],
    )
    reputation = ClubReputationService(session).get_reputation(club_id)

    assert snapshot.season_delta == (2 * 12) + 20
    assert reputation.last_snapshot is not None
    assert reputation.last_snapshot.badges == ["fair-play"]
    assert reputation.last_snapshot.milestones == ["season-one"]
