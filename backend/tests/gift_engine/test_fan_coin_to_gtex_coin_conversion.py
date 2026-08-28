from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.economy.conversion_service import EconomicConversionError, FanCoinGiftConversionService
from app.gift_engine.service import GiftEngineService
from app.models import (
    AdminRewardRule,
    Base,
    EconomicConversion,
    GiftCatalogItem,
    GiftTransaction,
    LedgerEntry,
    LedgerEntryReason,
    LedgerTransaction,
    LedgerUnit,
    RevenueShareRule,
)
from app.wallets.service import LedgerPosting, WalletService
from backend.tests.support.economic_policy import seed_economic_policy


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


def _seed_gift_economy(session, sender, *, gift_key: str = "conversion-star"):
    session.add(
        GiftCatalogItem(
            key=gift_key,
            display_name="Conversion Star",
            fancoin_price=Decimal("100.0000"),
            active=True,
        )
    )
    # The gift rake is read from the Admin economic policy, not RevenueShareRule.
    # The legacy rule stays seeded with a deliberately different share so these
    # tests also prove the retired authority can no longer move the split.
    session.add(
        RevenueShareRule(
            rule_key="gift-30",
            scope="gift",
            title="Gift 30 percent rake",
            description=None,
            platform_share_bps=9500,
            creator_share_bps=0,
            recipient_share_bps=None,
            burn_bps=0,
            priority=10,
            active=True,
        )
    )
    seed_economic_policy(session, gift_platform_rake_bps=3000)
    session.commit()

    wallet = WalletService()
    sender_account = wallet.get_user_account(session, sender, LedgerUnit.CREDIT)
    platform_credit = wallet.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=sender_account, amount=Decimal("100.0000")),
            LedgerPosting(account=platform_credit, amount=Decimal("-100.0000")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-gift-conversion",
        actor=sender,
    )
    session.commit()


def _assert_converted(session, wallet, tx, sender, recipient) -> None:
    sender_credit = wallet.get_user_account(session, sender, LedgerUnit.CREDIT)
    recipient_credit = wallet.get_user_account(session, recipient, LedgerUnit.CREDIT)
    recipient_coin = wallet.get_user_account(session, recipient, LedgerUnit.COIN)
    bridge_coin = wallet.ensure_named_system_account(
        session,
        code="platform:coin:gift_conversion_bridge",
        label="Platform GTEX Coin Gift Conversion Bridge",
        unit=LedgerUnit.COIN,
        allow_negative=True,
    )

    assert wallet.get_balance(session, sender_credit) == Decimal("0.0000")
    assert wallet.get_balance(session, recipient_credit) == Decimal("0.0000")
    assert wallet.get_balance(session, recipient_coin) == Decimal("70.0000")
    assert wallet.get_balance(session, bridge_coin) == Decimal("-70.0000")
    assert tx.ledger_unit is LedgerUnit.COIN
    assert tx.source_ledger_unit is LedgerUnit.CREDIT
    assert tx.destination_ledger_unit is LedgerUnit.COIN
    assert tx.recipient_net_amount == Decimal("70.0000")
    assert tx.platform_rake_amount == Decimal("30.0000")
    assert tx.economic_conversion_id is not None

    conversion = session.scalar(select(EconomicConversion).where(EconomicConversion.id == tx.economic_conversion_id))
    assert conversion is not None
    assert conversion.source_unit is LedgerUnit.CREDIT
    assert conversion.destination_unit is LedgerUnit.COIN
    assert conversion.source_amount == Decimal("100.0000")
    assert conversion.destination_amount == Decimal("70.0000")
    assert conversion.platform_fee_amount == Decimal("30.0000")
    assert conversion.status.value == "settled"

    entries = list(session.scalars(select(LedgerEntry).where(LedgerEntry.transaction_id == tx.ledger_transaction_id)))
    assert len(entries) == 5
    assert {entry.unit for entry in entries} == {LedgerUnit.CREDIT, LedgerUnit.COIN}
    assert sum(Decimal(entry.amount) for entry in entries if entry.unit is LedgerUnit.CREDIT) == Decimal("0.0000")
    assert sum(Decimal(entry.amount) for entry in entries if entry.unit is LedgerUnit.COIN) == Decimal("0.0000")
    assert sum(
        Decimal(entry.amount)
        for entry in entries
        if entry.unit is LedgerUnit.COIN and entry.account_id == recipient_coin.id
    ) == Decimal("70.0000")


