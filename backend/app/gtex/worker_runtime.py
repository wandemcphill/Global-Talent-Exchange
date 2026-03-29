from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event as ThreadEvent
from time import sleep
from uuid import uuid4

from app.backbone.redis_fanout import HybridEventPublisher
from app.core.config import get_settings
from app.core.database import DatabaseRuntime
from app.core.events import InMemoryEventPublisher
from app.gtex import redis_keys
from app.gtex.runtime import build_gtex_runtime


@dataclass(slots=True)
class WorkerContext:
    database: DatabaseRuntime
    runtime: object
    event_publisher: object

    def shutdown(self) -> None:
        if hasattr(self.event_publisher, "close"):
            self.event_publisher.close()


def build_worker_context() -> WorkerContext:
    settings = get_settings()
    database = DatabaseRuntime.build(settings=settings)
    database.initialize(run_migration_check=settings.run_migration_check)
    if settings.redis_url:
        event_publisher = HybridEventPublisher(redis_url=settings.redis_url, redis_channel=settings.redis_event_channel)
        event_publisher.start()
    else:
        event_publisher = InMemoryEventPublisher()
    runtime = build_gtex_runtime(
        app_settings=settings,
        session_factory=database.session_factory,
        event_publisher=event_publisher,
        redis_url=settings.redis_url,
        realtime_channel=settings.redis_realtime_channel,
    )
    with database.session_factory() as session:
        runtime.jackpot.ensure_open_round(session)
        runtime.ai_leagues.seed_defaults(session)
        session.commit()
    return WorkerContext(database=database, runtime=runtime, event_publisher=event_publisher)


@dataclass(slots=True)
class JackpotWorker:
    context: WorkerContext
    consumer_name: str = field(default_factory=lambda: f"jackpot-{uuid4().hex[:8]}")

    def run_once(self) -> bool:
        self.context.runtime.state_store.consume(
            redis_keys.stream_jackpot(),
            group="gtex-jackpot",
            consumer=self.consumer_name,
            count=1,
            block_ms=int(self.context.runtime.settings.worker_poll_interval_seconds * 1000),
        )
        with self.context.runtime.state_store.distributed_lock("gtex:jackpot:trigger_lock", ttl_seconds=30) as acquired:
            if not acquired:
                return False
            with self.context.database.session_factory() as session:
                result = self.context.runtime.jackpot.process_due_round(session)
                session.commit()
                return result is not None


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


def _run_forever(worker) -> None:
    stop_event = ThreadEvent()
    try:
        while not stop_event.is_set():
            worker.run_once()
            sleep(worker.context.runtime.settings.worker_poll_interval_seconds)
    finally:
        worker.context.shutdown()


def run_jackpot_worker() -> None:
    _run_forever(JackpotWorker(context=build_worker_context()))


def run_valuation_worker() -> None:
    _run_forever(ValuationWorker(context=build_worker_context()))


def run_ai_matchmaker_worker() -> None:
    _run_forever(AiMatchmakerWorker(context=build_worker_context()))


def run_ai_brain_worker() -> None:
    _run_forever(AiBrainWorker(context=build_worker_context()))
