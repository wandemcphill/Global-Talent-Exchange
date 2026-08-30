from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService
from app.players.trade_boundary import PlayerShareTradeBoundary


@pytest.fixture()
def session() -> Session:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _user(session: Session) -> User:
    user = User(
        id="trade-boundary-user",
        email="trade-boundary-user@example.com",
        username="trade-boundary-user",
        password_hash="hashed",  # pragma: allowlist secret
        role=UserRole.USER,
    )
    session.add(user)
    session.flush()
    return user


def _player(session: Session) -> Player:
    player = Player(
        id="trade-boundary-player",
        source_provider="test",
        provider_external_id="provider-trade-boundary-player",
        full_name="Trade Boundary Player",
        canonical_display_name="Trade Boundary Player",
        is_real_player=True,
        is_tradable=True,
    )
    session.add(player)
    session.flush()
    return player


def test_buy_rejects_unissued_market_before_trade_execution(session: Session) -> None:
    actor = _user(session)
    player = _player(session)
    service = PlayerTokenMarketService(session)
    boundary = PlayerShareTradeBoundary(session, service=service)

    with pytest.raises(PlayerTokenMarketError) as exc_info:
        boundary.buy(actor=actor, player_id=player.id, share_count=1, idempotency_key="boundary-buy-key")

    assert exc_info.value.reason == "market_not_found"
    assert session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)) is None


def test_sell_rejects_unissued_market_before_trade_execution(session: Session) -> None:
    actor = _user(session)
    player = _player(session)
    service = PlayerTokenMarketService(session)
    boundary = PlayerShareTradeBoundary(session, service=service)

    with pytest.raises(PlayerTokenMarketError) as exc_info:
        boundary.sell(actor=actor, player_id=player.id, share_count=1, idempotency_key="boundary-sell-key")

    assert exc_info.value.reason == "market_not_found"
    assert session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)) is None
