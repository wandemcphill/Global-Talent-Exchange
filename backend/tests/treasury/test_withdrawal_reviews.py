from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.service import AuthService
from backend.app.models import Base, CountryFeaturePolicy, KycStatus, LedgerEntryReason, LedgerUnit, TreasuryAuditEvent
from backend.app.models.risk_ops import AmlCase, SystemEvent
from backend.app.models.treasury import RateDirection, TreasuryWithdrawalStatus
from backend.app.models.withdrawal_review import WithdrawalReview
from backend.app.treasury.service import TreasuryService
from backend.app.wallets.service import LedgerPosting, WalletService


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


def _seed_policy(session) -> None:
    policy = CountryFeaturePolicy(
        country_code="GLOBAL",
        bucket_type="default",
        deposits_enabled=True,
        market_trading_enabled=True,
        platform_reward_withdrawals_enabled=True,
        user_hosted_gift_withdrawals_enabled=True,
        gtex_competition_gift_withdrawals_enabled=True,
        national_reward_withdrawals_enabled=True,
        one_time_region_change_after_days=180,
        active=True,
    )
    session.add(policy)
    session.commit()


def _seed_balance(session, *, user, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-balance",
        actor=user,
    )
    session.commit()


def _configure_withdrawal_settings(session) -> None:
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    settings.withdrawal_rate_value = Decimal("1.0000")
    settings.withdrawal_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_withdrawal = Decimal("0.0000")
    settings.max_withdrawal = Decimal("100000.0000")
    session.flush()


def test_withdrawal_review_creates_review_and_audit(session) -> None:
    _seed_policy(session)
    user = _create_user(session, email="withdrawal@example.com", username="withdrawaluser")
    admin = _create_user(session, email="admin@example.com", username="adminuser")
    user.kyc_status = KycStatus.FULLY_VERIFIED
    session.commit()
    _configure_withdrawal_settings(session)
    _seed_balance(session, user=user, amount=Decimal("100.0000"))

    treasury = TreasuryService()
    bank_account = treasury.create_user_bank_account(
        session,
        user=user,
        bank_name="Test Bank",
        account_number="1234567890",
        account_name="Test User",
        bank_code="001",
        currency_code="NGN",
        set_active=True,
    )
    session.commit()

    withdrawal = treasury.create_withdrawal_request(
        session,
        user=user,
        amount_coin=Decimal("10.0000"),
        bank_account_id=bank_account.id,
        source_scope="trade",
        notes="payout",
    )
    session.commit()

    reviewed = treasury.review_withdrawal_status(
        session,
        actor=admin,
        withdrawal_id=withdrawal.id,
        status=TreasuryWithdrawalStatus.APPROVED,
        admin_notes="approved",
    )
    session.commit()

    review = session.scalar(
        select(WithdrawalReview)
        .where(WithdrawalReview.withdrawal_request_id == withdrawal.id)
        .order_by(WithdrawalReview.created_at.desc())
    )
    assert reviewed.status == TreasuryWithdrawalStatus.APPROVED
    assert review is not None
    assert review.status_from == TreasuryWithdrawalStatus.PENDING_REVIEW.value
    assert review.status_to == TreasuryWithdrawalStatus.APPROVED.value
    assert review.fee_amount == withdrawal.fee_amount
    assert review.net_amount == withdrawal.net_amount

    audit = session.scalar(
        select(TreasuryAuditEvent).where(TreasuryAuditEvent.resource_id == withdrawal.id)
    )
    assert audit is not None


def test_withdrawal_risk_flags_and_dispute_event(session) -> None:
    _seed_policy(session)
    user = _create_user(session, email="risk@example.com", username="riskuser")
    admin = _create_user(session, email="riskadmin@example.com", username="riskadmin")
    user.kyc_status = KycStatus.FULLY_VERIFIED
    session.commit()
    _configure_withdrawal_settings(session)
    _seed_balance(session, user=user, amount=Decimal("7000.0000"))

    treasury = TreasuryService()
    bank_account = treasury.create_user_bank_account(
        session,
        user=user,
        bank_name="Risk Bank",
        account_number="9999999999",
        account_name="Risk User",
        bank_code="002",
        currency_code="NGN",
        set_active=True,
    )
    session.commit()

    withdrawal = treasury.create_withdrawal_request(
        session,
        user=user,
        amount_coin=Decimal("6000.0000"),
        bank_account_id=bank_account.id,
        source_scope="trade",
        notes="large payout",
    )
    session.commit()

    aml_case = session.scalar(select(AmlCase).where(AmlCase.user_id == user.id))
    assert aml_case is not None

    treasury.review_withdrawal_status(
        session,
        actor=admin,
        withdrawal_id=withdrawal.id,
        status=TreasuryWithdrawalStatus.DISPUTED,
        admin_notes="disputed",
    )
    session.commit()

    system_event = session.scalar(
        select(SystemEvent).where(SystemEvent.subject_id == withdrawal.id)
    )
    assert system_event is not None
