from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import DatabaseRuntime, create_database_engine, create_session_factory

if TYPE_CHECKING:
    from app.backbone.outbox_relay import OutboxRelayService
    from app.core.cache import CacheBackend
    from app.core.events import EventPublisher
    from app.global_memory.projections import GlobalMemoryProjectionService
    from app.core.jobs import InlineJobBackend
    from app.ingestion.pipeline import NormalizedMatchEventPipeline
    from app.jobs import IngestionJobRunner
    from app.market.service import MarketEngine
    from app.match_engine.services.match_simulation_service import MatchSimulationService
    from app.notifications.service import NotificationCenter
    from app.observability.alert_system import AlertSystem
    from app.observability.metrics import GTexMetrics
    from app.realtime.service import RealtimeHub
    from app.services.email import EmailService
    from app.services.referral_orchestrator import ReferralOrchestrator
    from app.value_engine.service import IngestionValueEngineBridge

logger = logging.getLogger(__name__)


class DeferredMetrics:
    def __init__(self, *, runtime_name: str, session_factory: sessionmaker[Session]) -> None:
        self.runtime_name = runtime_name
        self.session_factory = session_factory
        self._metrics: GTexMetrics | None = None

    def resolve(self) -> GTexMetrics:
        if self._metrics is None:
            from app.observability.metrics import GTexMetrics

            self._metrics = GTexMetrics(
                runtime_name=self.runtime_name,
                session_factory=self.session_factory,
            )
        return self._metrics

    def __getattr__(self, name: str) -> Any:
        return getattr(self.resolve(), name)


