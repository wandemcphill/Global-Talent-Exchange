from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MarketTickerView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="MarketTickerView",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "symbol": "A. Striker",
                "last_price": 120.0,
                "best_bid": 118.0,
                "best_ask": 122.0,
                "spread": 4.0,
                "mid_price": 120.0,
                "reference_price": 119.5,
                "day_change": 5.0,
                "day_change_percent": 4.3478,
                "volume_24h": 3.0,
            }
        },
    )

    player_id: str
    symbol: str | None = None
    last_price: float | None = None
    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    mid_price: float | None = None
    reference_price: float | None = None
    day_change: float = 0.0
    day_change_percent: float = 0.0
    volume_24h: float = 0.0


class MarketCandleView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="MarketCandleView",
        json_schema_extra={
            "example": {
                "timestamp": "2026-03-11T11:00:00Z",
                "open": 118.0,
                "high": 122.0,
                "low": 117.5,
                "close": 120.0,
                "volume": 2.0,
            }
        },
    )

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketCandlesView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="MarketCandlesView",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "interval": "1h",
                "candles": [
                    {
                        "timestamp": "2026-03-11T11:00:00Z",
                        "open": 118.0,
                        "high": 122.0,
                        "low": 117.5,
                        "close": 120.0,
                        "volume": 2.0,
                    }
                ],
            }
        },
    )

    player_id: str
    interval: str
    candles: list[MarketCandleView]


class MarketMoverItemView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="MarketMoverItemView",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "player_name": "Ayo Striker",
                "symbol": "A. Striker",
                "last_price": 120.0,
                "day_change": 5.0,
                "day_change_percent": 4.3478,
                "volume_24h": 3.0,
                "trend_score": 84.0,
            }
        },
    )

    player_id: str
    player_name: str
    symbol: str | None = None
    last_price: float | None = None
    day_change: float = 0.0
    day_change_percent: float = 0.0
    volume_24h: float = 0.0
    trend_score: float | None = None


class MarketMoversView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="MarketMoversView",
        json_schema_extra={
            "example": {
                "top_gainers": [
                    {
                        "player_id": "player-123",
                        "player_name": "Ayo Striker",
                        "symbol": "A. Striker",
                        "last_price": 120.0,
                        "day_change": 5.0,
                        "day_change_percent": 4.3478,
                        "volume_24h": 3.0,
                        "trend_score": 84.0,
                    }
                ],
                "top_losers": [],
                "most_traded": [],
                "trending": [],
            }
        },
    )

    top_gainers: list[MarketMoverItemView] = Field(default_factory=list)
    top_losers: list[MarketMoverItemView] = Field(default_factory=list)
    most_traded: list[MarketMoverItemView] = Field(default_factory=list)
    trending: list[MarketMoverItemView] = Field(default_factory=list)
