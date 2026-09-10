from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player
from app.models.base import Base
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.user import User
from app.market.lifecycle_status import (
    resolve_player_lifecycle_status,
    sync_player_lifecycle_and_market_status,
)
from app.players.market_integrity_service import PlayerShareMarketIntegrityService
from app.players.token_service import PlayerTokenMarketService
from app.players.legacy_token_service import PlayerTokenMarketError


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_resolve_player_lifecycle_status_all_4_states(db_session: Session) -> None:
    # 1. Unknown / Unavailable
    assert resolve_player_lifecycle_status(None) == ("unknown_unavailable", "Unknown / Unavailable")

    # 2. Active / Tradable
    player_active = Player(
        id="player_act_1",
        source_provider="test_prov",
        provider_external_id="ext_act_1",
        full_name="Active Tradable Player",
        is_tradable=True,
    )
    market_active = PlayerShareMarket(
        id="market_act_1",
        player_id=player_active.id,
        status="active",
        share_price_coin=Decimal("10.0000"),
    )
    player_active.share_market = market_active
    db_session.add_all([player_active, market_active])
    db_session.flush()

    assert resolve_player_lifecycle_status(player_active, market_active) == ("active_tradable", "Active / Tradable")

    # 3. Active / Not Tradable (is_tradable=True but no active share market)
    player_unissued = Player(
        id="player_act_2",
        source_provider="test_prov",
        provider_external_id="ext_act_2",
        full_name="Active Unissued Player",
        is_tradable=True,
    )
    db_session.add(player_unissued)
    db_session.flush()

    assert resolve_player_lifecycle_status(player_unissued) == ("active_not_tradable", "Active / Not Tradable")

    # 4. Inactive / Retired
    player_retired = Player(
        id="player_ret_1",
        source_provider="test_prov",
        provider_external_id="ext_ret_1",
        full_name="Retired Legend",
        is_tradable=False,
        dna_profile={"retired": True},
    )
    db_session.add(player_retired)
    db_session.flush()

    assert resolve_player_lifecycle_status(player_retired) == ("inactive_retired", "Inactive / Retired")


def test_sync_player_lifecycle_and_market_status(db_session: Session) -> None:
    player = Player(
        id="player_sync_1",
        source_provider="test_prov",
        provider_external_id="ext_sync_1",
        full_name="Sync Test Player",
        is_tradable=True,
    )
    market = PlayerShareMarket(
        id="market_sync_1",
        player_id=player.id,
        status="active",
        total_shares=1000,
        circulating_shares=100,
        share_price_coin=Decimal("5.0000"),
        metadata_json={"market_issued": True},
    )
    player.share_market = market
    db_session.add_all([player, market])
    db_session.flush()

    # Verify market integrity initially
    integrity_service = PlayerShareMarketIntegrityService(session=db_session)
    issues_before = integrity_service.inspect_market(market)
    assert not any(i.code == "ineligible_active_market" for i in issues_before)

    # Retire the player
    sync_player_lifecycle_and_market_status(db_session, player, is_retired=True)
    db_session.flush()

    assert player.is_tradable is False
    assert player.dna_profile.get("retired") is True
    assert market.status == "inactive"

    # Verify market integrity after retirement sync
    issues_after = integrity_service.inspect_market(market)
    assert not any(i.code == "ineligible_active_market" for i in issues_after)


def test_retired_player_holdings_preserved_and_trading_blocked(db_session: Session) -> None:
    user = User(
        id="user_hold_1",
        email="trader@gtex.io",
        username="trader1",
        password_hash="mock_hash_123",  # pragma: allowlist secret
    )
    player = Player(
        id="player_hold_1",
        source_provider="test_prov",
        provider_external_id="ext_hold_1",
        full_name="Preserved Holdings Player",
        is_tradable=True,
    )
    market = PlayerShareMarket(
        id="market_hold_1",
        player_id=player.id,
        status="active",
        total_shares=1000,
        circulating_shares=50,
        share_price_coin=Decimal("12.5000"),
        metadata_json={"market_issued": True},
    )
    holding = PlayerShareHolding(
        id="holding_1",
        user_id=user.id,
        player_id=player.id,
        share_count=50,
        average_cost_coin=Decimal("10.0000"),
    )
    db_session.add_all([user, player, market, holding])
    db_session.flush()

    # Verify initial holding
    saved_holding = db_session.scalar(select(PlayerShareHolding).where(PlayerShareHolding.id == "holding_1"))
    assert saved_holding is not None
    assert saved_holding.share_count == 50

    # Retire player
    sync_player_lifecycle_and_market_status(db_session, player, is_retired=True)
    db_session.flush()

    # User holdings must remain intact
    saved_holding_after = db_session.scalar(select(PlayerShareHolding).where(PlayerShareHolding.id == "holding_1"))
    assert saved_holding_after is not None
    assert saved_holding_after.share_count == 50

    # Trading on retired player must raise error
    token_service = PlayerTokenMarketService(db_session)
    with pytest.raises(PlayerTokenMarketError) as exc_info:
        token_service.buy_shares(actor=user, player_id=player.id, share_count=10)
    assert exc_info.value.reason in ("share_market_ineligible", "market_ineligible", "market_inactive")
