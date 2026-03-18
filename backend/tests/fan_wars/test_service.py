from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.fan_wars.schemas import CreatorCountryAssignmentRequest, FanWarPointRecordRequest, NationsCupCreateRequest
from backend.app.fan_wars.service import FanWarError, FanWarService
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.fan_war import FanWarPoint, FanWarProfile
from backend.app.models.user import User


def _assign_country(service: FanWarService, *, creator_profile_id: str, country_code: str, country_name: str, actor: User) -> None:
    service.assign_creator_country(
        CreatorCountryAssignmentRequest(
            creator_profile_id=creator_profile_id,
            represented_country_code=country_code,
            represented_country_name=country_name,
            eligible_country_codes=(country_code,),
        ),
        actor=actor,
    )


def test_fan_war_point_accumulation_records_multiple_fanbases(session: Session, admin_user: User, fan_user: User, creator_factory) -> None:
    creator = creator_factory("Speed", "speed", "NG")
    service = FanWarService(session)
    _assign_country(service, creator_profile_id=creator["creator_profile"].id, country_code="NG", country_name="Nigeria", actor=admin_user)

    payload = FanWarPointRecordRequest(
        actor_user_id=fan_user.id,
        source_type="watch_match",
        club_id=creator["club"].id,
        creator_profile_id=creator["creator_profile"].id,
        country_code="NG",
        country_name="Nigeria",
        engagement_units=3,
        dedupe_key="watch-1",
    )
    first = service.record_points(payload)
    session.commit()
    second = service.record_points(payload)

    assert len(first) == 3
    assert {item.id for item in first} == {item.id for item in second}
    assert all(item.weighted_points > 0 for item in first)
    assert session.scalar(select(func.count(FanWarPoint.id))) == 3
    assert {profile.profile_type for profile in session.scalars(select(FanWarProfile)).all()} == {"club", "country", "creator"}


def test_fanbase_rankings_split_global_club_and_country_boards(session: Session, admin_user: User, fan_user: User, creator_factory) -> None:
    first_creator = creator_factory("Speed", "speed", "NG")
    second_creator = creator_factory("Vision", "vision", "BR")
    service = FanWarService(session)
    _assign_country(service, creator_profile_id=first_creator["creator_profile"].id, country_code="NG", country_name="Nigeria", actor=admin_user)
    _assign_country(service, creator_profile_id=second_creator["creator_profile"].id, country_code="BR", country_name="Brazil", actor=admin_user)

    service.record_points(
        FanWarPointRecordRequest(
            actor_user_id=fan_user.id,
            source_type="watch_match",
            club_id=first_creator["club"].id,
            country_code="NG",
            country_name="Nigeria",
            engagement_units=6,
            awarded_at=datetime(2026, 3, 17, tzinfo=UTC),
            dedupe_key="rank-1",
        )
    )
    service.record_points(
        FanWarPointRecordRequest(
            actor_user_id=fan_user.id,
            source_type="creator_support",
            creator_profile_id=first_creator["creator_profile"].id,
            engagement_units=3,
            awarded_at=datetime(2026, 3, 17, tzinfo=UTC),
            dedupe_key="rank-2",
        )
    )
    service.record_points(
        FanWarPointRecordRequest(
            actor_user_id=fan_user.id,
            source_type="watch_match",
            club_id=second_creator["club"].id,
            country_code="BR",
            country_name="Brazil",
            engagement_units=2,
            awarded_at=datetime(2026, 3, 17, tzinfo=UTC),
            dedupe_key="rank-3",
        )
    )

    session.commit()
    service.refresh_rankings(period_type="weekly", reference_date=date(2026, 3, 17))
    global_board = service.get_leaderboard(board_type="global", period_type="weekly", reference_date=date(2026, 3, 17), limit=10)
    club_board = service.get_leaderboard(board_type="club", period_type="weekly", reference_date=date(2026, 3, 17), limit=10)
    country_board = service.get_leaderboard(board_type="country", period_type="weekly", reference_date=date(2026, 3, 17), limit=10)

    assert global_board.entries[0].display_name in {"Nigeria", "Speed FC", "Speed"}
    assert {entry.profile_type for entry in club_board.entries} == {"club"}
    assert {entry.profile_type for entry in country_board.entries} == {"country"}
    assert club_board.entries[0].display_name == "Speed FC"
    assert country_board.entries[0].display_name == "Nigeria"


def test_creator_country_assignment_blocks_out_of_set_without_override(session: Session, admin_user: User, creator_factory) -> None:
    creator = creator_factory("Builder", "builder", "NG")
    service = FanWarService(session)

    with pytest.raises(FanWarError, match="eligible"):
        service.assign_creator_country(
            CreatorCountryAssignmentRequest(
                creator_profile_id=creator["creator_profile"].id,
                represented_country_code="BR",
                represented_country_name="Brazil",
                eligible_country_codes=("NG",),
            ),
            actor=admin_user,
        )

    assignment = service.assign_creator_country(
        CreatorCountryAssignmentRequest(
            creator_profile_id=creator["creator_profile"].id,
            represented_country_code="BR",
            represented_country_name="Brazil",
            eligible_country_codes=("NG",),
            allow_admin_override=True,
        ),
        actor=admin_user,
    )

    assert assignment.represented_country_code == "BR"
    assert "BR" in assignment.eligible_country_codes


