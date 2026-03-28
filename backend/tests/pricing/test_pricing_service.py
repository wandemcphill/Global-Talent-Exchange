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
    monkeypatch.setattr(
        cold_service,
        "_build_snapshot",
        lambda **_kwargs: pytest.fail("expected cached player snapshot lookup"),
    )

    cached_snapshot = cold_service.get_snapshot(
        player_id="player-1",
        reference_price=220.0,
        symbol="A. Striker",
    )

    assert cached_snapshot.player_id == "player-1"
    assert cached_snapshot.market_price == snapshot.market_price
    assert cache_backend.values["player:player-1:price"] == str(snapshot.market_price)
