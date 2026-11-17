from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import Event as ThreadEvent
from time import monotonic, sleep
from uuid import uuid4

from app.backbone.redis_fanout import HybridEventPublisher
from app.core.config import Settings, get_settings
from app.core.database import DatabaseRuntime
from app.core.events import InMemoryEventPublisher
from app.gtex import redis_keys
from app.gtex.runtime import build_gtex_runtime

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkerContext:
    database: DatabaseRuntime
    runtime: object
    event_publisher: object

    def shutdown(self) -> None:
        if hasattr(self.event_publisher, "close"):
            self.event_publisher.close()


def build_worker_context(
    *,
    settings: Settings | None = None,
    database: DatabaseRuntime | None = None,
    run_migration_check: bool | None = None,
    seed_defaults: bool = True,
) -> WorkerContext:
    """Build a GTEX worker context, reusing a pre-initialized DatabaseRuntime when provided."""
    resolved_settings = settings or get_settings()
    resolved_database = database or DatabaseRuntime.build(settings=resolved_settings)
    should_check_migrations = (
        resolved_settings.run_migration_check if run_migration_check is None else run_migration_check
    )
    if database is None or should_check_migrations:
        resolved_database.initialize(run_migration_check=should_check_migrations)
    if resolved_settings.redis_url:
        event_publisher = HybridEventPublisher(
            redis_url=resolved_settings.redis_url,
            redis_channel=resolved_settings.redis_event_channel,
        )
        event_publisher.start()
    else:
        event_publisher = InMemoryEventPublisher()
    runtime = build_gtex_runtime(
        app_settings=resolved_settings,
        session_factory=resolved_database.session_factory,
        event_publisher=event_publisher,
        redis_url=resolved_settings.redis_url,
        realtime_channel=resolved_settings.redis_realtime_channel,
    )
    if seed_defaults:
        with resolved_database.session_factory() as session:
            runtime.jackpot.ensure_open_round(session)
            runtime.ai_leagues.seed_defaults(session)
            runtime.universe.seed_defaults(session)
            session.commit()
    return WorkerContext(database=resolved_database, runtime=runtime, event_publisher=event_publisher)


@dataclass(slots=True)
class JackpotWorker:
    context: WorkerContext
    consumer_name: str = field(default_factory=lambda: f"jackpot-{uuid4().hex[:8]}")

    def run_once(self) -> bool:
        messages = self.context.runtime.state_store.consume(
            redis_keys.stream_jackpot(),
            group="gtex-jackpot",
            consumer=self.consumer_name,
            count=1,
            block_ms=int(self.context.runtime.settings.worker_poll_interval_seconds * 1000),
        )
        with self.context.runtime.state_store.distributed_lock("gtex:jackpot:trigger_lock", ttl_seconds=30) as acquired:
            if not acquired:
                return False
            processed = False
            # Jackpot pools are isolated by currency. Process both the existing
            # GTEX Coin pool and the FanCoin pool so neither can remain stranded.
            for pool_key in ("global", "fancoin"):
                with self.context.database.session_factory() as session:
                    result = self.context.runtime.jackpot.process_due_round(session, pool_key=pool_key)
                    session.commit()
                    processed = processed or result is not None
            for message in messages:
                self.context.runtime.state_store.ack(message.stream, "gtex-jackpot", message.message_id)
            return processed


@dataclass(slots=True)
class ValuationWorker:
    context: WorkerContext
    consumer_name: str = field(default_factory=lambda: f"valuation-{uuid4().hex[:8]}")

    def run_once(self) -> int:
        handled = 0
        messages = self.context.runtime.state_store.consume(
            redis_keys.stream_valuation(),
            group="gtex-valuation",
            consumer=self.consumer_name,
            count=20,
            block_ms=int(self.context.runtime.settings.worker_poll_interval_seconds * 1000),
        )
        for message in messages:
            with self.context.database.session_factory() as session:
                self.context.runtime.creator_market.recalculate_asset_price(
                    session,
                    player_id=str(message.payload.get("player_id") or ""),
                    reason=str(message.payload.get("reason") or "valuation_worker"),
                )
                session.commit()
            self.context.runtime.state_store.ack(message.stream, "gtex-valuation", message.message_id)
            handled += 1
        return handled


