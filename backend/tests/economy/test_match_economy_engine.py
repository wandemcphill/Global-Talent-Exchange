from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from shutil import copyfile

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import pytest

import app.models.admin_rules  # noqa: F401
import app.models.economy_daily_stat  # noqa: F401
import app.models.reward_settlement  # noqa: F401
import app.models.wallet  # noqa: F401
from app.core.database import ensure_database_schema_current
from app.economy.match_economy_engine import MatchEconomyContext, MatchEconomyEngine, MatchEconomyType
from app.models.base import utcnow
from app.models.economy_daily_stat import EconomyDailyStat
from app.models.reward_settlement import RewardSettlement
from app.models.user import User, UserRole
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.reward_engine.service import RewardEngineService
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture(scope="session")
def migrated_match_economy_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("match-economy-db") / "template.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    engine.dispose()
    return db_path


@pytest.fixture()
def session(tmp_path, migrated_match_economy_db):
    db_path = tmp_path / "match-economy.db"
    copyfile(migrated_match_economy_db, db_path)
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session
    engine.dispose()


def _create_user(
    session,
    *,
    user_id: str,
    email: str,
    username: str,
    role: UserRole = UserRole.USER,
    last_login_at=None,
) -> User:
    user = User(
        id=user_id,
        email=email,
        username=username,
        password_hash="hashed",
        role=role,
        last_login_at=last_login_at,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    session.flush()
    return user


def _seed_balance(session, wallet: WalletService, *, user: User, unit: LedgerUnit, amount: Decimal) -> None:
    user_account = wallet.get_user_account(session, user, unit)
    platform_account = wallet.ensure_platform_account(session, unit)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            LedgerPosting(account=platform_account, amount=-amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
        ],
        reason=wallet.trade_settlement_reason,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed:{user.id}:{unit.value}",
        actor=user,
    )


def _seed_system_balance(
    session,
    wallet: WalletService,
    *,
    account,
    unit: LedgerUnit,
    amount: Decimal,
    actor: User,
) -> None:
    operations_account = wallet.ensure_operations_account(session, unit)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=account, amount=amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            LedgerPosting(account=operations_account, amount=-amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
        ],
        reason=wallet.trade_settlement_reason,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"seed-system:{account.code}",
        actor=actor,
    )


