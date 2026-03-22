from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.enums.match_status import MatchStatus
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.schemas.creator_league import CreatorLeagueSeasonCreateRequest, CreatorLeagueSeasonTierAssignmentRequest
from app.services.creator_league_service import CreatorLeagueService


def test_creator_league_bootstraps_default_three_divisions(session: Session) -> None:
    overview = CreatorLeagueService(session).get_overview()

    assert [tier.name for tier in overview.tiers] == ["Division 1", "Division 2", "Division 3"]
    assert [tier.club_count for tier in overview.tiers] == [20, 20, 20]
    assert [tier.promotion_spots for tier in overview.tiers] == [0, 3, 3]
    assert [tier.relegation_spots for tier in overview.tiers] == [3, 3, 0]
    assert [(rule.tier_name, rule.direction, rule.spots) for rule in overview.movement_rules] == [
        ("Division 1", "relegation", 3),
        ("Division 2", "promotion", 3),
        ("Division 2", "relegation", 3),
        ("Division 3", "promotion", 3),
    ]


def test_creator_league_generates_double_round_robin_fixtures(session: Session, seeded_clubs: list[ClubProfile]) -> None:
    service = CreatorLeagueService(session)
    overview = service.get_overview()
    assignments = tuple(
        CreatorLeagueSeasonTierAssignmentRequest(
            tier_id=tier.id,
            club_ids=tuple(club.id for club in seeded_clubs[start:start + 20]),
        )
        for tier, start in zip(overview.tiers, (0, 20, 40), strict=True)
    )

    season = service.create_season(
        CreatorLeagueSeasonCreateRequest(
            start_date=date(2026, 1, 4),
            assignments=assignments,
            activate=True,
            created_by_user_id="admin-user",
        )
    )
    top_tier = season.tiers[0]
    matches = session.scalars(select(CompetitionMatch).where(CompetitionMatch.competition_id == top_tier.competition_id)).all()

    assert season.status == "live"
    assert len(season.tiers) == 3
    assert top_tier.round_count == 38
    assert top_tier.fixture_count == 380
    assert len(matches) == 380
    assert {match.round_number for match in matches} == set(range(1, 39))

    pairings = defaultdict(set)
    club_match_counts = Counter()
    for match in matches:
        ordered_pair = tuple(sorted((match.home_club_id, match.away_club_id)))
        pairings[ordered_pair].add((match.home_club_id, match.away_club_id))
        club_match_counts[match.home_club_id] += 1
        club_match_counts[match.away_club_id] += 1
        assert match.home_club_id != match.away_club_id

    assert len(pairings) == 190
    assert all(len(pairs) == 2 for pairs in pairings.values())
    assert set(club_match_counts.values()) == {38}


def test_creator_league_standings_mark_promotion_and_relegation_zones(session: Session, seeded_clubs: list[ClubProfile]) -> None:
    service = CreatorLeagueService(session)
    overview = service.get_overview()
    season = service.create_season(
        CreatorLeagueSeasonCreateRequest(
            start_date=date(2026, 2, 1),
            assignments=tuple(
                CreatorLeagueSeasonTierAssignmentRequest(
                    tier_id=tier.id,
                    club_ids=tuple(club.id for club in seeded_clubs[start:start + 20]),
                )
                for tier, start in zip(overview.tiers, (0, 20, 40), strict=True)
            ),
            activate=True,
            created_by_user_id="admin-user",
        )
    )

    second_tier = season.tiers[1]
    participants = session.scalars(
        select(CompetitionParticipant)
        .where(CompetitionParticipant.competition_id == second_tier.competition_id)
        .order_by(CompetitionParticipant.seed.asc())
    ).all()
    for index, participant in enumerate(participants):
        participant.played = 38
        participant.wins = max(0, 20 - index)
        participant.draws = 0
        participant.losses = 38 - participant.wins
        participant.goals_for = 60 - index
        participant.goals_against = 20 + index
        participant.goal_diff = participant.goals_for - participant.goals_against
        participant.points = (20 - index) * 3
    session.commit()

    standings = service.get_standings(second_tier.id)

    assert [row.movement_zone for row in standings[:3]] == ["promotion", "promotion", "promotion"]
    assert standings[3].movement_zone == "safe"
    assert [row.movement_zone for row in standings[-3:]] == ["relegation", "relegation", "relegation"]


def test_creator_league_live_priority_places_creator_league_first(session: Session, seeded_clubs: list[ClubProfile]) -> None:
    service = CreatorLeagueService(session)
    overview = service.get_overview()
    season = service.create_season(
        CreatorLeagueSeasonCreateRequest(
            start_date=date(2026, 3, 1),
            assignments=tuple(
                CreatorLeagueSeasonTierAssignmentRequest(
                    tier_id=tier.id,
                    club_ids=tuple(club.id for club in seeded_clubs[start:start + 20]),
                )
                for tier, start in zip(overview.tiers, (0, 20, 40), strict=True)
            ),
            activate=True,
            created_by_user_id="admin-user",
        )
    )

    creator_match = session.scalars(
        select(CompetitionMatch).where(CompetitionMatch.competition_id == season.tiers[0].competition_id)
    ).first()
    assert creator_match is not None
    creator_match.status = MatchStatus.IN_PROGRESS.value

    regular_competition = Competition(
        id="regular-competition",
        host_user_id="admin-user",
        name="Regular League",
        description="Regular league",
        competition_type="league",
        source_type="standard",
        source_id="regular-source",
        format=CompetitionFormat.LEAGUE.value,
        visibility=CompetitionVisibility.PUBLIC.value,
        status=CompetitionStatus.LIVE.value,
        start_mode=CompetitionStartMode.SCHEDULED.value,
        stage="league",
        currency="coin",
        entry_fee_minor=0,
        platform_fee_bps=0,
        host_fee_bps=0,
        host_creation_fee_minor=0,
        gross_pool_minor=0,
        net_prize_pool_minor=0,
        metadata_json={},
    )
    regular_round = CompetitionRound(
        id="regular-round",
        competition_id=regular_competition.id,
        round_number=1,
        stage="league",
        status="scheduled",
        metadata_json={},
    )
    regular_match = CompetitionMatch(
        id="regular-match",
        competition_id=regular_competition.id,
        round_id=regular_round.id,
        round_number=1,
        stage="league",
        home_club_id=seeded_clubs[60].id,
        away_club_id=seeded_clubs[61].id,
        status=MatchStatus.IN_PROGRESS.value,
        scheduled_at=creator_match.scheduled_at - timedelta(hours=1) if creator_match.scheduled_at else None,
        metadata_json={},
    )
    session.add_all([regular_competition, regular_round, regular_match])
    session.commit()

    priority = service.live_priority(limit=5)

    assert priority.banner_title == "LIVE NOW - Creator League"
    assert priority.matches[0].is_creator_league is True
    assert priority.matches[0].competition_id == season.tiers[0].competition_id
    assert priority.matches[1].competition_id == regular_competition.id
