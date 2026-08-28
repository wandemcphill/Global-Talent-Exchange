from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_wallet_payments_treasury_release import audit  # noqa: E402
from app.auth.service import AuthService  # noqa: E402
from app.models import (  # noqa: E402
    AdminRewardRule,
    AdminRuntimeState,
    Base,
    CountryFeaturePolicy,
    KycStatus,
    LedgerEntry,
    LedgerEntryReason,
    LedgerTransaction,
    LedgerUnit,
    PayoutRequest,
)
from app.models.treasury import PaymentMode, RateDirection, TreasuryWithdrawalStatus  # noqa: E402
from app.policies.service import PolicyService  # noqa: E402
from app.treasury.service import TreasuryService  # noqa: E402
from app.wallets.service import LedgerPosting, WalletService  # noqa: E402
from backend.tests.support.economic_policy import seed_economic_policy


def test_wallet_payments_treasury_release_gate_passes() -> None:
    report = audit()
    assert report["pass"] is True, report
    assert report["violations"] == []
    assert report["read_only"] is True


def test_live_money_movement_surfaces_are_present() -> None:
    expected = [
        ROOT / "app" / "wallets" / "service.py",
        ROOT / "app" / "wallets" / "rail_service.py",
        ROOT / "app" / "services" / "payment_gateway_service.py",
        ROOT / "app" / "treasury" / "service.py",
        ROOT / "app" / "admin_finance" / "service.py",
        ROOT / "app" / "admin_finance" / "router.py",
    ]
    assert all(path.exists() for path in expected)


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    seed_economic_policy(session)
    session.commit()
    return session


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def _seed_withdrawal_policy(session) -> None:
    # _make_session() already seeds the single canonical active policy. A
    # second active AdminRewardRule here would make resolve_economic_policy()
    # fail closed on "more than one active" instead of resolving.
    session.add(
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
    session.add(
        AdminRuntimeState(
            state_key="admin_god_mode",
            payload_json={
                "commissions": {
                    "withdrawal_fee_bps": 1000,
                    "minimum_withdrawal_fee_credits": "5.0000",
                },
                "withdrawal_controls": {
                    "trade_withdrawals_enabled": True,
                    "processor_mode": "manual_bank_transfer",
                    "payouts_via_bank_transfer": True,
                },
            },
        )
    )
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


def _configure_withdrawal(session) -> None:
    treasury = TreasuryService()
    settings = treasury.ensure_settings(session)
    settings.withdrawal_rate_value = Decimal("1.0000")
    settings.withdrawal_rate_direction = RateDirection.FIAT_PER_COIN
    settings.min_withdrawal = Decimal("10.0000")
    settings.max_withdrawal = Decimal("100000.0000")
    settings.withdrawal_mode = PaymentMode.MANUAL
    session.commit()


def _seed_coin_balance(session, user, amount: Decimal) -> None:
    wallet = WalletService()
    account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    clearing = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=account, amount=amount),
            LedgerPosting(account=clearing, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="withdrawal-e2e-seed",
        actor=user,
    )
    session.commit()


