from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from backend.app.auth.service import AuthService
from backend.app.gift_engine.service import GiftEngineService
from backend.app.models import (
    Base,
    GiftCatalogItem,
    GiftComboEvent,
    GiftComboRule,
    GiftTransaction,
    LedgerEntryReason,
    LedgerUnit,
    RevenueShareRule,
)
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


def test_gift_combo_applies_bonus(session) -> None:
    sender = _create_user(session, email="sender@example.com", username="sender")
    recipient = _create_user(session, email="recipient@example.com", username="recipient")

    gift_item = GiftCatalogItem(
        key="cheer",
        display_name="Cheer",
        fancoin_price=Decimal("100.0000"),
        active=True,
    )
    session.add(gift_item)
    session.add(
        RevenueShareRule(
            rule_key="gift-default",
            scope="gift",
            title="Gift default",
            description=None,
            platform_share_bps=3000,
            creator_share_bps=0,
            recipient_share_bps=None,
            burn_bps=0,
            priority=10,
            active=True,
        )
    )
    session.add(
        GiftComboRule(
            rule_key="combo-2",
            title="2x combo",
            description="Second gift within window grants bonus.",
            min_combo_count=2,
            window_seconds=300,
            bonus_bps=500,
            priority=10,
            active=True,
        )
    )
    session.commit()

    wallet_service = WalletService()
    sender_account = wallet_service.get_user_account(session, sender, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=sender_account, amount=Decimal("500.0000")),
            LedgerPosting(account=platform_account, amount=Decimal("-500.0000")),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="seed-gifts",
        actor=sender,
    )
    session.commit()

    service = GiftEngineService(session)
    first_tx = service.send_gift(
        sender=sender,
        recipient_user_id=recipient.id,
        gift_key="cheer",
        quantity=Decimal("1.0000"),
    )
    session.commit()

    assert session.scalar(select(GiftComboEvent)) is None

    second_tx = service.send_gift(
        sender=sender,
        recipient_user_id=recipient.id,
        gift_key="cheer",
        quantity=Decimal("1.0000"),
    )
    session.commit()

    combo_event = session.scalar(select(GiftComboEvent).order_by(GiftComboEvent.created_at.desc()))
    assert combo_event is not None
    assert combo_event.combo_count == 2
    assert combo_event.bonus_amount == Decimal("5.0000")

    refreshed = session.get(GiftTransaction, second_tx.id)
    assert refreshed is not None
    assert refreshed.recipient_net_amount == Decimal("75.0000")