class Container:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        engine: Engine | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.database = DatabaseRuntime.build(
            settings=self.settings,
            engine=engine,
            session_factory=session_factory,
        )
        self.metrics = DeferredMetrics(
            runtime_name=self.settings.observability_service_name or self.settings.kafka_client_id,
            session_factory=self.database.session_factory,
        )
        self.email_service: EmailService | None = None
        self.cache_backend: CacheBackend | None = None
        self.event_publisher: EventPublisher | None = None
        self.job_backend: InlineJobBackend | None = None
        self.outbox_relay: OutboxRelayService | None = None
        self.notifications: NotificationCenter | None = None
        self.alert_system: AlertSystem | None = None
        self.realtime: RealtimeHub | None = None
        self.global_memory_projector: GlobalMemoryProjectionService | None = None
        self.market_engine: MarketEngine | None = None
        self.ingestion_pipeline: NormalizedMatchEventPipeline | None = None
        self.value_engine_bridge: IngestionValueEngineBridge | None = None
        self.ingestion_job_runner: IngestionJobRunner | None = None
        self.match_service: MatchSimulationService | None = None
        self.orchestrator: ReferralOrchestrator | None = None
        self._initialized = False

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self, *, run_migration_check: bool | None = None) -> Container:
        if self._initialized:
            return self

        from app.backbone.kafka import KafkaBackboneUnavailable, KafkaJsonProducer
        from app.backbone.outbox_relay import OutboxRelayService
        from app.backbone.routing import OutboxTopicRouter
        from app.backbone.redis_fanout import HybridEventPublisher
        from app.core.cache import build_cache_backend
        from app.core.events import InMemoryEventPublisher
        from app.core.jobs import InlineJobBackend
        from app.ingestion.pipeline import NormalizedMatchEventPipeline
        from app.infrastructure.outbox import RedisKafkaOutboxPublisher
        from app.global_memory.projections import GlobalMemoryProjectionService
        from app.jobs import IngestionJobRunner
        from app.market.projections import MarketSummaryProjector
        from app.market.repositories import build_market_repository
        from app.market.service import MarketEngine
        from app.matches.command_runtime import LocalMatchCommandBridge
        from app.match_engine.services.match_simulation_service import MatchSimulationService
        from app.notifications.service import NotificationCenter
        from app.observability.alert_system import AlertSystem
        from app.players.service import PlayerSummaryProjector
        from app.realtime.service import RealtimeHub
        from app.risk.fraud_service import FraudDetectionService
        from app.risk.security_monitoring_service import SecurityMonitoringService
        from app.services.email import EmailService
        from app.services.referral_orchestrator import ReferralOrchestrator
        from app.value_engine.service import IngestionValueEngineBridge

        logger.info("container.initialize.begin")
        self.database.initialize(run_migration_check=run_migration_check)
        self.email_service = EmailService.build(self.settings)
        self.cache_backend = build_cache_backend(settings=self.settings)

        if self.settings.redis_url:
            event_publisher = HybridEventPublisher(
                redis_url=self.settings.redis_url,
                redis_channel=self.settings.redis_event_channel,
            )
            event_publisher.start()
        else:
            event_publisher = InMemoryEventPublisher()
        self.event_publisher = event_publisher

        self.job_backend = InlineJobBackend(event_publisher=event_publisher)
        self.notifications = NotificationCenter()
        self.alert_system = AlertSystem()
        self.realtime = RealtimeHub()

        fraud_detection = FraudDetectionService(
            session_factory=self.database.session_factory,
            event_publisher=event_publisher,
        )
        security_monitoring = SecurityMonitoringService(
            session_factory=self.database.session_factory,
        )
        self.global_memory_projector = GlobalMemoryProjectionService(self.database.session_factory)
        event_publisher.subscribe(self.notifications.handle_event)
        event_publisher.subscribe(self.alert_system.handle_event)
        event_publisher.subscribe(self.metrics.handle_event)
        event_publisher.subscribe(self.realtime.handle_event)
        event_publisher.subscribe(fraud_detection.handle_event)
        event_publisher.subscribe(security_monitoring.handle_event)
        event_publisher.subscribe(self.global_memory_projector.handle_event)
        if _use_local_match_command_bridge(self.settings):
            event_publisher.subscribe(
                LocalMatchCommandBridge(
                    session_factory=self.database.session_factory,
                    event_publisher=event_publisher,
                ).handle_event
            )

        self.outbox_relay = None
        if self.settings.outbox_relay_enabled and (
            self.settings.kafka_enabled or self.settings.redis_url or _use_local_outbox_relay(self.settings)
        ):
            kafka_producer = None
            if self.settings.kafka_enabled:
                try:
                    kafka_producer = KafkaJsonProducer(
                        brokers=self.settings.kafka_brokers,
                        client_id=self.settings.kafka_client_id,
                    )
                except KafkaBackboneUnavailable:
                    if not self.settings.redis_url:
                        logger.warning("container.outbox_relay.unavailable")
                        kafka_producer = None
                    else:
                        logger.warning("container.outbox_relay.kafka_unavailable_falling_back_to_redis")
                        kafka_producer = None
            if kafka_producer is not None or self.settings.redis_url or _use_local_outbox_relay(self.settings):
                self.outbox_relay = OutboxRelayService(
                    session_factory=self.database.session_factory,
                    publisher=RedisKafkaOutboxPublisher(
                        event_publisher=event_publisher,
                        kafka_producer=kafka_producer,
                        topic_router=OutboxTopicRouter(topic_prefix=self.settings.kafka_topic_prefix),
                    ),
                    batch_size=self.settings.outbox_relay_batch_size,
                    poll_interval_ms=self.settings.outbox_relay_poll_interval_ms,
                )
                self.outbox_relay.start()

        self.market_engine = MarketEngine(
            repository=build_market_repository(self.settings.redis_url),
            summary_projector=MarketSummaryProjector(self.database.session_factory),
            event_publisher=event_publisher,
            cache_backend=self.cache_backend,
        )
        self.ingestion_pipeline = NormalizedMatchEventPipeline()
        self.value_engine_bridge = IngestionValueEngineBridge(
            session_factory=self.database.session_factory,
            pipeline=self.ingestion_pipeline,
            event_publisher=event_publisher,
            summary_projector=PlayerSummaryProjector(),
            settings=self.settings,
            default_lookback_days=self.settings.value_snapshot_lookback_days,
        )
        self.value_engine_bridge.ensure_event_subscription()
        self.ingestion_job_runner = IngestionJobRunner(
            session_factory=self.database.session_factory,
            cache_backend=self.cache_backend,
            provider_name=self.settings.default_ingestion_provider,
            value_snapshot_runner=self.value_engine_bridge,
            job_backend=self.job_backend,
        )
        self.match_service = MatchSimulationService()
        self.orchestrator = ReferralOrchestrator()
        self._initialized = True
        logger.info("container.initialize.complete")
        return self

    def shutdown(self) -> None:
        logger.info("container.shutdown.begin")
        if self.outbox_relay is not None:
            self.outbox_relay.stop()
        if self.event_publisher is not None and hasattr(self.event_publisher, "close"):
            self.event_publisher.close()
        if hasattr(self.database, "close"):
            self.database.close()
        self._initialized = False
        logger.info("container.shutdown.complete")

    def check_db(self, *, check_schema: bool | None = None) -> None:
        if not self.database.ping():
            raise RuntimeError("Database health check failed.")
        should_check_schema = self.settings.run_migration_check if check_schema is None else check_schema
        if should_check_schema:
            self.database.check_schema_smoke()

    def check_redis(self) -> None:
        if not self.settings.redis_url:
            logger.info("container.health.redis.skipped")
            return
        if self.cache_backend is None:
            logger.warning("container.health.redis.degraded reason=backend_missing")
            return
        if not self.cache_backend.ping():
            logger.warning("container.health.redis.degraded reason=ping_failed")
            return
        logger.info("container.health.redis.complete")


