from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.models import (
    Base,
    Competition,
    CompetitionEntry,
    CompetitionHistoryEntry,
    CompetitionParticipant,
    CompetitionPrizeRule,
    CompetitionProgressProfile,
    CompetitionReward,
    CompetitionRewardPool,
    CompetitionRuleSet,
    RewardSettlement,
)
from app.models.wallet import LedgerUnit
from app.reward_engine.service import RewardEngineService, RewardEngineError
from app.services.competition_lifecycle_service import CompetitionLifecycleService
from app.services.competition_wallet_service import CompetitionWalletService
from app.wallets.service import WalletService
from backend.tests.support.economic_policy import seed_economic_policy


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
        # create_all runs neither migration 20260827_0113 nor seed_defaults, so
        # resolve_economic_policy() would fail closed and settlement would be
        # skipped with "No active Admin economic policy exists" -- a database
        # shape production never has.
        seed_economic_policy(db_session)
        db_session.commit()
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


def _fund_user(session, user, amount: Decimal = Decimal("100.0000")) -> None:
    WalletService().credit_trade_proceeds(
        session,
        user=user,
        amount=amount,
        reference=f"seed:{user.id}",
        description="Competition wallet test funding",
        external_reference=f"seed:{user.id}",
        unit=LedgerUnit.CREDIT,
    )
    session.commit()


def _create_platform_competition(
    session, *, host_id: str, winner_id: str, runner_up_id: str, pool_minor: int = 1_000_000
) -> Competition:
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


def _create_user_hosted_competition(
    session,
    *,
    host_id: str,
    entrant_ids: list[str],
    entry_fee_minor: int = 200_000,
) -> Competition:
    gross_pool_minor = entry_fee_minor * len(entrant_ids)
    platform_fee_bps = 1000
    host_fee_bps = 500
    net_prize_pool_minor = (
        gross_pool_minor - (gross_pool_minor * platform_fee_bps // 10_000) - (gross_pool_minor * host_fee_bps // 10_000)
    )
    competition = Competition(
        host_user_id=host_id,
        name="User Hosted Treasure Chest",
        description="Paid league with wallet settlement",
        competition_type="league",
        format="league",
        visibility="public",
        status="completed",
        start_mode="scheduled",
        stage="completed",
        currency="credit",
        entry_fee_minor=entry_fee_minor,
        platform_fee_bps=platform_fee_bps,
        host_fee_bps=host_fee_bps,
        host_creation_fee_minor=0,
        gross_pool_minor=gross_pool_minor,
        net_prize_pool_minor=net_prize_pool_minor,
        metadata_json={},
    )
    session.add(competition)
    session.flush()
    session.add(
        CompetitionRuleSet(
            competition_id=competition.id,
            format="league",
            min_participants=4,
            max_participants=4,
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
            top_n=3,
            payout_percentages=[60, 25, 15],
        )
    )
    reward_pool = CompetitionRewardPool(
        competition_id=competition.id,
        pool_type="entry_fee",
        currency="credit",
        amount_minor=net_prize_pool_minor,
        status="planned",
        metadata_json={},
    )
    session.add(reward_pool)
    standings = [
        {"points": 9, "wins": 3, "goal_diff": 6, "goals_for": 8},
        {"points": 6, "wins": 2, "goal_diff": 2, "goals_for": 5},
        {"points": 3, "wins": 1, "goal_diff": -1, "goals_for": 3},
        {"points": 0, "wins": 0, "goal_diff": -7, "goals_for": 1},
    ]
    wallet_service = CompetitionWalletService(session)
    for user_id, stats in zip(entrant_ids, standings, strict=True):
        entry = CompetitionEntry(
            competition_id=competition.id,
            club_id=user_id,
            user_id=user_id,
            entry_type="direct",
            status="accepted",
            metadata_json={},
        )
        session.add(entry)
        session.flush()
        session.add(
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=user_id,
                entry_id=entry.id,
                status="joined",
                paid_entry_fee_minor=entry_fee_minor,
                paid_at=None,
                played=3,
                wins=stats["wins"],
                draws=0,
                losses=3 - stats["wins"],
                goals_for=stats["goals_for"],
                goals_against=max(stats["goals_for"] - stats["goal_diff"], 0),
                goal_diff=stats["goal_diff"],
                points=stats["points"],
            )
        )
        result = wallet_service.collect_entry_fee(competition=competition, participant_user_id=user_id)
        assert result.status == "settled"
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
    assert wallet_service.get_balance(session, winner_account) == settlement.net_amount
    assert wallet_service.get_balance(session, promo_pool_account) == (Decimal("100.0000") - settlement.gross_amount)


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
    settlements = session.scalars(
        select(RewardSettlement).where(RewardSettlement.competition_key == competition.id)
    ).all()
    assert len(rewards) == 1
    assert len(settlements) == 1


def test_finalize_user_hosted_competition_credits_wallets_and_records_progression(session) -> None:
    host = _create_user(session, email="wallet-host@example.com", username="wallethost")
    entrants = [
        _create_user(session, email="wallet-a@example.com", username="walleta"),
        _create_user(session, email="wallet-b@example.com", username="walletb"),
        _create_user(session, email="wallet-c@example.com", username="walletc"),
        _create_user(session, email="wallet-d@example.com", username="walletd"),
    ]
    wallet_service = WalletService()
    for user in entrants:
        _fund_user(session, user)
    competition = _create_user_hosted_competition(
        session,
        host_id=host.id,
        entrant_ids=[user.id for user in entrants],
    )

    lifecycle = CompetitionLifecycleService(session)
    lifecycle.finalize_competition(competition, settle=True)
    session.commit()

    rewards = session.scalars(
        select(CompetitionReward)
        .where(CompetitionReward.competition_id == competition.id)
        .order_by(CompetitionReward.placement.asc())
    ).all()
    assert [reward.amount_minor for reward in rewards] == [408_000, 170_000, 102_000]
    assert all(reward.status == "settled" for reward in rewards)

    credit_accounts = {user.id: wallet_service.get_user_account(session, user, LedgerUnit.CREDIT) for user in entrants}
    assert wallet_service.get_balance(session, credit_accounts[entrants[0].id]) == Decimal("120.8000")
    assert wallet_service.get_balance(session, credit_accounts[entrants[1].id]) == Decimal("97.0000")
    assert wallet_service.get_balance(session, credit_accounts[entrants[2].id]) == Decimal("90.2000")
    assert wallet_service.get_balance(session, credit_accounts[entrants[3].id]) == Decimal("80.0000")

    host_account = wallet_service.get_user_account(session, host, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(
        session,
        LedgerUnit.CREDIT,
    )
    assert wallet_service.get_balance(session, host_account) == Decimal("4.0000")
    assert wallet_service.get_balance(session, platform_account) == Decimal("8.0000")

    history = session.scalars(
        select(CompetitionHistoryEntry)
        .where(CompetitionHistoryEntry.competition_id == competition.id)
        .order_by(CompetitionHistoryEntry.placement.asc())
    ).all()
    assert len(history) == 4
    assert history[0].badge_code == "treasure_chest_gold"
    assert history[0].title_awarded == "Champion"
    assert history[0].earnings_minor == 408_000

    profile = session.scalar(
        select(CompetitionProgressProfile).where(CompetitionProgressProfile.subject_id == entrants[0].id)
    )
    assert profile is not None
    assert profile.current_title == "Champion"
    assert profile.total_earnings_minor == 408_000
    assert "treasure_chest_gold" in (profile.badges_json or [])
