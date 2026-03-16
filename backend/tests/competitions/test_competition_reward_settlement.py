from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.service import AuthService
from backend.app.models import (
    Base,
    Competition,
    CompetitionEntry,
    CompetitionParticipant,
    CompetitionPrizeRule,
    CompetitionReward,
    CompetitionRewardPool,
    CompetitionRuleSet,
    RewardSettlement,
)
from backend.app.reward_engine.service import RewardEngineService, RewardEngineError
from backend.app.services.competition_lifecycle_service import CompetitionLifecycleService
from backend.app.wallets.service import WalletService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def _create_platform_competition(session, *, host_id: str, winner_id: str, runner_up_id: str, pool_minor: int = 1_000_000) -> Competition:
    competition = Competition(
        host_user_id=host_id,
        name="GTEX Platform Cup",
        description="Promo-funded final",
        competition_type="league",
        source_type="gtex_platform",
        format="league",
        visibility="public",
        status="completed",
        start_mode="scheduled",
        stage="completed",
        currency="coin",
        entry_fee_minor=0,
        platform_fee_bps=0,
        host_fee_bps=0,
        host_creation_fee_minor=0,
        gross_pool_minor=0,
        net_prize_pool_minor=pool_minor,
        metadata_json={},
    )
    session.add(competition)
    session.flush()
    session.add(
        CompetitionRuleSet(
            competition_id=competition.id,
            format="league",
            min_participants=2,
            max_participants=2,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
            league_tie_break_order=["points", "goal_diff", "goals_for"],
            league_home_away=False,
            cup_allowed_participant_sizes=[],
            group_stage_enabled=False,
        )
    )
    session.add(
        CompetitionPrizeRule(
            competition_id=competition.id,
            payout_mode="custom_percent",
            top_n=1,
            payout_percentages=[100],
        )
    )
    reward_pool = CompetitionRewardPool(
        competition_id=competition.id,
        pool_type="promo_pool",
        currency="coin",
        amount_minor=pool_minor,
        status="planned",
        metadata_json={},
    )
    session.add(reward_pool)
    winner_entry = CompetitionEntry(
        competition_id=competition.id,
        club_id=winner_id,
        user_id=winner_id,
        entry_type="direct",
        status="accepted",
        metadata_json={},
    )
    runner_up_entry = CompetitionEntry(
        competition_id=competition.id,
        club_id=runner_up_id,
        user_id=runner_up_id,
        entry_type="direct",
        status="accepted",
        metadata_json={},
    )
    session.add_all([winner_entry, runner_up_entry])
    session.flush()
    session.add_all(
        [
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=winner_id,
                entry_id=winner_entry.id,
                status="joined",
                points=3,
                goal_diff=2,
                goals_for=2,
            ),
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=runner_up_id,
                entry_id=runner_up_entry.id,
                status="joined",
                points=0,
                goal_diff=-2,
                goals_for=0,
            ),
        ]
    )
    session.flush()
    return competition


def test_finalize_competition_settles_platform_rewards_to_ledger(session) -> None:
    host = _create_user(session, email="host@example.com", username="hostuser")
    winner = _create_user(session, email="winner@example.com", username="winneruser")
    runner_up = _create_user(session, email="runnerup@example.com", username="runnerupuser")
    competition = _create_platform_competition(session, host_id=host.id, winner_id=winner.id, runner_up_id=runner_up.id)

    reward_engine = RewardEngineService(session)
    reward_engine.credit_promo_pool(actor=host, amount=Decimal("100.0000"))

    lifecycle = CompetitionLifecycleService(session)
    lifecycle.finalize_competition(competition, settle=True)
    session.commit()

    reward = session.scalar(select(CompetitionReward).where(CompetitionReward.competition_id == competition.id))
    settlement = session.scalar(select(RewardSettlement).where(RewardSettlement.competition_key == competition.id))
    assert reward is not None
    assert settlement is not None
    assert reward.status == "settled"
    assert reward.ledger_transaction_id == settlement.ledger_transaction_id
    assert reward.metadata_json["reward_settlement_id"] == settlement.id

    wallet_service = WalletService()
    winner_account = wallet_service.get_user_account(session, winner, settlement.ledger_unit)
    promo_pool_account = wallet_service.ensure_promo_pool_account(session, settlement.ledger_unit)
    assert wallet_service.get_balance(session, winner_account) == Decimal("90.0000")
    assert wallet_service.get_balance(session, promo_pool_account) == Decimal("0.0000")


def test_finalize_competition_blocks_when_promo_pool_is_underfunded(session) -> None:
    host = _create_user(session, email="host2@example.com", username="hostuser2")
    winner = _create_user(session, email="winner2@example.com", username="winneruser2")
    runner_up = _create_user(session, email="runnerup2@example.com", username="runnerupuser2")
    competition = _create_platform_competition(session, host_id=host.id, winner_id=winner.id, runner_up_id=runner_up.id)

    lifecycle = CompetitionLifecycleService(session)
    with pytest.raises(RewardEngineError, match="Promo pool balance is lower than the reward amount."):
        lifecycle.finalize_competition(competition, settle=True)


def test_finalize_competition_does_not_duplicate_reward_rows_or_settlements(session) -> None:
    host = _create_user(session, email="host3@example.com", username="hostuser3")
    winner = _create_user(session, email="winner3@example.com", username="winneruser3")
    runner_up = _create_user(session, email="runnerup3@example.com", username="runnerupuser3")
    competition = _create_platform_competition(session, host_id=host.id, winner_id=winner.id, runner_up_id=runner_up.id)

    reward_engine = RewardEngineService(session)
    reward_engine.credit_promo_pool(actor=host, amount=Decimal("100.0000"))

    lifecycle = CompetitionLifecycleService(session)
    lifecycle.finalize_competition(competition, settle=True)
    session.commit()
    lifecycle.finalize_competition(competition, settle=True)
    session.commit()

    rewards = session.scalars(select(CompetitionReward).where(CompetitionReward.competition_id == competition.id)).all()
    settlements = session.scalars(select(RewardSettlement).where(RewardSettlement.competition_key == competition.id)).all()
    assert len(rewards) == 1
    assert len(settlements) == 1
