from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import backend.app.ingestion.models  # noqa: F401
import backend.app.ledger.models  # noqa: F401
import backend.app.models  # noqa: F401
import backend.app.orders.models  # noqa: F401
from backend.app.auth.service import AuthService
from backend.app.ingestion.models import Player
from backend.app.models.base import Base
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntry, LedgerEntryReason, LedgerUnit
from backend.app.orders.models import Order, OrderSide, OrderStatus
from backend.app.orders.service import OrderService
from backend.app.risk.service import DuplicateSettlementError
from backend.app.settlement.service import SettlementService
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


def _create_user(session) -> User:
    user = AuthService().register_user(
        session,
        email="settlement@example.com",
        username="settlement-user",
        password="SuperSecret1",
    )
    session.commit()
    return user


def _create_player(session, *, provider_external_id: str = "settlement-player") -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Settlement Test Player",
        is_tradable=True,
    )
    session.add(player)
    session.commit()
    return player


def _fund_user(session, user: User, *, amount: Decimal) -> None:
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
        reference="settlement-funding",
        description="Seed cash for settlement tests",
        actor=user,
    )
    session.commit()


def _place_buy_order(session, user: User, player: Player) -> Order:
    order = OrderService().place_order(
        session,
        user=user,
        player_id=player.id,
        side=OrderSide.BUY,
        quantity=Decimal("2"),
        max_price=Decimal("10"),
    )
    session.commit()
    session.refresh(order)
    return order


def test_successful_settlement_path(session) -> None:
    user = _create_user(session)
    player = _create_player(session)
    _fund_user(session, user, amount=Decimal("100"))
    order = _place_buy_order(session, user, player)

    SettlementService().settle_order_execution(
        session,
        user=user,
        execution_id="exec-settle-1",
        order_id=order.id,
        quantity=Decimal("2"),
        price=Decimal("9"),
    )
    session.commit()
    session.refresh(order)

    wallet_service = WalletService()
    wallet_summary = wallet_service.get_wallet_summary(session, user, currency=LedgerUnit.COIN)

    assert order.status is OrderStatus.FILLED
    assert wallet_summary.available_balance == Decimal("82.0000")
    assert wallet_summary.reserved_balance == Decimal("0.0000")
    assert wallet_service.get_available_position_quantity(session, user, player.id) == Decimal("2.0000")


def test_duplicate_settlement_prevention(session) -> None:
    user = _create_user(session)
    player = _create_player(session, provider_external_id="settlement-player-dup")
    _fund_user(session, user, amount=Decimal("100"))
    order = _place_buy_order(session, user, player)
    service = SettlementService()

    service.settle_order_execution(
        session,
        user=user,
        execution_id="exec-settle-dup",
        order_id=order.id,
        quantity=Decimal("2"),
        price=Decimal("9"),
    )
    session.commit()

    with pytest.raises(DuplicateSettlementError, match="already been settled"):
        service.settle_order_execution(
            session,
            user=user,
            execution_id="exec-settle-dup",
            order_id=order.id,
            quantity=Decimal("2"),
            price=Decimal("9"),
        )


def test_ledger_entries_written_on_settlement(session) -> None:
    user = _create_user(session)
    player = _create_player(session, provider_external_id="settlement-player-ledger")
    _fund_user(session, user, amount=Decimal("100"))
    order = _place_buy_order(session, user, player)

    SettlementService().settle_order_execution(
        session,
        user=user,
        execution_id="exec-settle-ledger",
        order_id=order.id,
        quantity=Decimal("2"),
        price=Decimal("9"),
    )
    session.commit()

    entries = session.scalars(
        select(LedgerEntry)
        .where(
            LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
            LedgerEntry.external_reference == "exec-settle-ledger",
        )
        .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
    ).all()

    assert len(entries) == 4
    assert {entry.reference for entry in entries} == {order.id}
