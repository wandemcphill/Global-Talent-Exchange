from __future__ import annotations

from decimal import Decimal
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.auth.service import AuthService
from app.models import (
    AdminRuntimeState,
    Base,
    CountryFeaturePolicy,
    KycStatus,
    LedgerEntryReason,
    LedgerUnit,
    TreasuryAuditEvent,
)
from app.models.risk_ops import AmlCase, SystemEvent
from app.models.treasury import PaymentMode, RateDirection, TreasuryWithdrawalStatus
from app.models.withdrawal_review import WithdrawalReview
from app.models.wallet import PayoutRequest, PayoutStatus
from app.policies.service import PolicyService
from app.treasury.service import TreasuryService
from app.wallets.service import LedgerPosting, WalletService


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
    state = AdminRuntimeState(
        state_key="admin_god_mode",
        payload_json={
            "commissions": {
                "withdrawal_fee_bps": 1000,
                "minimum_withdrawal_fee_credits": "5.0000",
            },
            "withdrawal_controls": {
                "egame_withdrawals_enabled": False,
                "trade_withdrawals_enabled": True,
                "processor_mode": "manual_bank_transfer",
                "deposits_via_bank_transfer": True,
                "payouts_via_bank_transfer": True,
            },
        },
    )
    session.add(state)
    session.commit()


def _accept_required_policies(session, user) -> None:
    service = PolicyService(session)
    service.seed_defaults()
    service.ensure_user_region_profile(user=user, region_code="NG")
    for version in service.list_missing_acceptances(user_id=user.id):
        service.accept_document(
            user_id=user.id,
            document_key=version.document.document_key,
            version_label=version.version_label,
            ip_address=None,
            device_id=None,
        )
    session.commit()


def _seed_balance(session, *, user, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
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


