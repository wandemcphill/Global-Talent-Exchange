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
from app.auth.service import AuthService
from app.models.base import Base
from app.models.user import User
from app.risk.service import InsufficientCashError, InsufficientHoldingsError, RiskControlService
from app.wallets.service import WalletService


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
        email="risk@example.com",
        username="risk-user",
        password="SuperSecret1",
    )
    session.commit()
    return user


def test_buy_side_insufficient_cash_rejection(session) -> None:
    user = _create_user(session)

    with pytest.raises(InsufficientCashError, match="available cash"):
        RiskControlService().validate_trade(
            session,
            user,
            player_id="player-risk-buy",
            side="buy",
            quantity=Decimal("5"),
            price=Decimal("10"),
        )


def test_sell_side_insufficient_holdings_rejection(session) -> None:
    user = _create_user(session)
    wallet_service = WalletService()
    wallet_service.credit_position_units(
        session,
        user=user,
        player_id="player-risk-sell",
        quantity=Decimal("1"),
        reference="risk-seed",
        description="Seed one unit",
        external_reference="risk-seed-exec",
    )
    session.commit()

    with pytest.raises(InsufficientHoldingsError, match="exceeds owned quantity"):
        RiskControlService(wallet_service=wallet_service).validate_trade(
            session,
            user,
            player_id="player-risk-sell",
            side="sell",
            quantity=Decimal("2"),
            price=Decimal("10"),
        )