def test_manual_withdrawal_complete_path_reconciles_ledger() -> None:
    session = _make_session()
    try:
        _seed_withdrawal_policy(session)
        user = _create_user(session, email="withdraw-e2e@example.com", username="withdraw-e2e")
        admin = _create_user(session, email="withdraw-admin@example.com", username="withdraw-admin")
        user.kyc_status = KycStatus.FULLY_VERIFIED
        session.commit()
        _accept_required_policies(session, user)
        _configure_withdrawal(session)
        _seed_coin_balance(session, user, Decimal("110.0000"))

        treasury = TreasuryService()
        bank_account = treasury.create_user_bank_account(
            session,
            user=user,
            bank_name="GTEX Test Bank",
            account_number="1234567890",
            account_name="GTEX Test User",
            bank_code="001",
            currency_code="NGN",
            set_active=True,
        )
        session.commit()

        withdrawal = treasury.create_withdrawal_request(
            session,
            user=user,
            amount_coin=Decimal("100.0000"),
            bank_account_id=bank_account.id,
            source_scope="trade",
            notes="manual provider payout e2e",
        )
        session.commit()

        payout = session.get(PayoutRequest, withdrawal.payout_request_id)
        assert payout is not None
        assert withdrawal.status == TreasuryWithdrawalStatus.PENDING_REVIEW
        assert payout.status.value == "reviewing"
        assert withdrawal.unit is LedgerUnit.COIN
        assert withdrawal.amount_coin == Decimal("100.0000")
        assert withdrawal.fee_amount == Decimal("10.0000")
        assert withdrawal.net_amount == Decimal("100.0000")

        payout_meta = json.loads(payout.notes or "{}")
        assert payout_meta["processor_mode"] == "manual_bank_transfer"
        assert payout_meta["payout_channel"] == "bank_transfer"
        assert payout_meta["total_debit"] == "110.0000"

        user_coin = treasury.wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        user_escrow = treasury.wallet_service.get_user_escrow_account(session, user, LedgerUnit.COIN)
        assert treasury.wallet_service.get_balance(session, user_coin) == Decimal("0.0000")
        assert treasury.wallet_service.get_balance(session, user_escrow) == Decimal("110.0000")

        treasury.review_withdrawal_status(
            session,
            actor=admin,
            withdrawal_id=withdrawal.id,
            status=TreasuryWithdrawalStatus.APPROVED,
            admin_notes="approved for manual bank payout",
        )
        session.commit()
        assert withdrawal.status == TreasuryWithdrawalStatus.APPROVED
        assert payout.status.value == "reviewing"

        treasury.review_withdrawal_status(
            session,
            actor=admin,
            withdrawal_id=withdrawal.id,
            status=TreasuryWithdrawalStatus.PROCESSING,
            admin_notes="bank transfer submitted",
        )
        session.commit()
        assert withdrawal.status == TreasuryWithdrawalStatus.PROCESSING
        assert payout.status.value == "processing"

        treasury.review_withdrawal_status(
            session,
            actor=admin,
            withdrawal_id=withdrawal.id,
            status=TreasuryWithdrawalStatus.PAID,
            admin_notes="provider confirmation received",
        )
        session.commit()

        session.refresh(withdrawal)
        session.refresh(payout)
        assert withdrawal.status == TreasuryWithdrawalStatus.PAID
        assert withdrawal.paid_at is not None
        assert payout.status.value == "completed"
        assert payout.settlement_transaction_id is not None

        withdrawal_clearing = treasury.wallet_service.ensure_withdrawal_clearing_account(
            session, LedgerUnit.COIN
        )
        assert treasury.wallet_service.get_balance(session, user_coin) == Decimal("0.0000")
        assert treasury.wallet_service.get_balance(session, user_escrow) == Decimal("0.0000")
        assert treasury.wallet_service.get_balance(session, withdrawal_clearing) == Decimal("110.0000")

        settlement_entries = list(
            session.scalars(
                select(LedgerEntry).where(LedgerEntry.transaction_id == payout.settlement_transaction_id)
            ).all()
        )
        assert len(settlement_entries) == 4
        assert {entry.unit for entry in settlement_entries} == {LedgerUnit.COIN}
        assert sum(Decimal(entry.amount) for entry in settlement_entries) == Decimal("0.0000")
        assert sum(Decimal(entry.amount) for entry in settlement_entries if entry.account_id == user_escrow.id) == Decimal("-110.0000")
        assert sum(Decimal(entry.amount) for entry in settlement_entries if entry.account_id == withdrawal_clearing.id) == Decimal("110.0000")

        withdrawal_transactions = session.scalar(
            select(func.count(LedgerTransaction.id)).where(LedgerTransaction.id == payout.settlement_transaction_id)
        )
        assert withdrawal_transactions == 1
    finally:
        session.close()
