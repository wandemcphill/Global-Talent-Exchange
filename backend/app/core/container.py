from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.backbone.kafka import KafkaBackboneUnavailable, KafkaJsonProducer
from app.backbone.outbox_relay import OutboxRelayService
from app.backbone.redis_fanout import HybridEventPublisher
from app.backbone.routing import OutboxTopicRouter
from app.core.cache import CacheBackend, build_cache_backend
from app.core.config import Settings, get_settings
from app.core.database import DatabaseRuntime
from app.core.events import EventPublisher, InMemoryEventPublisher
from app.core.jobs import InlineJobBackend
from app.ingestion.pipeline import NormalizedMatchEventPipeline
from app.jobs import IngestionJobRunner
from app.market.projections import MarketSummaryProjector
from app.market.repositories import InMemoryMarketRepository
from app.market.service import MarketEngine
from app.notifications.service import NotificationCenter
from app.observability.alert_system import AlertSystem
from app.players.service import PlayerSummaryProjector
from app.realtime.service import RealtimeHub
from app.risk.fraud_service import FraudDetectionService
from app.services.email import EmailService
from app.value_engine.service import IngestionValueEngineBridge


@dataclass(slots=True)
class ApplicationContext:
    settings: Settings
    database: DatabaseRuntime
    email_service: EmailService
    cache_backend: CacheBackend
    event_publisher: EventPublisher
    job_backend: InlineJobBackend
    outbox_relay: OutboxRelayService | None
    notifications: NotificationCenter
    alert_system: AlertSystem
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
    email_service = EmailService.build(resolved_settings)
    cache_backend = build_cache_backend(settings=resolved_settings)
    if resolved_settings.redis_url:
        event_publisher: EventPublisher = HybridEventPublisher(
            redis_url=resolved_settings.redis_url,
            redis_channel=resolved_settings.redis_event_channel,
        )
        event_publisher.start()
    else:
        event_publisher = InMemoryEventPublisher()
    job_backend = InlineJobBackend(event_publisher=event_publisher)
    outbox_relay: OutboxRelayService | None = None
    notifications = NotificationCenter()
    alert_system = AlertSystem()
    realtime = RealtimeHub()
    fraud_detection = FraudDetectionService(
        session_factory=database.session_factory,
        event_publisher=event_publisher,
    )
    event_publisher.subscribe(notifications.handle_event)
    event_publisher.subscribe(alert_system.handle_event)
    event_publisher.subscribe(realtime.handle_event)
    event_publisher.subscribe(fraud_detection.handle_event)
    if resolved_settings.kafka_enabled and resolved_settings.outbox_relay_enabled:
        try:
            outbox_relay = OutboxRelayService(
                session_factory=database.session_factory,
                producer=KafkaJsonProducer(
                    brokers=resolved_settings.kafka_brokers,
                    client_id=resolved_settings.kafka_client_id,
                ),
                router=OutboxTopicRouter(topic_prefix=resolved_settings.kafka_topic_prefix),
                batch_size=resolved_settings.outbox_relay_batch_size,
                poll_interval_ms=resolved_settings.outbox_relay_poll_interval_ms,
            )
            outbox_relay.start()
        except KafkaBackboneUnavailable:
            outbox_relay = None

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
        email_service=email_service,
        cache_backend=cache_backend,
        event_publisher=event_publisher,
        job_backend=job_backend,
        outbox_relay=outbox_relay,
        notifications=notifications,
        alert_system=alert_system,
        realtime=realtime,
        market_engine=market_engine,
        ingestion_pipeline=ingestion_pipeline,
        value_engine_bridge=value_engine_bridge,
        ingestion_job_runner=ingestion_job_runner,
    )
