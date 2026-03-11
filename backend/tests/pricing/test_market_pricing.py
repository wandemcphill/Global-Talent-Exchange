from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.ingestion.models  # noqa: F401
import backend.app.market.read_models  # noqa: F401
import backend.app.players.read_models  # noqa: F401
import backend.app.value_engine.read_models  # noqa: F401
from backend.app.auth.dependencies import get_session
from backend.app.ingestion.models import Player
from backend.app.market.projections import MarketSummaryProjector
from backend.app.market.router import router
from backend.app.market.service import MarketEngine
from backend.app.models.base import Base
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord


@pytest.fixture()
def pricing_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    app = FastAPI()
    app.include_router(router)
    app.state.session_factory = SessionLocal
    app.state.market_engine = MarketEngine(summary_projector=MarketSummaryProjector(SessionLocal))

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session

    _seed_players(session)

    with TestClient(app) as client:
        yield client, session, app.state.market_engine

    session.close()


def _seed_players(session) -> None:
    players = [
        Player(
            id="player-1",
            source_provider="synthetic",
            provider_external_id="player-1",
            full_name="Ayo Striker",
            short_name="A. Striker",
            is_tradable=True,
            market_value_eur=12_000_000.0,
        ),
        Player(
            id="player-2",
            source_provider="synthetic",
            provider_external_id="player-2",
            full_name="Bola Midfield",
            short_name="B. Midfield",
            is_tradable=True,
            market_value_eur=9_000_000.0,
        ),
        Player(
            id="player-3",
            source_provider="synthetic",
            provider_external_id="player-3",
            full_name="Carlos Keeper",
            short_name="C. Keeper",
            is_tradable=True,
            market_value_eur=15_000_000.0,
        ),
        Player(
            id="player-4",
            source_provider="synthetic",
            provider_external_id="player-4",
            full_name="Diego Defender",
            short_name="D. Defender",
            is_tradable=True,
            market_value_eur=6_000_000.0,
        ),
    ]
    session.add_all(players)

    snapshot_time = datetime(2026, 3, 10, 9, 0, tzinfo=UTC)
    summaries = [
        PlayerSummaryReadModel(
            player_id="player-1",
            player_name="Ayo Striker",
            last_snapshot_id="snapshot-1",
            last_snapshot_at=snapshot_time,
            current_value_credits=120.0,
            previous_value_credits=110.0,
            movement_pct=9.09,
            market_interest_score=72,
            average_rating=7.4,
            summary_json={"published_card_value_credits": 120.0, "global_scouting_index": 84.0},
        ),
        PlayerSummaryReadModel(
            player_id="player-2",
            player_name="Bola Midfield",
            last_snapshot_id="snapshot-2",
            last_snapshot_at=snapshot_time,
            current_value_credits=90.0,
            previous_value_credits=100.0,
            movement_pct=-10.0,
            market_interest_score=65,
            average_rating=7.2,
            summary_json={"published_card_value_credits": 90.0, "global_scouting_index": 79.0},
        ),
        PlayerSummaryReadModel(
            player_id="player-3",
            player_name="Carlos Keeper",
            last_snapshot_id="snapshot-3",
            last_snapshot_at=snapshot_time,
            current_value_credits=150.0,
            previous_value_credits=145.0,
            movement_pct=3.45,
            market_interest_score=40,
            average_rating=6.9,
            summary_json={"published_card_value_credits": 150.0, "global_scouting_index": 70.0},
        ),
        PlayerSummaryReadModel(
            player_id="player-4",
            player_name="Diego Defender",
            last_snapshot_id="snapshot-4",
            last_snapshot_at=snapshot_time,
            current_value_credits=60.0,
            previous_value_credits=60.0,
            movement_pct=0.0,
            market_interest_score=52,
            average_rating=7.0,
            summary_json={"published_card_value_credits": 60.0, "global_scouting_index": 74.0},
        ),
    ]
    session.add_all(summaries)

    snapshots = [
        PlayerValueSnapshotRecord(
            id="snapshot-1",
            player_id="player-1",
            player_name="Ayo Striker",
            as_of=snapshot_time,
            previous_credits=110.0,
            target_credits=120.0,
            movement_pct=9.09,
            football_truth_value_credits=118.0,
            market_signal_value_credits=2.0,
            breakdown_json={"published_card_value_credits": 120.0},
            drivers_json=["finishing"],
        ),
        PlayerValueSnapshotRecord(
            id="snapshot-2",
            player_id="player-2",
            player_name="Bola Midfield",
            as_of=snapshot_time,
            previous_credits=100.0,
            target_credits=90.0,
            movement_pct=-10.0,
            football_truth_value_credits=88.0,
            market_signal_value_credits=2.0,
            breakdown_json={"published_card_value_credits": 90.0},
            drivers_json=["control"],
        ),
        PlayerValueSnapshotRecord(
            id="snapshot-3",
            player_id="player-3",
            player_name="Carlos Keeper",
            as_of=snapshot_time,
            previous_credits=145.0,
            target_credits=150.0,
            movement_pct=3.45,
            football_truth_value_credits=147.0,
            market_signal_value_credits=3.0,
            breakdown_json={"published_card_value_credits": 150.0},
            drivers_json=["shot stopping"],
        ),
        PlayerValueSnapshotRecord(
            id="snapshot-4",
            player_id="player-4",
            player_name="Diego Defender",
            as_of=snapshot_time,
            previous_credits=60.0,
            target_credits=60.0,
            movement_pct=0.0,
            football_truth_value_credits=59.0,
            market_signal_value_credits=1.0,
            breakdown_json={"published_card_value_credits": 60.0},
            drivers_json=["positioning"],
        ),
    ]
    session.add_all(snapshots)
    session.commit()


