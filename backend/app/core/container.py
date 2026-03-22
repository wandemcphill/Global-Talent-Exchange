from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.cache import CacheBackend, build_cache_backend
from app.core.config import Settings, get_settings
from app.core.database import DatabaseRuntime
from app.core.events import InMemoryEventPublisher
from app.core.jobs import InlineJobBackend
from app.ingestion.pipeline import NormalizedMatchEventPipeline
from app.jobs import IngestionJobRunner
from app.market.projections import MarketSummaryProjector
from app.market.repositories import InMemoryMarketRepository
from app.market.service import MarketEngine
from app.notifications.service import NotificationCenter
from app.players.service import PlayerSummaryProjector
from app.realtime.service import RealtimeHub
from app.value_engine.service import IngestionValueEngineBridge


@dataclass(slots=True)
class ApplicationContext:
    settings: Settings
    database: DatabaseRuntime
    cache_backend: CacheBackend
    event_publisher: InMemoryEventPublisher
    job_backend: InlineJobBackend
    notifications: NotificationCenter
    realtime: RealtimeHub
    market_engine: MarketEngine
    ingestion_pipeline: NormalizedMatchEventPipeline
    value_engine_bridge: IngestionValueEngineBridge
    ingestion_job_runner: IngestionJobRunner


def build_application_context(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> ApplicationContext:
    resolved_settings = settings or get_settings()
    database = DatabaseRuntime.build(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
    )
    cache_backend = build_cache_backend(settings=resolved_settings)
    event_publisher = InMemoryEventPublisher()
    job_backend = InlineJobBackend(event_publisher=event_publisher)
    notifications = NotificationCenter()
    realtime = RealtimeHub()
    event_publisher.subscribe(notifications.handle_event)
    event_publisher.subscribe(realtime.handle_event)

    market_engine = MarketEngine(
        repository=InMemoryMarketRepository(),
        summary_projector=MarketSummaryProjector(database.session_factory),
        event_publisher=event_publisher,
    )
    ingestion_pipeline = NormalizedMatchEventPipeline()
    value_engine_bridge = IngestionValueEngineBridge(
        session_factory=database.session_factory,
        pipeline=ingestion_pipeline,
        event_publisher=event_publisher,
        summary_projector=PlayerSummaryProjector(),
        settings=resolved_settings,
        default_lookback_days=resolved_settings.value_snapshot_lookback_days,
    )
    value_engine_bridge.ensure_event_subscription()
    ingestion_job_runner = IngestionJobRunner(
        session_factory=database.session_factory,
        cache_backend=cache_backend,
        provider_name=resolved_settings.default_ingestion_provider,
        value_snapshot_runner=value_engine_bridge,
        job_backend=job_backend,
    )
    return ApplicationContext(
        settings=resolved_settings,
        database=database,
        cache_backend=cache_backend,
        event_publisher=event_publisher,
        job_backend=job_backend,
        notifications=notifications,
        realtime=realtime,
        market_engine=market_engine,
        ingestion_pipeline=ingestion_pipeline,
        value_engine_bridge=value_engine_bridge,
        ingestion_job_runner=ingestion_job_runner,
    )