def test_join_match_collects_user_hosted_entry_fee_into_prize_pool(session) -> None:
    wallet = WalletService()
    user = _create_user(
        session,
        user_id="user-hosted-player",
        email="user-hosted@example.com",
        username="user-hosted-player",
    )
    _seed_balance(session, wallet, user=user, unit=LedgerUnit.CREDIT, amount=Decimal("500.0000"))

    engine = MatchEconomyEngine(session=session, wallet_service=wallet)
    match = MatchEconomyContext(
        match_id="user-hosted-match-1",
        match_type=MatchEconomyType.USER_HOSTED,
        entry_fee=Decimal("250.0000"),
        prize_pool_unit=LedgerUnit.CREDIT,
        title="User Hosted Match",
    )

    result = engine.join_match(user=user, match=match)

    prize_pool_account = engine.ensure_prize_pool_account(match)
    treasury_account = wallet.ensure_treasury_account(session, LedgerUnit.CREDIT)
    assert result.charged_amount == Decimal("250.0000")
    assert result.transaction_id is not None
    assert result.prize_pool_account_code == prize_pool_account.code
    assert wallet.get_balance(session, prize_pool_account) == Decimal("200.0000")
    assert wallet.get_balance(session, treasury_account) == Decimal("50.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, user, LedgerUnit.CREDIT)) == Decimal("250.0000")


def test_join_match_is_free_for_gtex_hosted_matches(session) -> None:
    wallet = WalletService()
    user = _create_user(
        session,
        user_id="gtex-hosted-player",
        email="gtex-hosted@example.com",
        username="gtex-hosted-player",
    )

    engine = MatchEconomyEngine(session=session, wallet_service=wallet)
    match = MatchEconomyContext(
        match_id="gtex-hosted-match-1",
        match_type=MatchEconomyType.GTEX_HOSTED,
        entry_fee=Decimal("99.0000"),
        prize_pool_unit=LedgerUnit.COIN,
        title="GTEX Hosted Match",
    )

    result = engine.join_match(user=user, match=match)

    assert result.transaction_id is None
    assert result.charged_amount == Decimal("0.0000")
    assert result.prize_pool_balance == Decimal("0.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, user, LedgerUnit.COIN)) == Decimal("0.0000")


def test_fund_gtex_match_uses_promo_pool_as_controlled_source(session) -> None:
    wallet = WalletService()
    admin = _create_user(
        session,
        user_id="economy-admin",
        email="economy-admin@example.com",
        username="economy-admin",
        role=UserRole.ADMIN,
    )
    RewardEngineService(session=session, wallet_service=wallet).credit_promo_pool(
        actor=admin,
        amount=Decimal("20.0000"),
    )

    engine = MatchEconomyEngine(session=session, wallet_service=wallet)
    match = MatchEconomyContext(
        match_id="gtex-funded-match-1",
        match_type=MatchEconomyType.GTEX_HOSTED,
        prize_pool_unit=LedgerUnit.COIN,
        title="GTEX Final",
    )

    result = engine.fund_gtex_match(match=match, prize_amount=Decimal("7.5000"), actor=admin)

    prize_pool_account = engine.ensure_prize_pool_account(match)
    promo_pool_account = wallet.ensure_promo_pool_account(session, LedgerUnit.COIN)
    assert result.funded_amount == Decimal("7.5000")
    assert wallet.get_balance(session, prize_pool_account) == Decimal("7.5000")
    assert wallet.get_balance(session, promo_pool_account) == Decimal("12.5000")


def test_fund_gtex_match_can_top_up_rewards_pool_from_treasury(session) -> None:
    wallet = WalletService()
    admin = _create_user(
        session,
        user_id="treasury-admin",
        email="treasury-admin@example.com",
        username="treasury-admin",
        role=UserRole.ADMIN,
    )
    treasury_account = wallet.ensure_treasury_account(session, LedgerUnit.COIN)
    _seed_system_balance(
        session,
        wallet,
        account=treasury_account,
        unit=LedgerUnit.COIN,
        amount=Decimal("40.0000"),
        actor=admin,
    )

    engine = MatchEconomyEngine(session=session, wallet_service=wallet)
    match = MatchEconomyContext(
        match_id="gtex-funded-match-2",
        match_type=MatchEconomyType.GTEX_HOSTED,
        prize_pool_unit=LedgerUnit.COIN,
        title="GTEX Treasury Match",
    )

    result = engine.fund_gtex_match(match=match, prize_amount=Decimal("10.0000"), actor=admin)

    prize_pool_account = engine.ensure_prize_pool_account(match)
    rewards_pool_account = wallet.ensure_rewards_pool_account(session, LedgerUnit.COIN)
    assert result.funded_amount == Decimal("10.0000")
    assert wallet.get_balance(session, prize_pool_account) == Decimal("10.0000")
    assert wallet.get_balance(session, rewards_pool_account) == Decimal("0.0000")
    assert wallet.get_balance(session, treasury_account) == Decimal("30.0000")


def test_record_match_volume_triggers_lottery_for_recently_active_users(session) -> None:
    wallet = WalletService()
    admin = _create_user(
        session,
        user_id="lottery-admin",
        email="lottery-admin@example.com",
        username="lottery-admin",
        role=UserRole.ADMIN,
    )
    eligible_user = _create_user(
        session,
        user_id="eligible-user",
        email="eligible@example.com",
        username="eligible-user",
        last_login_at=utcnow(),
    )
    _create_user(
        session,
        user_id="stale-user",
        email="stale@example.com",
        username="stale-user",
        last_login_at=utcnow() - timedelta(days=45),
    )
    RewardEngineService(session=session, wallet_service=wallet).credit_promo_pool(
        actor=admin,
        amount=Decimal("20.0000"),
    )

    engine = MatchEconomyEngine(session=session, wallet_service=wallet)

    result = engine.record_match_volume(
        amount=Decimal("5.0000"),
        unit=LedgerUnit.CREDIT,
        actor=admin,
        trigger_step=Decimal("5.0000"),
        reward_options=(Decimal("3.0000"),),
        activity_window=timedelta(days=30),
    )

    settlement = session.scalar(
        select(RewardSettlement).where(RewardSettlement.reward_source == "lottery_volume_trigger")
    )
    daily_stat = session.get(EconomyDailyStat, utcnow().date())
    assert result.previous_volume == Decimal("0.0000")
    assert result.current_volume == Decimal("5.0000")
    assert len(result.triggered_rewards) == 1
    assert result.triggered_rewards[0].winner_user_id == eligible_user.id
    assert wallet.get_balance(session, wallet.get_user_account(session, eligible_user, LedgerUnit.COIN)) == Decimal("3.0000")
    assert settlement is not None
    assert settlement.net_amount == Decimal("3.0000")
    assert daily_stat is not None
    assert daily_stat.match_spend_amount == Decimal("5.0000")
