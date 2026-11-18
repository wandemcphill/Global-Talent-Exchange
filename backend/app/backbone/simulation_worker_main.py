from __future__ import annotations

import logging
from threading import Event as ThreadEvent

from app.backbone.kafka import KafkaJsonConsumer
from app.backbone.worker_health import note_worker_mode, record_worker_cycle, worker_health_snapshot
from app.core.database import collect_database_pool_telemetry
from app.backbone.queue_runtime import SimulationQueueConsumerService
from app.competition_engine.match_dispatcher import MatchDispatcher
from app.competition_engine.queue_contracts import DurableQueuePublisher
from app.core.config import get_settings
from app.core.container import build_application_context
from app.match_engine.services.execution_runtime import LocalMatchExecutionWorker
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing
from app.realtime.match_stream_service import MatchStreamService
from app.replay_archive.persistence import DatabaseReplayArchiveRepository
from app.replay_archive.policy import SpectatorVisibilityPolicyService
from app.replay_archive.service import ReplayArchiveService

logger = logging.getLogger(__name__)


def _park_disabled_worker(*, reason: str) -> None:
    logger.warning("simulation_worker.idle reason=%s", reason)
    ThreadEvent().wait()


def main() -> None:
    settings = get_settings()
    service_name = settings.observability_service_name or settings.kafka_client_id or "gtex-simulation-worker"
    context = None
    match_stream_service = None
    runtime = None
    configure_logging(
        json_logs=settings.observability_log_json,
        service_name=service_name,
        environment=settings.app_env,
    )
    use_kafka_consumer = bool(settings.kafka_brokers and settings.kafka_simulation_consumer_enabled)
    use_autonomous_scanner = bool(getattr(settings, "autonomous_fixture_execution_enabled", False))
    if not use_kafka_consumer and not use_autonomous_scanner:
        raise RuntimeError(
            "Simulation worker misconfigured: no active Kafka simulation consumer and "
            "GTE_AUTONOMOUS_FIXTURE_EXECUTION_ENABLED is false. Worker cannot start."
        )
    try:
        context = build_application_context(settings=settings)
        configure_tracing(
            enabled=settings.observability_tracing_enabled,
            service_name=service_name,
            environment=settings.app_env,
            service_version=settings.app_version,
            exporter_endpoint=settings.observability_otlp_traces_endpoint,
            sample_ratio=settings.observability_trace_sample_ratio,
            engine=context.database.engine,
        )
        if settings.observability_metrics_enabled:
            context.metrics.start_http_server(settings.observability_metrics_port)
        context.metrics.refresh_from_database()
        queue_publisher = DurableQueuePublisher(
            session_factory=context.database.session_factory,
            event_publisher=context.event_publisher,
        )
        dispatcher = MatchDispatcher(queue_publisher=queue_publisher)
        match_stream_service = MatchStreamService.from_settings(
            settings,
            event_publisher=context.event_publisher,
        )
        worker = LocalMatchExecutionWorker(
            dispatcher=dispatcher,
            event_publisher=context.event_publisher,
            session_factory=context.database.session_factory,
            team_factory=SyntheticSquadFactory(
                session_factory=context.database.session_factory,
                allow_synthetic_fallback=False,
            ),
            match_stream_service=match_stream_service,
            cache_backend=context.cache_backend,
            stream_update_interval_seconds=settings.match_stream_interval_seconds,
            stream_cache_ttl_seconds=settings.match_stream_cache_ttl_seconds,
        )
        replay_archive = ReplayArchiveService(
            spectator_policy=SpectatorVisibilityPolicyService(),
            repository=DatabaseReplayArchiveRepository(session_factory=context.database.session_factory),
        )
        context.event_publisher.subscribe(replay_archive.handle_event)
        if use_kafka_consumer:
            note_worker_mode("kafka_consumer")
            consumer = KafkaJsonConsumer(
                brokers=settings.kafka_brokers,
                group_id=f"{settings.kafka_queue_consumer_group}-simulation",
                client_id=f"{settings.kafka_client_id}-simulation",
                topics=KafkaJsonConsumer.topic_names(
                    prefix=settings.kafka_topic_prefix,
                    topics=("match.scheduled",),
                ),
            )
            runtime = SimulationQueueConsumerService(
                consumer=consumer,
                worker=worker,
                metrics=context.metrics,
            )
            runtime.start()
            ThreadEvent().wait()
        else:
            from app.services.autonomous_match_service import AutonomousMatchExecutionService

            stop_event = ThreadEvent()
            interval = max(1, getattr(settings, "autonomous_fixture_interval_seconds", 30) or 30)
            note_worker_mode("autonomous_fixture_scanner")
            logger.info(
                "simulation_worker.running mode=autonomous_fixture_scanner interval_seconds=%s",
                interval,
            )
            while not stop_event.is_set():
                try:
                    pool_snapshot: dict[str, object] | None = None
                    with context.database.session_factory() as session:
                        scanner = AutonomousMatchExecutionService(session)
                        results = scanner.start_and_step_live_fixtures()
                        if results.get("failed", 0) > 0 or results.get("errors"):
                            logger.error("simulation_worker.fixture_execution_failures results=%s", results)
                        elif (
                            results.get("started", 0) > 0
                            or results.get("advanced", 0) > 0
                            or results.get("settled_competitions")
                        ):
                            logger.info("simulation_worker.stepped_live_fixtures results=%s", results)
                        session.commit()
                        try:
                            db_health = scanner.get_health_telemetry()
                        except Exception:
                            logger.exception("simulation_worker.health_query_failed")
                            db_health = {}
                        bind = session.get_bind()
                        engine = getattr(bind, "engine", bind)
                        if engine is not None:
                            pool_snapshot = collect_database_pool_telemetry(engine)
                    record_worker_cycle(
                        advanced=int(results.get("advanced") or 0),
                        started=int(results.get("started") or 0),
                        failed=int(results.get("failed") or 0) + len(results.get("errors") or []),
                    )
                    logger.info(
                        "simulation_worker.health process=%s executions=%s fixtures=%s pool=%s",
                        worker_health_snapshot(),
                        (db_health.get("executions") if isinstance(db_health, dict) else None),
                        (db_health.get("fixtures") if isinstance(db_health, dict) else None),
                        pool_snapshot,
                    )
                except Exception as exc:
                    record_worker_cycle(error=str(exc))
                    logger.exception("simulation_worker.autonomous_cycle_error error=%s", exc)

                # Owner-console regen growth, injuries and owner decisions must
                # advance from the same persisted GTEX virtual calendar even if
                # no owner opens the control centre. Use a separate transaction
                # so a failed owner tick cannot roll back a successfully executed
                # canonical competition fixture, and vice versa.
                try:
                    from app.owner_console.service import process_due_owner_world_ticks

                    with context.database.session_factory() as owner_session:
                        owner_results = process_due_owner_world_ticks(owner_session)
                        owner_session.commit()
                    if (
                        owner_results.get("ticks_executed", 0) > 0
                        or owner_results.get("clubs_backlogged", 0) > 0
                        or owner_results.get("ticks_failed", 0) > 0
                    ):
                        logger.info("simulation_worker.owner_world_ticks results=%s", owner_results)
                except Exception as exc:
                    logger.exception("simulation_worker.owner_world_tick_cycle_error error=%s", exc)
                stop_event.wait(interval)
    finally:
        if runtime is not None:
            runtime.stop()
        if context is not None:
            shutdown = getattr(context, "shutdown", None)
            if callable(shutdown):
                shutdown()
            else:
                outbox_relay = getattr(context, "outbox_relay", None)
                if outbox_relay is not None:
                    outbox_relay.stop()
                if hasattr(context.event_publisher, "close"):
                    context.event_publisher.close()
        if match_stream_service is not None:
            match_stream_service.close()


if __name__ == "__main__":
    main()
