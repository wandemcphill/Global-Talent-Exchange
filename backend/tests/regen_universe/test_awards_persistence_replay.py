from __future__ import annotations


import pytest
from sqlalchemy import select

from app.models.regen_ecosystem import RegenAwardVote
from app.regen_universe.models import RegenAward, RegenAwardWinner, RegenHallOfFame, RegenSeason
from app.services.regen_ecosystem_service import RegenEcosystemService
from backend.tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


@pytest.fixture()
def session():
    db_session = build_regen_universe_session()
    try:
        yield db_session
    finally:
        db_session.close()


def test_award_vote_deduplication_and_winner_persistence_replay(session) -> None:
    bundle = seed_two_season_universe(session)
    universe_service = bundle["service"]
    eco_service = RegenEcosystemService(session)
    players = bundle["players"]

    season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
    assert season is not None

    award = session.scalar(select(RegenAward))
    assert award is not None

    user_id = bundle["club_profile"].owner_user_id
    player_id = players["veteran"].id

    first_vote = eco_service.cast_award_vote(
        award.id,
        user_id=user_id,
        player_id=player_id,
        season_id=season.id,
    )
    session.commit()

    second_vote = eco_service.cast_award_vote(
        award.id,
        user_id=user_id,
        player_id=player_id,
        season_id=season.id,
    )
    session.commit()

    assert first_vote.id == second_vote.id
    vote_count = (
        session.query(RegenAwardVote)
        .filter_by(
            award_id=award.id,
            user_id=user_id,
            player_id=player_id,
            season_id=season.id,
        )
        .count()
    )
    assert vote_count == 1

    universe_service.close_season(season.id, start_next_season=True)
    session.commit()

    winners_first_pass = list(
        session.scalars(select(RegenAwardWinner).where(RegenAwardWinner.season_id == season.id)).all()
    )
    hall_of_fame_first_pass = list(session.scalars(select(RegenHallOfFame)).all())
    assert len(winners_first_pass) > 0

    universe_service.close_season(season.id, start_next_season=False)
    session.commit()

    winners_second_pass = list(
        session.scalars(select(RegenAwardWinner).where(RegenAwardWinner.season_id == season.id)).all()
    )
    hall_of_fame_second_pass = list(session.scalars(select(RegenHallOfFame)).all())

    assert len(winners_second_pass) == len(winners_first_pass)
    assert len(hall_of_fame_second_pass) == len(hall_of_fame_first_pass)