@dataclass(slots=True)
class AiMatchmakerWorker:
    context: WorkerContext
    consumer_name: str = field(default_factory=lambda: f"matchmaker-{uuid4().hex[:8]}")

    def run_once(self) -> int:
        handled = 0
        messages = self.context.runtime.state_store.consume(
            redis_keys.stream_matchmaking(),
            group="gtex-matchmaking",
            consumer=self.consumer_name,
            count=20,
            block_ms=int(self.context.runtime.settings.worker_poll_interval_seconds * 1000),
        )
        for message in messages:
            with self.context.database.session_factory() as session:
                self.context.runtime.ai_leagues.process_matchmaking(
                    session,
                    queue_entry_id=str(message.payload.get("queue_entry_id") or ""),
                )
                session.commit()
            self.context.runtime.state_store.ack(message.stream, "gtex-matchmaking", message.message_id)
            handled += 1
        return handled


@dataclass(slots=True)
class AiBrainWorker:
    context: WorkerContext
    consumer_name: str = field(default_factory=lambda: f"ai-brain-{uuid4().hex[:8]}")

    def run_once(self) -> int:
        handled = 0
        messages = self.context.runtime.state_store.consume(
            redis_keys.stream_ai_brain(),
            group="gtex-ai-brain",
            consumer=self.consumer_name,
            count=20,
            block_ms=int(self.context.runtime.settings.worker_poll_interval_seconds * 1000),
        )
        for message in messages:
            with self.context.database.session_factory() as session:
                self.context.runtime.ai_leagues.simulate_match(
                    session,
                    match_id=str(message.payload.get("match_id") or ""),
                )
                session.commit()
            self.context.runtime.state_store.ack(message.stream, "gtex-ai-brain", message.message_id)
            handled += 1
        return handled


def _expire_coin_trade_orders(worker) -> None:
    now = monotonic()
    if now - getattr(_expire_coin_trade_orders, "last_run", 0.0) < 30:
        return
    _expire_coin_trade_orders.last_run = now  # type: ignore[attr-defined]
    try:
        from app.coin_traders.service import CoinTraderService

        with worker.context.database.session_factory() as session:
            CoinTraderService(session).expire_stale_orders()
    except Exception:
        logger.exception("gtex.worker.coin_trade_expiry_failed")


def _run_forever(worker) -> None:
    stop_event = ThreadEvent()
    try:
        while not stop_event.is_set():
            worker.run_once()
            _expire_coin_trade_orders(worker)
            sleep(worker.context.runtime.settings.worker_poll_interval_seconds)
    finally:
        worker.context.shutdown()


def _run_worker(
    worker_cls,
    *,
    context: WorkerContext | None = None,
    database: DatabaseRuntime | None = None,
    run_migration_check: bool | None = None,
    seed_defaults: bool = True,
) -> None:
    resolved_context = context or build_worker_context(
        database=database,
        run_migration_check=run_migration_check,
        seed_defaults=seed_defaults,
    )
    _run_forever(worker_cls(context=resolved_context))


def run_jackpot_worker(
    *,
    context: WorkerContext | None = None,
    database: DatabaseRuntime | None = None,
    run_migration_check: bool | None = None,
    seed_defaults: bool = True,
) -> None:
    _run_worker(
        JackpotWorker,
        context=context,
        database=database,
        run_migration_check=run_migration_check,
        seed_defaults=seed_defaults,
    )


def run_valuation_worker(
    *,
    context: WorkerContext | None = None,
    database: DatabaseRuntime | None = None,
    run_migration_check: bool | None = None,
    seed_defaults: bool = True,
) -> None:
    _run_worker(
        ValuationWorker,
        context=context,
        database=database,
        run_migration_check=run_migration_check,
        seed_defaults=seed_defaults,
    )


def run_ai_matchmaker_worker(
    *,
    context: WorkerContext | None = None,
    database: DatabaseRuntime | None = None,
    run_migration_check: bool | None = None,
    seed_defaults: bool = True,
) -> None:
    _run_worker(
        AiMatchmakerWorker,
        context=context,
        database=database,
        run_migration_check=run_migration_check,
        seed_defaults=seed_defaults,
    )


def run_ai_brain_worker(
    *,
    context: WorkerContext | None = None,
    database: DatabaseRuntime | None = None,
    run_migration_check: bool | None = None,
    seed_defaults: bool = True,
) -> None:
    _run_worker(
        AiBrainWorker,
        context=context,
        database=database,
        run_migration_check=run_migration_check,
        seed_defaults=seed_defaults,
    )
