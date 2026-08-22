from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.gift_engine.service import GiftEngineService
from app.models import Base, EconomicConversion, GiftCatalogItem, LedgerEntryReason, LedgerUnit, RevenueShareRule
from app.wallets.service import LedgerPosting, WalletService


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
        password="SuperSecret1",
    )
    session.commit()
    return user


def test_any_gift_converts_recipient_fan_coin_to_withdrawable_gtex_coin() -> None:
    session = _make_session()
    try:
        sender = _create_user(session, email="gift-sender@example.com", username="gift-sender")
        recipient = _create_user(session, email="gift-recipient@example.com", username="gift-recipient")
        session.add(
            GiftCatalogItem(
                key="conversion-star",
                display_name="Conversion Star",
                fancoin_price=Decimal("100.0000"),
                active=True,
            )
        )
        session.add(
            RevenueShareRule(
                rule_key="gift-30",
                scope="gift",
                title="Gift 30 percent rake",
                description=None,
                platform_share_bps=3000,
                creator_share_bps=0,
                recipient_share_bps=None,
                burn_bps=0,
                priority=10,
                active=True,
            )
        )
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

        tx = GiftEngineService(session).send_gift(
            sender=sender,
            recipient_user_id=recipient.id,
            gift_key="conversion-star",
            quantity=Decimal("1.0000"),
            source_scope="user_hosted",
            idempotency_key="conversion-gift-1",
        )
        session.commit()

        recipient_credit = wallet.get_user_account(session, recipient, LedgerUnit.CREDIT)
        recipient_coin = wallet.get_user_account(session, recipient, LedgerUnit.COIN)

        assert wallet.get_balance(session, recipient_credit) == Decimal("0.0000")
        assert wallet.get_balance(session, recipient_coin) == Decimal("70.0000")
        assert tx.ledger_unit is LedgerUnit.COIN
        assert tx.source_ledger_unit is LedgerUnit.CREDIT
        assert tx.destination_ledger_unit is LedgerUnit.COIN
        assert tx.recipient_net_amount == Decimal("70.0000")
        assert tx.economic_conversion_id is not None

        conversion = session.scalar(
            select(EconomicConversion).where(EconomicConversion.id == tx.economic_conversion_id)
        )
        assert conversion is not None
        assert conversion.source_unit is LedgerUnit.CREDIT
        assert conversion.destination_unit is LedgerUnit.COIN
        assert conversion.source_amount == Decimal("70.0000")
        assert conversion.destination_amount == Decimal("70.0000")
        assert conversion.platform_fee_amount == Decimal("0.0000")
        assert conversion.status.value == "settled"
    finally:
        session.close()
