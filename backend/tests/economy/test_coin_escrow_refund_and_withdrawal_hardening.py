from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.economy.hosted_competition_coin_escrow import HostedCompetitionCoinEscrowService
from app.models import (
    AdminRewardRule,
    AdminRuntimeState,
    Base,
    CompetitionTemplate,
    CountryFeaturePolicy,
    HostedCompetitionStatus,
    KycStatus,
    LedgerEntryReason,
    LedgerUnit,
    TreasuryWithdrawalStatus,
    UserHostedCompetition,
)
from app.models.hosted_competition import HostedCompetitionFundingMode
from app.models.user import User
from app.policies.service import PolicyService
from app.treasury.service import TreasuryError, TreasuryService
from app.wallets.service import LedgerError, LedgerPosting, WalletService


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        db_session.add(
            AdminRewardRule(
                rule_key="platform-economy-defaults",
                title="Platform Economy Defaults",
                description="Canonical Admin fee and rake policy.",
                trading_fee_bps=2000,
                gift_platform_rake_bps=3000,
                withdrawal_fee_bps=1000,
                minimum_withdrawal_fee_credits=Decimal("5.0000"),
                competition_platform_fee_bps=3000,
                stability_controls_json={},
                active=True,
            )
        )
        db_session.add(
            CountryFeaturePolicy(
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
        )
        db_session.add(
            AdminRuntimeState(
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
        )
        db_session.commit()
        yield db_session
    engine.dispose()


def _create_user(session: Session, *, email: str, username: str) -> User:
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecretPassword123!",  # pragma: allowlist secret — synthetic fixture password, not a credential
    )
    user.kyc_status = KycStatus.VERIFIED
    session.commit()
    return user


def _accept_required_policies(session: Session, user: User) -> None:
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


def _fund_coin(session: Session, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=account, amount=amount),
            LedgerPosting(account=platform, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"seed-coin:{user.id}",
        actor=user,
    )
    session.commit()


def test_coin_escrow_refund_to_host(session: Session) -> None:
    host = _create_user(session, email="host1@example.com", username="host1")
    _fund_coin(session, host, Decimal("100.0000"))

    template = CompetitionTemplate(
        title="Standard Cup",
        description="Standard 8-player knockout cup",
        template_key="standard_cup",
        competition_type="cup",
        team_type="club",
        participants=8,
        is_user_hostable=True,
    )
    session.add(template)
    session.commit()

    wallet = WalletService()
    escrow_service = HostedCompetitionCoinEscrowService(session, wallet)

    competition = UserHostedCompetition(
        template_id=template.id,
        host_user_id=host.id,
        title="Escrow Refund Cup",
        slug="escrow-refund-cup",
        funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
        entry_fee_fancoin=Decimal("0.0000"),
        reward_pool_fancoin=Decimal("0.0000"),
        reward_pool_coin=Decimal("50.0000"),
        host_funding_required_coin=Decimal("50.0000"),
        host_funding_escrowed_coin=Decimal("0.0000"),
        status=HostedCompetitionStatus.OPEN,
    )
    session.add(competition)
    session.commit()

    # Host funds the competition escrow
    escrow_service.fund_from_host(competition=competition, host=host, gross_prize=Decimal("50.0000"))
    assert escrow_service.available_balance(competition) == Decimal("50.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, host, LedgerUnit.COIN)) == Decimal("50.0000")

    # Competition is cancelled, escrow refunded to host
    tx_id = escrow_service.refund_to_host(
        competition=competition,
        host=host,
        actor=host,
        reason="Competition cancelled before start",
    )
    assert tx_id is not None
    assert escrow_service.available_balance(competition) == Decimal("0.0000")
    assert wallet.get_balance(session, wallet.get_user_account(session, host, LedgerUnit.COIN)) == Decimal("100.0000")
    assert competition.host_funding_escrowed_coin == Decimal("0.0000")


def test_payout_rejects_fancoin_currency(session: Session) -> None:
    user = _create_user(session, email="payout-user@example.com", username="payout_user")
    wallet = WalletService()

    with pytest.raises(LedgerError, match="FanCoin is never withdrawable"):
        wallet.request_payout(
            session,
            user=user,
            amount=Decimal("50.0000"),
            destination_reference="BANK-12345",
            unit=LedgerUnit.CREDIT,
        )


def test_treasury_review_rejects_terminal_state_transition(session: Session) -> None:
    admin = _create_user(session, email="admin-review@example.com", username="admin_review")
    user = _create_user(session, email="user-review@example.com", username="user_review")
    _accept_required_policies(session, user)
    _fund_coin(session, user, Decimal("100.0000"))

    wallet = WalletService()
    treasury = TreasuryService(wallet_service=wallet)
    bank_account = treasury.create_user_bank_account(
        session,
        user=user,
        bank_code="044",
        bank_name="Access Bank",
        account_number="0123456789",
        account_name="Test User",
        currency_code="NGN",
        set_active=True,
    )
    w_req = treasury.create_withdrawal_request(
        session,
        user=user,
        amount_coin=Decimal("20.0000"),
        bank_account_id=bank_account.id,
    )
    session.commit()

    # Reject the withdrawal
    reviewed = treasury.review_withdrawal_status(
        session,
        actor=admin,
        withdrawal_id=w_req.id,
        status=TreasuryWithdrawalStatus.REJECTED,
        admin_notes="Suspicious activity",
    )
    session.commit()
    assert reviewed.status == TreasuryWithdrawalStatus.REJECTED

    # Attempting to change status from REJECTED to PAID must raise TreasuryError
    with pytest.raises(TreasuryError, match="Terminal withdrawal request with status rejected cannot change status"):
        treasury.review_withdrawal_status(
            session,
            actor=admin,
            withdrawal_id=w_req.id,
            status=TreasuryWithdrawalStatus.PAID,
        )
