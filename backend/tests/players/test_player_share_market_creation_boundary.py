from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.players.token_service import PlayerTokenMarketService


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


def _player(session, player_id: str) -> Player:
    player = Player(
        id=player_id,
        source_provider="test",
        provider_external_id=f"provider-{player_id}",
        full_name="Boundary Test Player",
        canonical_display_name="Boundary Test Player",
        is_real_player=True,
        is_tradable=True,
    )
    session.add(player)
    return player


def _admin(session) -> User:
    admin = User(
        id="share-boundary-admin",
        email="share-boundary-admin@example.com",
        username="share-boundary-admin",
        password_hash="hashed",
        role=UserRole.ADMIN,
    )
    session.add(admin)
    return admin


def test_eligible_player_creation_does_not_implicitly_issue_share_market(session) -> None:
    player = _player(session, "player-no-implicit-market")
    session.flush()

    assert player.share_market is None
    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).first() is None


def test_explicit_issue_still_creates_market(session) -> None:
    player = _player(session, "player-explicit-market")
    admin = _admin(session)
    session.flush()

    market = PlayerTokenMarketService(session).issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=1000,
        share_price_coin=Decimal("0.1000"),
        liquidity_coin=Decimal("25.0000"),
    )

    assert market.player_id == player.id
    assert market.total_shares == 1000
    assert market.status == "active"
    assert session.query(PlayerShareMarket).filter_by(player_id=player.id).one().id == market.id
