from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PlayerExecution:
    execution_id: str
    player_id: str
    price: float
    quantity: float
    seller_user_id: str | None
    buyer_user_id: str | None
    occurred_at: datetime
    source: str


@dataclass(frozen=True, slots=True)
class PlayerPricingSnapshot:
    player_id: str
    symbol: str | None
    last_price: float | None
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    mid_price: float | None
    reference_price: float | None
    market_price: float | None
    day_change: float
    day_change_percent: float
    volume_24h: float
    last_trade_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PricingHistoryPoint:
    player_id: str
    timestamp: datetime
    price: float
    volume: float
    last_price: float | None
    best_bid: float | None
    best_ask: float | None
    mid_price: float | None
    reference_price: float | None
    event_name: str


@dataclass(frozen=True, slots=True)
class MarketCandle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class CandleSeries:
    player_id: str
    interval: str
    candles: tuple[MarketCandle, ...]


@dataclass(frozen=True, slots=True)
class MarketMoverItem:
    player_id: str
    player_name: str
    symbol: str | None
    last_price: float | None
    day_change: float
    day_change_percent: float
    volume_24h: float
    trend_score: float | None = None


@dataclass(frozen=True, slots=True)
class MarketMovers:
    top_gainers: tuple[MarketMoverItem, ...]
    top_losers: tuple[MarketMoverItem, ...]
    most_traded: tuple[MarketMoverItem, ...]
    trending: tuple[MarketMoverItem, ...]