ApplicationContext = Container


def build_application_context(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
    run_migration_check: bool | None = None,
) -> ApplicationContext:
    return Container(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
    ).initialize(run_migration_check=run_migration_check)


def resolve_database_engine(
    *,
    settings: Settings,
    engine: Engine | None,
    session_factory: sessionmaker[Session] | None,
) -> Engine:
    if engine is not None:
        return engine
    bound_engine = session_factory.kw.get("bind") if session_factory is not None else None  # type: ignore[union-attr]
    if bound_engine is not None:
        return bound_engine
    return create_database_engine(settings.database_url)


def ensure_session_factory(
    *,
    engine: Engine,
    session_factory: sessionmaker[Session] | None,
) -> sessionmaker[Session]:
    return session_factory or create_session_factory(engine)


def bind_application_state(
    app: FastAPI,
    *,
    context: ApplicationContext,
    modules: Iterable[object],
) -> None:
    app.state.settings = context.settings
    app.state.container = context
    app.state.context = context
    app.state.db_engine = context.database.engine
    app.state.session_factory = context.database.session_factory
    app.state.read_db_engine = context.database.read_engine
    app.state.read_session_factory = context.database.read_session_factory
    app.state.email_service = context.email_service
    app.state.cache_backend = context.cache_backend
    app.state.event_publisher = context.event_publisher
    app.state.job_backend = context.job_backend
    app.state.outbox_relay = context.outbox_relay
    app.state.notifications = context.notifications
    app.state.alert_system = context.alert_system
    app.state.metrics = context.metrics
    app.state.realtime = context.realtime
    app.state.market_engine = context.market_engine
    app.state.ingestion_pipeline = context.ingestion_pipeline
    app.state.value_engine_bridge = context.value_engine_bridge
    app.state.ingestion_job_runner = context.ingestion_job_runner
    app.state.match_service = context.match_service
    app.state.orchestrator = context.orchestrator
    app.state.domain_modules = tuple(_module_name(module) for module in modules)


def _module_name(module: object) -> str:
    return str(getattr(module, "name", module))


def _use_local_outbox_relay(settings: Settings) -> bool:
    return not settings.kafka_enabled and not bool(settings.redis_url)


def _use_local_match_command_bridge(settings: Settings) -> bool:
    return settings.outbox_relay_enabled and _use_local_outbox_relay(settings)


__all__ = [
    "ApplicationContext",
    "Container",
    "bind_application_state",
    "build_application_context",
    "ensure_session_factory",
    "resolve_database_engine",
]
