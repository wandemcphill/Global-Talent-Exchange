from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.models.base import Base
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.players.trade_boundary import PlayerShareTradeBoundary
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService
from app.ingestion.models import Player
from app.wallets.service import WalletService


@pytest.fixture()
def session():
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


def _user(session, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _player(session, player_id: str) -> Player:
    player = Player(
        id=player_id,
        source_provider="boundary-test",
        provider_external_id=player_id,
        full_name="Boundary Test Player",
        canonical_display_name="Boundary Test Player",
        is_tradable=True,
    )
    session.add(player)
    session.flush()
    return player


def test_trade_boundary_rejects_unissued_market_without_creating_one(session):
    player = _player(session, "boundary-unissued")
    fan = _user(session, "boundary-fan")
    service = PlayerTokenMarketService(session)
    boundary = PlayerShareTradeBoundary(session, service)

    with pytest.raises(PlayerTokenMarketError) as exc_info:
        boundary.buy(actor=fan, player_id=player.id, share_count=1)

    assert exc_info.value.reason == "market_not_found"
    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).first() is None


def test_trade_boundary_accepts_only_existing_issued_market(session):
    player = _player(session, "boundary-issued")
    admin = _user(session, "boundary-admin", UserRole.ADMIN)
    fan = _user(session, "boundary-fan-issued")
    wallet = WalletService()
    service = PlayerTokenMarketService(session, wallet_service=wallet)
    service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=100,
        share_price_coin=Decimal("0.1000"),
    )

    boundary = PlayerShareTradeBoundary(session, service)
    market = boundary.require_issued_market(player.id)

    assert market.player_id == player.id
    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).count() == 1

    with pytest.raises(PlayerTokenMarketError, match="does not have enough balance"):
        boundary.buy(actor=fan, player_id=player.id, share_count=1)