def test_user_hosted_gift_is_one_atomic_fan_coin_to_gtex_coin_ledger_transaction() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="gift-sender@example.com", username="gift-sender")
        recipient = _create_user(session, email="gift-recipient@example.com", username="gift-recipient")
        _seed_gift_economy(session, sender)

        tx = GiftEngineService(session).send_gift(
            sender=sender,
            recipient_user_id=recipient.id,
            gift_key="conversion-star",
            quantity=Decimal("1.0000"),
            source_scope="user_hosted",
            idempotency_key="conversion-gift-user-hosted",
        )
        session.commit()

        _assert_converted(session, WalletService(), tx, sender, recipient)
        transaction_count = session.scalar(select(func.count(LedgerTransaction.id)))
        gift_ledger_count = session.scalar(
            select(func.count(LedgerTransaction.id)).where(LedgerTransaction.id == tx.ledger_transaction_id)
        )
        assert transaction_count == 2
        assert gift_ledger_count == 1
    finally:
        session.close()


def test_gtex_competition_gift_uses_same_fan_coin_to_gtex_coin_conversion() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="gtex-gift-sender@example.com", username="gtex-gift-sender")
        recipient = _create_user(
            session,
            email="gtex-gift-recipient@example.com",
            username="gtex-gift-recipient",
        )
        _seed_gift_economy(session, sender, gift_key="stadium-conversion-star")

        tx = GiftEngineService(session).send_gift(
            sender=sender,
            recipient_user_id=recipient.id,
            gift_key="stadium-conversion-star",
            quantity=Decimal("1.0000"),
            source_scope="gtex_competition",
            competition_id="gtex-competition-1",
            match_id="match-1",
            idempotency_key="conversion-gift-gtex-competition",
        )
        session.commit()

        assert tx.source_scope == "gtex_competition"
        _assert_converted(session, WalletService(), tx, sender, recipient)
    finally:
        session.close()


def test_gift_idempotency_reuses_the_existing_atomic_conversion() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="idempotent-sender@example.com", username="idempotent-sender")
        recipient = _create_user(session, email="idempotent-recipient@example.com", username="idempotent-recipient")
        _seed_gift_economy(session, sender)
        service = GiftEngineService(session)

        first = service.send_gift(
            sender=sender,
            recipient_user_id=recipient.id,
            gift_key="conversion-star",
            quantity=Decimal("1.0000"),
            idempotency_key="conversion-gift-idempotent",
        )
        session.commit()
        second = service.send_gift(
            sender=sender,
            recipient_user_id=recipient.id,
            gift_key="conversion-star",
            quantity=Decimal("1.0000"),
            idempotency_key="conversion-gift-idempotent",
        )
        session.commit()

        assert second.id == first.id
        assert session.scalar(select(func.count(GiftTransaction.id))) == 1
        assert session.scalar(select(func.count(EconomicConversion.id))) == 1
        assert session.scalar(select(func.count(LedgerTransaction.id))) == 2
    finally:
        session.close()


def test_conversion_service_rejects_non_reconciling_currency_legs_before_ledger_mutation() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="conversion-source@example.com", username="conversion-source")
        recipient = _create_user(session, email="conversion-target@example.com", username="conversion-target")
        conversion_service = FanCoinGiftConversionService(session)

        try:
            conversion_service.convert(
                source_user_id=sender.id,
                recipient_user_id=recipient.id,
                gross_fancoin=Decimal("100.0000"),
                platform_fee_fancoin=Decimal("30.0000"),
                destination_coin_amount=Decimal("71.0000"),
                conversion_key="invalid-conversion",
                idempotency_key="invalid-conversion",
            )
        except EconomicConversionError as exc:
            assert "reconcile exactly" in str(exc)
        else:
            raise AssertionError("Non-reconciling gift conversion unexpectedly succeeded.")

        assert session.scalar(select(func.count(LedgerTransaction.id))) == 0
        assert session.scalar(select(func.count(EconomicConversion.id))) == 0
    finally:
        session.close()
