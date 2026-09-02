"""Admin gift refunds must reverse both currency legs, not mint GTEX Coin.

A canonical gift debits FanCoin and credits GTEX Coin through a two-unit
conversion. Reversing it in a single unit would hand the sender withdrawable
Coin for a non-withdrawable FanCoin debit that was never unwound, creating
value the platform never received. These tests pin the compensating shape.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.gift_engine.router import admin_refund_gift_event
from app.gift_engine.service import GiftEngineService
from app.models import (
    AdminRewardRule,
    Base,
    EconomicConversion,
    GiftCatalogItem,
    GiftTransaction,
    GiftTransactionStatus,
    LedgerEntry,
    LedgerEntryReason,
    LedgerTransaction,
    LedgerUnit,
)
from app.wallets.service import LedgerPosting, WalletService

GIFT_KEY = "refund-safety-star"
GROSS = Decimal("100.0000")
RAKE = Decimal("30.0000")
NET = Decimal("70.0000")


def _make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def _seed(session, sender):
    session.add(
        GiftCatalogItem(
            key=GIFT_KEY,
            display_name="Refund Safety Star",
            fancoin_price=GROSS,
            active=True,
        )
    )
    session.add(
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
    session.commit()

    wallet = WalletService()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=wallet.get_user_account(session, sender, LedgerUnit.CREDIT), amount=GROSS),
            LedgerPosting(account=wallet.ensure_platform_account(session, LedgerUnit.CREDIT), amount=-GROSS),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-refund-safety",
        actor=sender,
    )
    session.commit()


def _accounts(session, wallet, sender, recipient) -> dict[str, object]:
    return {
        "sender_credit": wallet.get_user_account(session, sender, LedgerUnit.CREDIT),
        "sender_coin": wallet.get_user_account(session, sender, LedgerUnit.COIN),
        "recipient_coin": wallet.get_user_account(session, recipient, LedgerUnit.COIN),
        "bridge_credit": wallet.ensure_named_system_account(
            session,
            code="platform:credit:gift_conversion_bridge",
            label="Platform FanCoin Gift Conversion Bridge",
            unit=LedgerUnit.CREDIT,
            allow_negative=False,
        ),
        "bridge_coin": wallet.ensure_named_system_account(
            session,
            code="platform:coin:gift_conversion_bridge",
            label="Platform GTEX Coin Gift Conversion Bridge",
            unit=LedgerUnit.COIN,
            allow_negative=True,
        ),
        "fee_revenue": wallet.ensure_named_system_account(
            session,
            code="platform:credit:gift_conversion_fee_revenue",
            label="Platform FanCoin Gift Conversion Fee Revenue",
            unit=LedgerUnit.CREDIT,
            allow_negative=False,
        ),
    }


def _balances(session, wallet, accounts) -> dict[str, Decimal]:
    return {name: wallet.get_balance(session, account) for name, account in accounts.items()}


def _send_gift(session, sender, recipient):
    tx = GiftEngineService(session).send_gift(
        sender=sender,
        recipient_user_id=recipient.id,
        gift_key=GIFT_KEY,
        quantity=Decimal("1.0000"),
        source_scope="user_hosted",
        idempotency_key="refund-safety-gift",
    )
    session.commit()
    return tx


def test_refund_returns_fan_coin_and_never_mints_gtex_coin() -> None:
    session = _make_session()
    try:
        admin = _create_user(session, email="refund-admin@example.com", username="refund-admin")
        sender = _create_user(session, email="refund-sender@example.com", username="refund-sender")
        recipient = _create_user(session, email="refund-recipient@example.com", username="refund-recipient")
        _seed(session, sender)

        wallet = WalletService()
        accounts = _accounts(session, wallet, sender, recipient)
        tx = _send_gift(session, sender, recipient)

        after_gift = _balances(session, wallet, accounts)
        assert after_gift["sender_credit"] == Decimal("0.0000")
        assert after_gift["recipient_coin"] == NET
        assert after_gift["bridge_coin"] == -NET
        assert after_gift["bridge_credit"] == NET
        assert after_gift["fee_revenue"] == RAKE

        admin_refund_gift_event(event_id=tx.id, actor=admin, session=session)

        after_refund = _balances(session, wallet, accounts)
        # The sender is made whole in the currency they actually spent.
        assert after_refund["sender_credit"] == GROSS
        # ...and receives no withdrawable Coin at all. This is the invariant the
        # single-unit refund violated.
        assert after_refund["sender_coin"] == Decimal("0.0000")
        assert after_refund["recipient_coin"] == Decimal("0.0000")
        assert after_refund["bridge_coin"] == Decimal("0.0000")
        assert after_refund["bridge_credit"] == Decimal("0.0000")
        assert after_refund["fee_revenue"] == Decimal("0.0000")

        session.refresh(tx)
        assert tx.status is GiftTransactionStatus.REFUNDED

        conversion = session.get(EconomicConversion, tx.economic_conversion_id)
        assert conversion is not None
        assert conversion.status.value == "reversed"
        reversal_transaction_id = (conversion.metadata_json or {}).get("reversal_ledger_transaction_id")
        assert reversal_transaction_id

        entries = list(
            session.scalars(select(LedgerEntry).where(LedgerEntry.transaction_id == reversal_transaction_id))
        )
        assert {entry.unit for entry in entries} == {LedgerUnit.CREDIT, LedgerUnit.COIN}
        assert sum(Decimal(e.amount) for e in entries if e.unit is LedgerUnit.CREDIT) == Decimal("0.0000")
        assert sum(Decimal(e.amount) for e in entries if e.unit is LedgerUnit.COIN) == Decimal("0.0000")
        assert not any(
            e.unit is LedgerUnit.COIN and e.account_id == accounts["sender_coin"].id and Decimal(e.amount) > 0
            for e in entries
        )
    finally:
        session.close()


def test_repeated_refund_does_not_double_credit() -> None:
    session = _make_session()
    try:
        admin = _create_user(session, email="dup-admin@example.com", username="dup-admin")
        sender = _create_user(session, email="dup-sender@example.com", username="dup-sender")
        recipient = _create_user(session, email="dup-recipient@example.com", username="dup-recipient")
        _seed(session, sender)

        wallet = WalletService()
        accounts = _accounts(session, wallet, sender, recipient)
        tx = _send_gift(session, sender, recipient)

        admin_refund_gift_event(event_id=tx.id, actor=admin, session=session)
        first = _balances(session, wallet, accounts)
        transactions_after_first = session.scalar(select(func.count(LedgerTransaction.id)))

        admin_refund_gift_event(event_id=tx.id, actor=admin, session=session)
        second = _balances(session, wallet, accounts)

        assert first == second
        assert first["sender_credit"] == GROSS
        assert session.scalar(select(func.count(LedgerTransaction.id))) == transactions_after_first
        assert session.scalar(select(func.count(GiftTransaction.id))) == 1
    finally:
        session.close()


def test_refund_fails_closed_when_recipient_already_spent_the_coin() -> None:
    session = _make_session()
    try:
        admin = _create_user(session, email="spent-admin@example.com", username="spent-admin")
        sender = _create_user(session, email="spent-sender@example.com", username="spent-sender")
        recipient = _create_user(session, email="spent-recipient@example.com", username="spent-recipient")
        _seed(session, sender)

        wallet = WalletService()
        accounts = _accounts(session, wallet, sender, recipient)
        tx = _send_gift(session, sender, recipient)

        wallet.append_transaction(
            session,
            postings=[
                LedgerPosting(account=accounts["recipient_coin"], amount=-NET),
                LedgerPosting(account=wallet.ensure_platform_account(session, LedgerUnit.COIN), amount=NET),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference="recipient-spends-gift-coin",
            actor=recipient,
        )
        session.commit()

        before = _balances(session, wallet, accounts)
        transactions_before = session.scalar(select(func.count(LedgerTransaction.id)))
        entries_before = session.scalar(select(func.count(LedgerEntry.id)))

        with pytest.raises(Exception) as excinfo:
            admin_refund_gift_event(event_id=tx.id, actor=admin, session=session)
        assert "does not have enough balance" in str(excinfo.value)

        session.rollback()
        # Atomic: no partial ledger rows, no partial balance movement, and the
        # gift is not left marked refunded.
        assert session.scalar(select(func.count(LedgerTransaction.id))) == transactions_before
        assert session.scalar(select(func.count(LedgerEntry.id))) == entries_before
        assert _balances(session, wallet, accounts) == before
        assert wallet.get_balance(session, accounts["sender_coin"]) == Decimal("0.0000")
        assert wallet.get_balance(session, accounts["sender_credit"]) == Decimal("0.0000")

        session.refresh(tx)
        assert tx.status is not GiftTransactionStatus.REFUNDED
        conversion = session.get(EconomicConversion, tx.economic_conversion_id)
        assert conversion is not None and conversion.status.value == "settled"
    finally:
        session.close()
