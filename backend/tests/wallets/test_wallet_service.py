from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.service import AuthService
from backend.app.models import Base, LedgerEntry, LedgerEntryReason, LedgerUnit, PaymentStatus
from backend.app.wallets.service import (
    InsufficientBalanceError,
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