def test_nations_cup_progression_advances_groups_and_crowns_champion(session: Session, admin_user: User, creator_factory) -> None:
    service = FanWarService(session)
    creators = [
        creator_factory("Speed", "speed", "NG"),
        creator_factory("Vision", "vision", "BR"),
        creator_factory("Nova", "nova", "GH"),
        creator_factory("Pulse", "pulse", "AR"),
        creator_factory("Orbit", "orbit", "US"),
        creator_factory("Blaze", "blaze", "MX"),
        creator_factory("Comet", "comet", "DE"),
        creator_factory("Aero", "aero", "FR"),
    ]
    for creator, code, name in zip(creators, ("NG", "BR", "GH", "AR", "US", "MX", "DE", "FR"), ("Nigeria", "Brazil", "Ghana", "Argentina", "United States", "Mexico", "Germany", "France"), strict=True):
        _assign_country(service, creator_profile_id=creator["creator_profile"].id, country_code=code, country_name=name, actor=admin_user)
    session.commit()

    overview = service.create_nations_cup(
        NationsCupCreateRequest(
            title="GTEX Nations Cup Test",
            season_label="2026",
            start_date=date(2026, 6, 1),
            group_count=2,
            group_size=4,
            group_advance_count=2,
            creator_profile_ids=tuple(creator["creator_profile"].id for creator in creators),
            created_by_user_id=admin_user.id,
        )
    )
    competition = session.get(Competition, overview.competition_id)
    assert competition is not None
    assert competition.stage == "group"
    participants = session.scalars(select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition.id).order_by(CompetitionParticipant.group_key.asc(), CompetitionParticipant.seed.asc())).all()
    group_a = [participant for participant in participants if participant.group_key == "g01"]
    group_b = [participant for participant in participants if participant.group_key == "g02"]
    for index, participant in enumerate(group_a):
        participant.played = 3
        participant.wins = max(0, 3 - index)
        participant.draws = 0
        participant.losses = index
        participant.goals_for = 7 - index
        participant.goals_against = 2 + index
        participant.goal_diff = participant.goals_for - participant.goals_against
        participant.points = max(0, 9 - index * 3)
    for index, participant in enumerate(group_b):
        participant.played = 3
        participant.wins = max(0, 3 - index)
        participant.draws = 0
        participant.losses = index
        participant.goals_for = 8 - index
        participant.goals_against = 3 + index
        participant.goal_diff = participant.goals_for - participant.goals_against
        participant.points = max(0, 9 - index * 3)
    for match in session.scalars(select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id, CompetitionMatch.stage == "group")).all():
        match.status = "completed"
        match.winner_club_id = match.home_club_id
    session.commit()

    overview = service.advance_nations_cup(competition.id)
    assert overview.stage == "knockout"
    assert sum(1 for entry in overview.entries if entry.advanced_to_knockout) == 4

    for match in session.scalars(select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id, CompetitionMatch.stage == "knockout", CompetitionMatch.round_number == 1)).all():
        match.status = "completed"
        match.winner_club_id = match.home_club_id
    session.commit()
    overview = service.advance_nations_cup(competition.id)
    assert overview.stage == "knockout"

    final_match = session.scalar(select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id, CompetitionMatch.stage == "knockout", CompetitionMatch.round_number == 2))
    assert final_match is not None
    final_match.status = "completed"
    final_match.winner_club_id = final_match.home_club_id
    session.commit()

    overview = service.advance_nations_cup(competition.id)

    assert overview.status == CompetitionStatus.COMPLETED.value
    assert any(entry.status == "champion" for entry in overview.entries)


def test_fan_contribution_weighting_caps_large_spend(session: Session, admin_user: User, fan_user: User, creator_factory) -> None:
    creator = creator_factory("Builder", "builder", "NG")
    service = FanWarService(session)
    _assign_country(service, creator_profile_id=creator["creator_profile"].id, country_code="NG", country_name="Nigeria", actor=admin_user)

    moderate_gift = service.record_points(
        FanWarPointRecordRequest(
            actor_user_id=fan_user.id,
            source_type="gift",
            country_code="NG",
            country_name="Nigeria",
            spend_amount_minor=10_000,
            target_categories=("country",),
            dedupe_key="gift-moderate",
        )
    )[0]
    huge_gift = service.record_points(
        FanWarPointRecordRequest(
            actor_user_id=fan_user.id,
            source_type="gift",
            country_code="NG",
            country_name="Nigeria",
            spend_amount_minor=1_000_000,
            target_categories=("country",),
            dedupe_key="gift-huge",
        )
    )[0]
    heavy_watch = service.record_points(
        FanWarPointRecordRequest(
            actor_user_id=fan_user.id,
            source_type="watch_match",
            country_code="NG",
            country_name="Nigeria",
            target_categories=("country",),
            engagement_units=8,
            dedupe_key="watch-heavy",
        )
    )[0]

    assert huge_gift.weighted_points <= 36
    assert huge_gift.weighted_points - moderate_gift.weighted_points <= 5
    assert huge_gift.weighted_points <= heavy_watch.weighted_points
