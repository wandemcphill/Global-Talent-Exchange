from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.models.base import Base
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.user import User, UserRole
from app.players.market_integrity_service import PlayerShareMarketIntegrityService
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


def _player(session, player_id: str, *, tradable: bool = True) -> Player:
    player = Player(
        id=player_id,
        source_provider="integrity-test",
        provider_external_id=player_id,
        full_name=player_id,
        canonical_display_name=player_id,
        is_tradable=tradable,
    )
    session.add(player)
    session.flush()
    return player


def _user(session, user_id: str) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        role=UserRole.USER,
    )
    session.add(user)
    session.flush()
    return user


def test_audit_accepts_explicitly_issued_empty_market(session):
    player = _player(session, "integrity-issued")
    admin = _user(session, "integrity-admin")
    admin.role = UserRole.ADMIN
    service = PlayerTokenMarketService(session)
    service.issue_market(
        actor=admin,
        player_id=player.id,
        total_shares=100,
        share_price_coin=Decimal("0.1000"),
        liquidity_coin=Decimal("10.0000"),
    )
    session.commit()

    report = PlayerShareMarketIntegrityService(session).audit()

    assert report.markets_scanned == 1
    assert report.active_markets == 1
    assert report.healthy_markets == 1
    assert report.healthy is True
    assert report.issues == ()


def test_audit_flags_ineligible_active_market(session):
    player = _player(session, "integrity-ineligible", tradable=True)
    market = PlayerShareMarket(
        player_id=player.id,
        total_shares=100,
        circulating_shares=0,
        share_price_coin=Decimal("0.1000"),
        status="active",
        metadata_json={"market_issued": True, "auto_initialized": False, "liquidity_coin": "0.0000"},
    )
    session.add(market)
    session.flush()
    player.is_tradable = False
    session.commit()

    report = PlayerShareMarketIntegrityService(session).audit()
    codes = {issue.code for issue in report.issues}

    assert "ineligible_active_market" in codes
    assert report.healthy is False


def test_audit_flags_holding_circulation_mismatch(session):
    player = _player(session, "integrity-mismatch")
    user = _user(session, "integrity-holder")
    market = PlayerShareMarket(
        player_id=player.id,
        total_shares=100,
        circulating_shares=10,
        share_price_coin=Decimal("0.1000"),
        status="active",
        metadata_json={"market_issued": True, "auto_initialized": False, "liquidity_coin": "0.0000"},
    )
    session.add(market)
    session.flush()
    session.add(PlayerShareHolding(user_id=user.id, player_id=player.id, share_count=9))
    session.commit()

    report = PlayerShareMarketIntegrityService(session).audit()
    codes = {issue.code for issue in report.issues}

    assert "holding_circulation_mismatch" in codes


def test_audit_does_not_create_missing_liquidity_account(session):
    player = _player(session, "integrity-no-liquidity")
    session.add(
        PlayerShareMarket(
            player_id=player.id,
            total_shares=100,
            circulating_shares=0,
            share_price_coin=Decimal("0.1000"),
            status="active",
            metadata_json={"market_issued": True, "auto_initialized": False, "liquidity_coin": "0.0000"},
        )
    )
    session.commit()

    before = session.query(PlayerShareMarket).count()
    PlayerShareMarketIntegrityService(session).audit()
    after = session.query(PlayerShareMarket).count()

    assert before == after == 1
