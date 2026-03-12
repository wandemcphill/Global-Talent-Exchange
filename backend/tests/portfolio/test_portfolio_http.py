from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import backend.app.ingestion.models  # noqa: F401
import backend.app.ledger.models  # noqa: F401
import backend.app.models  # noqa: F401
import backend.app.orders.models  # noqa: F401
import backend.app.players.read_models  # noqa: F401
import backend.app.value_engine.read_models  # noqa: F401
from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.auth.service import AuthService
from backend.app.ingestion.models import Player
from backend.app.models.base import Base
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.settlement.service import SettlementService, TradeExecution
from backend.app.wallets.router import router
from backend.app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def api_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    current_user = AuthService().register_user(
        session,
        email="portfolio-http@example.com",
        username="portfolio-http-user",
        password="SuperSecret1",
    )
    session.commit()

    app = FastAPI()
    app.include_router(router)

    def override_session():
        yield session

    def override_current_user():
        return current_user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield client, session, current_user

    session.close()


def _create_player(session, *, provider_external_id: str = "portfolio-http-player") -> Player:
    player = Player(
        source_provider="manual",
        provider_external_id=provider_external_id,
        full_name="Portfolio HTTP Player",
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
        reference="portfolio-http-funding",
        description="Seed cash for portfolio HTTP tests",
        actor=user,
    )
    session.commit()


def _set_player_price(session, player: Player, *, price: Decimal) -> None:
    session.add(
        PlayerSummaryReadModel(
            player_id=player.id,
            player_name=player.full_name,
            last_snapshot_at=player.created_at,
            current_value_credits=float(price),
            previous_value_credits=float(price),
            movement_pct=0.0,
            summary_json={},
        )
    )
    session.commit()


def test_portfolio_api_endpoints(api_context) -> None:
    client, session, current_user = api_context
    player = _create_player(session)
    _fund_user(session, current_user, amount=Decimal("100"))
    SettlementService().settle_execution(
        session,
        user=current_user,
        execution=TradeExecution(
            execution_id="exec-http-1",
            player_id=player.id,
            side="buy",
            quantity=Decimal("2"),
            price=Decimal("10"),
            reserve_before_settlement=True,
        ),
    )
    session.commit()
    _set_player_price(session, player, price=Decimal("12"))

    portfolio_response = client.get("/api/portfolio")
    snapshot_response = client.get("/api/portfolio/snapshot")
    legacy_snapshot_response = client.get("/portfolio")
    summary_response = client.get("/api/portfolio/summary")

    assert portfolio_response.status_code == 200
    assert snapshot_response.status_code == 200
    assert legacy_snapshot_response.status_code == 200
    assert summary_response.status_code == 200

    portfolio_payload = portfolio_response.json()
    snapshot_payload = snapshot_response.json()
    legacy_snapshot_payload = legacy_snapshot_response.json()
    summary_payload = summary_response.json()
    assert set(portfolio_payload) == {"holdings"}
    assert len(portfolio_payload["holdings"]) == 1
    holding = portfolio_payload["holdings"][0]
    assert set(holding) == {
        "player_id",
        "quantity",
        "average_cost",
        "current_price",
        "market_value",
        "unrealized_pl",
        "unrealized_pl_percent",
    }
    assert holding["player_id"] == player.id
    assert Decimal(str(holding["average_cost"])) == Decimal("10.0000")
    assert Decimal(str(holding["current_price"])) == Decimal("12.0000")
    assert Decimal(str(holding["market_value"])) == Decimal("24.0000")
    assert Decimal(str(holding["unrealized_pl"])) == Decimal("4.0000")
    assert snapshot_payload == legacy_snapshot_payload
    assert set(snapshot_payload) == {
        "user_id",
        "currency",
        "available_balance",
        "reserved_balance",
        "total_balance",
        "holdings",
    }
    assert snapshot_payload["user_id"] == current_user.id
    assert Decimal(str(snapshot_payload["available_balance"])) == Decimal("80.0000")
    assert Decimal(str(snapshot_payload["reserved_balance"])) == Decimal("0.0000")
    assert Decimal(str(snapshot_payload["total_balance"])) == Decimal("80.0000")
    assert len(snapshot_payload["holdings"]) == 1
    assert set(summary_payload) == {
        "total_market_value",
        "cash_balance",
        "total_equity",
        "unrealized_pl_total",
        "realized_pl_total",
    }
    assert Decimal(str(summary_payload["total_market_value"])) == Decimal("24.0000")
    assert Decimal(str(summary_payload["cash_balance"])) == Decimal("80.0000")
    assert Decimal(str(summary_payload["total_equity"])) == Decimal("104.0000")
