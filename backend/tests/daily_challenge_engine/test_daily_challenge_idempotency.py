from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_engine.schemas import AdminRewardRuleStabilityControls
from app.auth.service import AuthService
from app.daily_challenge_engine.service import DailyChallengeError, DailyChallengeService
from app.models import (
    AdminFeatureFlag,
    AdminRewardRule,
    Base,
    DailyChallenge,
    DailyChallengeClaim,
    RewardSettlement,
    User,
)
from app.models.wallet import LedgerUnit
from app.reward_engine.service import RewardEngineService
from app.wallets.service import WalletService


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
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def _setup_environment(session, admin: User):
    # Enable daily-challenges feature flag
    session.add(
        AdminFeatureFlag(
            feature_key="daily-challenges",
            title="Daily Challenges",
            description="Daily challenges system",
            enabled=True,
        )
    )
    # Admin reward rules for fee calculations
    session.add(
        AdminRewardRule(
            rule_key="daily-reward-rules",
            title="Daily Challenge Rules",
            description="Testing daily challenge rewards.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=1000,
            stability_controls_json=AdminRewardRuleStabilityControls().model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()

    # Credit promo pool so rewards can be paid out
    reward_service = RewardEngineService(session)
    reward_service.credit_promo_pool(actor=admin, amount=Decimal("1000.0000"), unit=LedgerUnit.CREDIT)
    reward_service.credit_promo_pool(actor=admin, amount=Decimal("1000.0000"), unit=LedgerUnit.COIN)
    session.commit()


def test_daily_challenge_claim_is_unique_and_prevents_double_crediting(session) -> None:
    admin = _create_user(session, email="dc-admin@example.com", username="dc-admin")
    user = _create_user(session, email="dc-user@example.com", username="dc-user")
    _setup_environment(session, admin)

    service = DailyChallengeService(session)
    service.seed_defaults()
    session.commit()

    # 1. User claims daily-login challenge
    claim1 = service.claim(user=user, challenge_key="daily-login")
    session.commit()

    assert claim1 is not None
    assert claim1.user_id == user.id
    assert claim1.reward_settlement_id is not None
    assert Decimal(str(claim1.reward_amount)) >= Decimal("25.0000")

    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    balance_after_first = wallet_service.get_balance(session, user_account)
    assert balance_after_first > Decimal("0.0000")

    # 2. Same-day immediate duplicate claim attempt must raise DailyChallengeError
    with pytest.raises(DailyChallengeError, match="already been claimed for today"):
        service.claim(user=user, challenge_key="daily-login")

    # 3. Verify exactly 1 DailyChallengeClaim and 1 RewardSettlement record exist
    today = datetime.now(UTC).date()
    claims = list(
        session.scalars(
            select(DailyChallengeClaim).where(
                DailyChallengeClaim.user_id == user.id,
                DailyChallengeClaim.claim_date == today,
            )
        ).all()
    )
    assert len(claims) == 1

    settlements = list(
        session.scalars(
            select(RewardSettlement).where(
                RewardSettlement.competition_key == f"daily:daily-login:{today.isoformat()}",
                RewardSettlement.user_id == user.id,
                RewardSettlement.reward_source == "daily_challenge",
            )
        ).all()
    )
    assert len(settlements) == 1

    # Balance remains unchanged
    assert wallet_service.get_balance(session, user_account) == balance_after_first


def test_concurrent_session_savepoint_rollback_isolation(session) -> None:
    admin = _create_user(session, email="concurrent-admin@example.com", username="concurrent-admin")
    user = _create_user(session, email="concurrent-user@example.com", username="concurrent-user")
    _setup_environment(session, admin)

    service = DailyChallengeService(session)
    service.seed_defaults()
    session.commit()

    today = datetime.now(UTC).date()
    challenge = session.scalar(select(DailyChallenge).where(DailyChallenge.challenge_key == "watch-highlight"))
    assert challenge is not None
    # Raise claim_limit_per_day to 2 so a second claim bypasses the pre-check and directly
    # exercises the database UniqueConstraint("user_id", "challenge_id", "claim_date") savepoint rollback.
    challenge.claim_limit_per_day = 2
    session.commit()

    # First claim succeeds
    claim = service.claim(user=user, challenge_key="watch-highlight")
    session.commit()
    assert claim.id is not None

    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    balance_after_first = wallet_service.get_balance(session, user_account)

    # Verify that in a separate session, inserting a duplicate claim with the same (user_id, challenge_id, claim_date)
    # triggers the DB unique constraint IntegrityError and the nested savepoint rolls back cleanly before settling
    RetrySession = sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
    with RetrySession() as retry_session:
        retry_user = retry_session.get(User, user.id)
        assert retry_user is not None
        retry_service = DailyChallengeService(retry_session)

        with pytest.raises(DailyChallengeError, match="already been claimed for today"):
            retry_service.claim(user=retry_user, challenge_key="watch-highlight")

        # Session is still functional after the IntegrityError savepoint rollback
        streak = retry_service.build_login_streak(user=retry_user)
        assert streak is not None
        assert wallet_service.get_balance(retry_session, user_account) == balance_after_first
        assert streak is not None

    # Total claims in DB remain exactly 1
    total_claims = session.scalar(
        select(func.count(DailyChallengeClaim.id)).where(
            DailyChallengeClaim.user_id == user.id,
            DailyChallengeClaim.challenge_id == challenge.id,
            DailyChallengeClaim.claim_date == today,
        )
    )
    assert total_claims == 1
