from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ingestion.models import Player
from backend.app.market.models import (
    Listing,
    ListingStatus,
    Offer,
    OfferStatus,
    TradeIntent,
    TradeIntentDirection,
    TradeIntentStatus,
)
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.pricing.models import (
    CandleSeries,
    MarketCandle,
    PlayerExecution,
    PlayerPricingSnapshot,
    PricingHistoryPoint,
)
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord
from backend.app.value_engine.scoring import credits_from_real_world_value

SUPPORTED_CANDLE_INTERVALS: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


class PricingValidationError(ValueError):
    pass


@dataclass(slots=True)
class MarketPricingService:
    session_factory: sessionmaker[Session] | None = None
    _snapshots: dict[str, PlayerPricingSnapshot] = field(default_factory=dict)
    _executions: dict[str, list[PlayerExecution]] = field(default_factory=lambda: defaultdict(list))
    _history: dict[str, list[PricingHistoryPoint]] = field(default_factory=lambda: defaultdict(list))
    _lock: RLock = field(default_factory=RLock)

    def record_execution(
        self,
        *,
        player_id: str,
        price: float,
        quantity: float = 1.0,
        seller_user_id: str | None = None,
        buyer_user_id: str | None = None,
        occurred_at: datetime | None = None,
        source: str = "execution",
    ) -> PlayerExecution:
        if price <= 0:
            raise PricingValidationError("execution price must be positive")
        if quantity <= 0:
            raise PricingValidationError("execution quantity must be positive")

        execution = PlayerExecution(
            execution_id=f"exe_{uuid4().hex[:12]}",
            player_id=player_id,
            price=round(float(price), 2),
            quantity=round(float(quantity), 4),
            seller_user_id=seller_user_id,
            buyer_user_id=buyer_user_id,
            occurred_at=self._normalize_timestamp(occurred_at),
            source=source,
        )
        with self._lock:
            self._executions[player_id].append(execution)
            self._executions[player_id].sort(key=lambda item: (item.occurred_at, item.execution_id))
        return execution

    def refresh_player_snapshot(
        self,
        *,
        player_id: str,
        listings: tuple[Listing, ...] = (),
        offers: tuple[Offer, ...] = (),
        trade_intents: tuple[TradeIntent, ...] = (),
        occurred_at: datetime | None = None,
        event_name: str = "market.pricing.updated",
        execution: PlayerExecution | None = None,
        reference_price: float | None = None,
        symbol: str | None = None,
    ) -> PlayerPricingSnapshot:
        snapshot = self._build_snapshot(
            player_id=player_id,
            listings=listings,
            offers=offers,
            trade_intents=trade_intents,
            occurred_at=occurred_at,
            reference_price=reference_price,
            symbol=symbol,
        )
        with self._lock:
            self._snapshots[player_id] = snapshot
            if snapshot.market_price is not None:
                self._history[player_id].append(
                    PricingHistoryPoint(
                        player_id=player_id,
                        timestamp=snapshot.updated_at,
                        price=snapshot.market_price,
                        volume=execution.quantity if execution is not None else 0.0,
                        last_price=snapshot.last_price,
                        best_bid=snapshot.best_bid,
                        best_ask=snapshot.best_ask,
                        mid_price=snapshot.mid_price,
                        reference_price=snapshot.reference_price,
                        event_name=event_name,
                    )
                )
                self._history[player_id].sort(key=lambda item: item.timestamp)
        return snapshot

    def get_snapshot(
        self,
        *,
        player_id: str,
        listings: tuple[Listing, ...] = (),
        offers: tuple[Offer, ...] = (),
        trade_intents: tuple[TradeIntent, ...] = (),
        reference_price: float | None = None,
        symbol: str | None = None,
    ) -> PlayerPricingSnapshot:
        with self._lock:
            cached_snapshot = self._snapshots.get(player_id)
        if cached_snapshot is not None:
            return cached_snapshot
        return self._build_snapshot(
            player_id=player_id,
            listings=listings,
            offers=offers,
            trade_intents=trade_intents,
            reference_price=reference_price,
            symbol=symbol,
        )

    def get_candles(
        self,
        *,
        player_id: str,
        interval: str,
        limit: int,
        listings: tuple[Listing, ...] = (),
        offers: tuple[Offer, ...] = (),
        trade_intents: tuple[TradeIntent, ...] = (),
        reference_price: float | None = None,
        symbol: str | None = None,
    ) -> CandleSeries:
        if interval not in SUPPORTED_CANDLE_INTERVALS:
            raise PricingValidationError(
                f"unsupported candle interval '{interval}'. Expected one of: {', '.join(SUPPORTED_CANDLE_INTERVALS)}"
            )
        if limit <= 0:
            raise PricingValidationError("candle limit must be positive")

        snapshot = self.get_snapshot(
            player_id=player_id,
            listings=listings,
            offers=offers,
            trade_intents=trade_intents,
            reference_price=reference_price,
            symbol=symbol,
        )
        with self._lock:
            history = tuple(self._history.get(player_id, ()))

        if not history and snapshot.market_price is not None:
            history = (
                PricingHistoryPoint(
                    player_id=player_id,
                    timestamp=snapshot.updated_at,
                    price=snapshot.market_price,
                    volume=0.0,
                    last_price=snapshot.last_price,
                    best_bid=snapshot.best_bid,
                    best_ask=snapshot.best_ask,
                    mid_price=snapshot.mid_price,
                    reference_price=snapshot.reference_price,
                    event_name="market.pricing.synthetic",
                ),
            )

        bucket_size = SUPPORTED_CANDLE_INTERVALS[interval]
        bucketed: dict[datetime, list[PricingHistoryPoint]] = defaultdict(list)
        for point in history:
            bucketed[self._bucket_start(point.timestamp, bucket_size)].append(point)

        candles = tuple(
            MarketCandle(
                timestamp=bucket_start,
                open=round(points[0].price, 2),
                high=round(max(point.price for point in points), 2),
                low=round(min(point.price for point in points), 2),
                close=round(points[-1].price, 2),
                volume=round(sum(point.volume for point in points), 4),
            )
            for bucket_start, points in sorted(bucketed.items())
        )
        return CandleSeries(player_id=player_id, interval=interval, candles=candles[-limit:])

    def history_for_player(self, player_id: str) -> tuple[PricingHistoryPoint, ...]:
        with self._lock:
            return tuple(self._history.get(player_id, ()))

    def executions_for_player(self, player_id: str) -> tuple[PlayerExecution, ...]:
        with self._lock:
            return tuple(self._executions.get(player_id, ()))

    def _build_snapshot(
        self,
        *,
        player_id: str,
        listings: tuple[Listing, ...],
        offers: tuple[Offer, ...],
        trade_intents: tuple[TradeIntent, ...],
        occurred_at: datetime | None = None,
        reference_price: float | None = None,
        symbol: str | None = None,
    ) -> PlayerPricingSnapshot:
        timestamp = self._normalize_timestamp(occurred_at)
        reference = self._round_price(reference_price)
        resolved_symbol = symbol
        if reference is None or resolved_symbol is None:
            lookup_reference, lookup_symbol = self._load_reference_context(player_id)
            reference = reference if reference is not None else lookup_reference
            resolved_symbol = resolved_symbol if resolved_symbol is not None else lookup_symbol

        best_bid = self._best_bid(offers=offers, trade_intents=trade_intents)
        best_ask = self._best_ask(listings=listings, trade_intents=trade_intents)
        spread = round(best_ask - best_bid, 2) if best_bid is not None and best_ask is not None else None
        mid_price = round((best_bid + best_ask) / 2.0, 2) if best_bid is not None and best_ask is not None else reference
        executions = self.executions_for_player(player_id)
        last_trade = executions[-1] if executions else None
        last_price = self._round_price(last_trade.price if last_trade is not None else reference)
        market_price = self._round_price(
            mid_price
            if best_bid is not None and best_ask is not None
            else last_price or reference or best_bid or best_ask
        )
        baseline_price = self._baseline_price(player_id=player_id, as_of=timestamp, fallback_price=market_price)
        day_change = 0.0
        day_change_percent = 0.0
        if market_price is not None and baseline_price not in {None, 0}:
            day_change = round(market_price - baseline_price, 2)
            day_change_percent = round((day_change / baseline_price) * 100.0, 4)
        volume_24h = round(
            sum(
                execution.quantity
                for execution in executions
                if execution.occurred_at >= timestamp - timedelta(hours=24)
            ),
            4,
        )
        return PlayerPricingSnapshot(
            player_id=player_id,
            symbol=resolved_symbol,
            last_price=last_price,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            mid_price=mid_price,
            reference_price=reference,
            market_price=market_price,
            day_change=day_change,
            day_change_percent=day_change_percent,
            volume_24h=volume_24h,
            last_trade_at=last_trade.occurred_at if last_trade is not None else None,
            updated_at=timestamp,
        )

    def _best_bid(self, *, offers: tuple[Offer, ...], trade_intents: tuple[TradeIntent, ...]) -> float | None:
        bid_candidates = [
            float(offer.cash_amount)
            for offer in offers
            if offer.status == OfferStatus.PENDING and offer.cash_amount > 0
        ]
        bid_candidates.extend(
            float(intent.price_ceiling)
            for intent in trade_intents
            if (
                intent.status == TradeIntentStatus.ACTIVE
                and intent.direction in {TradeIntentDirection.BUY, TradeIntentDirection.SWAP}
                and intent.price_ceiling is not None
            )
        )
        return self._round_price(max(bid_candidates)) if bid_candidates else None

    def _best_ask(self, *, listings: tuple[Listing, ...], trade_intents: tuple[TradeIntent, ...]) -> float | None:
        ask_candidates = [
            float(listing.ask_price)
            for listing in listings
            if listing.status == ListingStatus.OPEN and listing.ask_price is not None and listing.ask_price > 0
        ]
        ask_candidates.extend(
            float(intent.price_floor)
            for intent in trade_intents
            if (
                intent.status == TradeIntentStatus.ACTIVE
                and intent.direction in {TradeIntentDirection.SELL, TradeIntentDirection.SWAP}
                and intent.price_floor is not None
            )
        )
        return self._round_price(min(ask_candidates)) if ask_candidates else None

    def _baseline_price(
        self,
        *,
        player_id: str,
        as_of: datetime,
        fallback_price: float | None,
    ) -> float | None:
        with self._lock:
            history = tuple(self._history.get(player_id, ()))
        if not history:
            return fallback_price

        cutoff = as_of - timedelta(hours=24)
        at_or_before_cutoff = [point.price for point in history if point.timestamp <= cutoff]
        if at_or_before_cutoff:
            return at_or_before_cutoff[-1]
        return history[0].price if history else fallback_price

    def _load_reference_context(self, player_id: str) -> tuple[float | None, str | None]:
        if self.session_factory is None:
            return None, None

        with self.session_factory() as session:
            player = session.get(Player, player_id)
            if player is None:
                return None, None

            latest_snapshot = session.scalar(
                select(PlayerValueSnapshotRecord)
                .where(PlayerValueSnapshotRecord.player_id == player_id)
                .order_by(
                    PlayerValueSnapshotRecord.as_of.desc(),
                    PlayerValueSnapshotRecord.created_at.desc(),
                    PlayerValueSnapshotRecord.id.desc(),
                )
            )
            summary = session.get(PlayerSummaryReadModel, player_id)

        reference_candidates: tuple[float | None, ...] = (
            self._coerce_float(
                (latest_snapshot.breakdown_json or {}).get("published_card_value_credits")
                if latest_snapshot is not None
                else None
            ),
            self._coerce_float(latest_snapshot.target_credits if latest_snapshot is not None else None),
            self._coerce_float(summary.current_value_credits if summary is not None else None),
            self._coerce_float(
                credits_from_real_world_value(player.market_value_eur)
                if player.market_value_eur is not None
                else None
            ),
        )
        for candidate in reference_candidates:
            if candidate is not None and candidate > 0:
                return round(candidate, 2), player.short_name
        return None, player.short_name

    def _bucket_start(self, timestamp: datetime, bucket_size: timedelta) -> datetime:
        normalized = self._normalize_timestamp(timestamp)
        bucket_seconds = int(bucket_size.total_seconds())
        epoch_seconds = int(normalized.timestamp())
        bucket_epoch = epoch_seconds - (epoch_seconds % bucket_seconds)
        return datetime.fromtimestamp(bucket_epoch, tz=UTC)

    def _normalize_timestamp(self, value: datetime | None) -> datetime:
        candidate = value or datetime.now(UTC)
        if candidate.tzinfo is None:
            return candidate.replace(tzinfo=UTC)
        return candidate.astimezone(UTC)

    def _round_price(self, value: float | None) -> float | None:
        if value is None:
            return None
        return round(float(value), 2)

    def _coerce_float(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
