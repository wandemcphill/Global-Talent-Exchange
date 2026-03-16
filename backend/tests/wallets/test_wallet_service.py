from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.service import AuthService
from backend.app.models import Base, LedgerEntry, LedgerEntryReason, LedgerSourceTag, LedgerUnit, PaymentStatus
from backend.app.wallets.service import (
    InsufficientBalanceError,
    LedgerError,
    LedgerPosting,
    UnbalancedTransactionError,
    WalletService,
)


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


def _create_user(session):
    user = AuthService().register_user(
        session,
        email="wallet@example.com",
        username="walletuser",
        password="SuperSecret1",
    )
    session.commit()
    return user


def test_append_transaction_requires_balanced_postings(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)

    with pytest.raises(UnbalancedTransactionError, match="at least two postings"):
        service.append_transaction(
            session,
            postings=[LedgerPosting(account=user_account, amount=Decimal("10"))],
            reason=LedgerEntryReason.ADJUSTMENT,
        )


def test_verify_payment_event_credits_user_with_append_only_entries(session) -> None:
    user = _create_user(session)
    service = WalletService()
    payment_event = service.create_payment_event(
        session,
        user=user,
        provider="monnify",
        provider_reference="monnify-ref-001",
        amount=Decimal("50"),
        pack_code="starter-50",
    )
    service.verify_payment_event(session, payment_event, actor=user)
    session.commit()

    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    ledger_entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == payment_event.ledger_transaction_id)
    ).all()

    assert payment_event.status == PaymentStatus.VERIFIED
    assert len(ledger_entries) == 2
    assert service.get_balance(session, user_account) == Decimal("50.0000")
    assert service.get_balance(session, platform_account) == Decimal("-50.0000")

    ledger_entries[0].description = "tampered"
    with pytest.raises(ValueError, match="append-only"):
        session.commit()
    session.rollback()


def test_append_transaction_rejects_negative_balance_for_user_accounts(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)

    with pytest.raises(InsufficientBalanceError, match="does not have enough balance"):
        service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=Decimal("-1")),
                LedgerPosting(account=platform_account, amount=Decimal("1")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
        )


def test_request_payout_holds_total_and_tracks_fee(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("100")),
            LedgerPosting(account=platform_account, amount=Decimal("-100")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-payout",
        actor=user,
    )
    result = service.request_payout(
        session,
        user=user,
        amount=Decimal("20"),
        destination_reference="bank:0012345678",
        withdrawal_fee_bps=1000,
        minimum_fee=Decimal("0.0000"),
        source_scope="trade",
        actor=user,
    )
    session.commit()

    escrow_account = service.get_user_escrow_account(session, user, LedgerUnit.COIN)
    hold_entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == result.payout_request.hold_transaction_id)
    ).all()
    assert result.fee_amount == Decimal("2.0000")
    assert result.total_debit == Decimal("22.0000")
    assert service.get_balance(session, user_account) == Decimal("78.0000")
    assert service.get_balance(session, escrow_account) == Decimal("22.0000")
    assert sum(entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT) == Decimal("0.0000")
    assert sum(entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN) == Decimal("0.0000")
    assert sorted(entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT) == [
        Decimal("-20.0000"),
        Decimal("20.0000"),
    ]
    assert sorted(entry.amount for entry in hold_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN) == [
        Decimal("-2.0000"),
        Decimal("2.0000"),
    ]


def test_complete_payout_request_tags_only_fee_entries_as_fee_burn(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("100")),
            LedgerPosting(account=platform_account, amount=Decimal("-100")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-complete-payout",
        actor=user,
    )
    result = service.request_payout(
        session,
        user=user,
        amount=Decimal("20"),
        destination_reference="bank:0012345678",
        withdrawal_fee_bps=1000,
        minimum_fee=Decimal("0.0000"),
        source_scope="trade",
        actor=user,
    )
    payout_request = service.complete_payout_request(session, result.payout_request, actor=user)
    session.commit()

    settlement_entries = session.scalars(
        select(LedgerEntry).where(LedgerEntry.transaction_id == payout_request.settlement_transaction_id)
    ).all()
    assert sorted(entry.amount for entry in settlement_entries if entry.source_tag == LedgerSourceTag.ADMIN_ADJUSTMENT) == [
        Decimal("-20.0000"),
        Decimal("20.0000"),
    ]
    assert sorted(entry.amount for entry in settlement_entries if entry.source_tag == LedgerSourceTag.WITHDRAWAL_FEE_BURN) == [
        Decimal("-2.0000"),
        Decimal("2.0000"),
    ]


def test_request_competition_payout_requires_reward_balance(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("50")),
            LedgerPosting(account=platform_account, amount=Decimal("-50")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-wallet",
        actor=user,
    )
    with pytest.raises(InsufficientBalanceError, match="Competition reward balance"):
        service.request_payout(
            session,
            user=user,
            amount=Decimal("10"),
            destination_reference="bank:0012345678",
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("0.0000"),
            source_scope="competition",
            actor=user,
        )


def test_request_payout_rejects_unknown_source_scope(session) -> None:
    user = _create_user(session)
    service = WalletService()
    user_account = service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = service.ensure_platform_account(session, LedgerUnit.COIN)
    service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=Decimal("25")),
            LedgerPosting(account=platform_account, amount=Decimal("-25")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-scope",
        actor=user,
    )
    with pytest.raises(LedgerError, match="Withdrawal source must be trade, competition, user_hosted_gift, gtex_competition_gift, or national_reward"):
        service.request_payout(
            session,
            user=user,
            amount=Decimal("5"),
            destination_reference="bank:0012345678",
            withdrawal_fee_bps=1000,
            minimum_fee=Decimal("0.0000"),
            source_scope="bonus",
            actor=user,
        )