def test_ticker_falls_back_to_reference_price_when_no_trades_exist(pricing_api) -> None:
    client, _session, _market_engine = pricing_api

    response = client.get("/api/market/ticker/player-1")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "player_id",
        "symbol",
        "last_price",
        "best_bid",
        "best_ask",
        "spread",
        "mid_price",
        "reference_price",
        "day_change",
        "day_change_percent",
        "volume_24h",
    }
    assert payload["player_id"] == "player-1"
    assert payload["symbol"] == "A. Striker"
    assert payload["last_price"] == 120.0
    assert payload["reference_price"] == 120.0
    assert payload["best_bid"] is None
    assert payload["best_ask"] is None
    assert payload["mid_price"] == 120.0
    assert payload["day_change"] == 0.0
    assert payload["day_change_percent"] == 0.0


def test_ticker_updates_after_execution(pricing_api) -> None:
    client, _session, market_engine = pricing_api

    listing = market_engine.create_listing(
        asset_id="player-1",
        seller_user_id="seller-1",
        listing_type="transfer",
        ask_price=130,
    )
    offer = market_engine.create_offer(
        asset_id="player-1",
        seller_user_id="seller-1",
        buyer_user_id="buyer-1",
        cash_amount=135,
        listing_id=listing.listing_id,
    )
    market_engine.accept_offer(offer_id=offer.offer_id, acting_user_id="seller-1")

    response = client.get("/api/market/ticker/player-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_price"] == 135.0
    assert payload["volume_24h"] == 1.0


def test_spread_and_mid_price_are_computed_from_open_book(pricing_api) -> None:
    client, _session, market_engine = pricing_api

    market_engine.create_listing(
        asset_id="player-2",
        seller_user_id="seller-2",
        listing_type="transfer",
        ask_price=110,
    )
    market_engine.create_trade_intent(
        user_id="buyer-2",
        asset_id="player-2",
        direction="buy",
        price_ceiling=100,
    )

    response = client.get("/api/market/ticker/player-2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["best_bid"] == 100.0
    assert payload["best_ask"] == 110.0
    assert payload["spread"] == 10.0
    assert payload["mid_price"] == 105.0


def test_candles_endpoint_returns_valid_sparse_series(pricing_api) -> None:
    client, _session, _market_engine = pricing_api

    response = client.get("/api/market/players/player-3/candles", params={"interval": "1h", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["player_id"] == "player-3"
    assert payload["interval"] == "1h"
    assert isinstance(payload["candles"], list)
    assert len(payload["candles"]) == 1
    candle = payload["candles"][0]
    assert set(candle) == {"timestamp", "open", "high", "low", "close", "volume"}
    assert candle["open"] == 150.0
    assert candle["high"] == 150.0
    assert candle["low"] == 150.0
    assert candle["close"] == 150.0
    assert candle["volume"] == 0.0


def test_day_change_uses_rolling_24h_baseline(pricing_api) -> None:
    client, _session, market_engine = pricing_api

    market_engine.record_execution(
        asset_id="player-4",
        price=60.0,
        occurred_at=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
        seller_user_id="seller-4",
        buyer_user_id="buyer-4a",
    )
    market_engine.record_execution(
        asset_id="player-4",
        price=75.0,
        occurred_at=datetime(2026, 3, 11, 11, 0, tzinfo=UTC),
        seller_user_id="seller-4",
        buyer_user_id="buyer-4b",
    )

    response = client.get("/api/market/ticker/player-4")

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_price"] == 75.0
    assert payload["day_change"] == 15.0
    assert payload["day_change_percent"] == 25.0
    assert payload["volume_24h"] == 1.0


def test_movers_endpoint_returns_stable_buckets(pricing_api) -> None:
    client, _session, market_engine = pricing_api

    market_engine.record_execution(
        asset_id="player-1",
        price=100.0,
        occurred_at=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
    )
    market_engine.record_execution(
        asset_id="player-1",
        price=130.0,
        occurred_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
    )
    market_engine.record_execution(
        asset_id="player-2",
        price=100.0,
        occurred_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
    )
    market_engine.record_execution(
        asset_id="player-2",
        price=80.0,
        occurred_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
    )
    market_engine.record_execution(
        asset_id="player-3",
        price=150.0,
        occurred_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
    )
    market_engine.record_execution(
        asset_id="player-3",
        price=151.0,
        occurred_at=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
    )
    market_engine.record_execution(
        asset_id="player-3",
        price=152.0,
        occurred_at=datetime(2026, 3, 11, 11, 0, tzinfo=UTC),
    )

    response = client.get("/api/market/movers", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"top_gainers", "top_losers", "most_traded", "trending"}
    assert len(payload["top_gainers"]) == 2
    assert len(payload["top_losers"]) == 2
    assert len(payload["most_traded"]) == 2
    assert len(payload["trending"]) == 2
    expected_item_shape = {
        "player_id",
        "player_name",
        "symbol",
        "last_price",
        "day_change",
        "day_change_percent",
        "volume_24h",
        "trend_score",
    }
    assert set(payload["top_gainers"][0]) == expected_item_shape
    assert set(payload["top_losers"][0]) == expected_item_shape
    assert set(payload["most_traded"][0]) == expected_item_shape
    assert payload["top_gainers"][0]["player_id"] == "player-1"
    assert payload["top_losers"][0]["player_id"] == "player-2"
    assert payload["most_traded"][0]["player_id"] == "player-3"
    assert set(payload["trending"][0]) == expected_item_shape
