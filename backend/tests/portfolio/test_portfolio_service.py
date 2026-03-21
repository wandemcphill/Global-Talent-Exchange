from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import app.ingestion.models  # noqa: F401
import app.ledger.models  # noqa: F401
import app.models  # noqa: F401
import app.orders.models  # noqa: F401
import app.players.read_models  # noqa: F401
import app.value_engine.read_models  # noqa: F401
from app.auth.service import AuthService
from app.ingestion.models import Player
from app.models.base import Base
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.players.read_models import PlayerSummaryReadModel
from app.portfolio.service import PortfolioService
from app.settlement.service import SettlementService, TradeExecution
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


def _create_user(session) -> User:
    user = AuthService().register_user(
        session,
        email="portfolio@example.com",
        username="portfolio-user",
        password="SuperSecret1",
    )
    session.commit()
    return user


def _create_player(session, *, provider_external_id: str = "portfolio-player") -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Portfolio Test Player",
        is_tradable=True,
    )
    session.add(player)
    session.commit()
    return player


def _fund_user(session, user: User, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="portfolio-funding",
        description="Seed cash for portfolio tests",
        actor=user,
    )
    session.commit()


def _set_player_price(session, player: Player, *, price: Decimal) -> None:
    summary = session.get(PlayerSummaryReadModel, player.id)
    if summary is None:
        summary = PlayerSummaryReadModel(
            player_id=player.id,
            player_name=player.full_name,
            last_snapshot_at=player.created_at,
            current_value_credits=float(price),
            previous_value_credits=float(price),
            movement_pct=0.0,
            summary_json={},
        )
        session.add(summary)
    else:
        summary.current_value_credits = float(price)
        summary.previous_value_credits = float(price)
    session.commit()


def _settle_buy(session, user: User, player: Player, *, quantity: Decimal, price: Decimal, execution_id: str) -> None:
    SettlementService().settle_execution(
        session,
        user=user,
        execution=TradeExecution(
            execution_id=execution_id,
            player_id=player.id,
            side="buy",
            quantity=quantity,
            price=price,
            reserve_before_settlement=True,
        ),
    )
    session.commit()


def test_portfolio_valuation_with_price_changes(session) -> None:
    user = _create_user(session)
    player = _create_player(session)
    _fund_user(session, user, amount=Decimal("100"))
    _settle_buy(session, user, player, quantity=Decimal("2"), price=Decimal("10"), execution_id="exec-price-1")
    _set_player_price(session, player, price=Decimal("12"))

    service = PortfolioService()
    first_snapshot = service.build_for_user(session, user)

    assert len(first_snapshot.holdings) == 1
    first_holding = first_snapshot.holdings[0]
    assert first_holding.quantity == Decimal("2.0000")
    assert first_holding.average_cost == Decimal("10.0000")
    assert first_holding.current_price == Decimal("12.0000")
    assert first_holding.market_value == Decimal("24.0000")
    assert first_holding.unrealized_pl == Decimal("4.0000")
    assert first_holding.unrealized_pl_percent == Decimal("20.0000")

    _set_player_price(session, player, price=Decimal("15"))
    second_snapshot = service.build_for_user(session, user)
    second_holding = second_snapshot.holdings[0]

    assert second_holding.current_price == Decimal("15.0000")
    assert second_holding.market_value == Decimal("30.0000")
    assert second_holding.unrealized_pl == Decimal("10.0000")
    assert second_snapshot.summary.total_market_value == Decimal("30.0000")


def test_empty_portfolio_summary(session) -> None:
    user = _create_user(session)

    summary = PortfolioService().build_summary(session, user)

    assert summary.total_market_value == Decimal("0.0000")
    assert summary.cash_balance == Decimal("0.0000")
    assert summary.total_equity == Decimal("0.0000")
    assert summary.unrealized_pl_total == Decimal("0.0000")
    assert summary.realized_pl_total == Decimal("0.0000")


def test_unrealized_pl_computation(session) -> None:
    user = _create_user(session)
    player = _create_player(session, provider_external_id="portfolio-player-loss")
    _fund_user(session, user, amount=Decimal("100"))
    _settle_buy(session, user, player, quantity=Decimal("3"), price=Decimal("10"), execution_id="exec-price-2")
    _set_player_price(session, player, price=Decimal("8"))

    holding = PortfolioService().build_holdings(session, user)[0]

    assert holding.market_value == Decimal("24.0000")
    assert holding.unrealized_pl == Decimal("-6.0000")
    assert holding.unrealized_pl_percent == Decimal("-20.0000")
