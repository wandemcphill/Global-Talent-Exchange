from __future__ import annotations

import pytest

from app.pricing.service import MarketPricingService


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


def test_market_pricing_service_uses_cached_snapshot(monkeypatch) -> None:
    cache_backend = FakeCacheBackend()
    warm_service = MarketPricingService(cache_backend=cache_backend)
    snapshot = warm_service.refresh_player_snapshot(
        player_id="player-1",
        reference_price=220.0,
        symbol="A. Striker",
    )

    cold_service = MarketPricingService(cache_backend=cache_backend)

    def fail_snapshot_build(self, **_kwargs):
        if self is cold_service:
            pytest.fail("expected cached player snapshot lookup")

    monkeypatch.setattr(MarketPricingService, "_build_snapshot", fail_snapshot_build)

    cached_snapshot = cold_service.get_snapshot(
        player_id="player-1",
        reference_price=220.0,
        symbol="A. Striker",
    )

    assert cached_snapshot.player_id == "player-1"
    assert cached_snapshot.market_price == snapshot.market_price
    assert cache_backend.values["player:player-1:price"] == str(snapshot.market_price)


def test_market_pricing_candles_do_not_synthesize_history_from_snapshot_only() -> None:
    service = MarketPricingService()

    candles = service.get_candles(
        player_id="player-1",
        interval="1m",
        limit=10,
        reference_price=220.0,
        symbol="A. Striker",
    )

    assert candles.candles == ()
    assert service.history_for_player("player-1") == ()
