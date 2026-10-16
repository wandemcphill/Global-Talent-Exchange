from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.backbone import feed_worker_main, outbox_relay_main, projection_worker_main, simulation_worker_main


class _FakeMetrics:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self.http_server_ports: list[int] = []

    def start_http_server(self, port: int) -> None:
        self.http_server_ports.append(port)

    def refresh_from_database(self) -> None:
        self.refresh_calls += 1


class _FakeEventPublisher:
    def __init__(self) -> None:
        self.subscribers: list[object] = []
        self.closed = False

    def subscribe(self, subscriber) -> None:
        self.subscribers.append(subscriber)

    def close(self) -> None:
        self.closed = True


class _FakeOutboxRelay:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _FakeMatchStreamService:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeWaitEvent:
    def wait(self) -> None:
        return None


class _FakeDatabaseRuntime:
    def __init__(self) -> None:
        self.session_factory = object()
        self.read_session_factory = object()
        self.initialize_calls: list[bool] = []
        self.close_calls = 0

    def initialize(self, *, run_migration_check: bool) -> None:
        self.initialize_calls.append(run_migration_check)

    def close(self) -> None:
        self.close_calls += 1


class _FakeScaleApp:
    def __init__(self) -> None:
        self.state = SimpleNamespace(metrics=_FakeMetrics())


def _build_settings(**overrides):
    defaults = {
        "observability_service_name": None,
        "kafka_client_id": "gtex-tests",
        "observability_log_json": False,
        "app_env": "test",
        "app_version": "test-version",
        "observability_tracing_enabled": False,
        "observability_otlp_traces_endpoint": None,
        "observability_trace_sample_ratio": 0.0,
        "observability_metrics_enabled": True,
        "observability_metrics_port": 9100,
        "kafka_queue_consumer_group": "gtex-queue-tests",
        "kafka_projection_consumer_group": "gtex-projection-tests",
        "kafka_topic_prefix": "gtex",
        "kafka_brokers": ("localhost:9092",),
        "match_stream_interval_seconds": 1,
        "match_stream_cache_ttl_seconds": 30,
        "kafka_simulation_consumer_enabled": True,
        "projection_workers_enabled": True,
        "run_migration_check": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _build_context() -> SimpleNamespace:
    return SimpleNamespace(
        database=SimpleNamespace(
            engine=object(),
            session_factory=object(),
        ),
        cache_backend=object(),
        metrics=_FakeMetrics(),
        outbox_relay=_FakeOutboxRelay(),
        event_publisher=_FakeEventPublisher(),
    )


def test_simulation_worker_main_cleans_up_on_runtime_start_failure(monkeypatch) -> None:
    settings = _build_settings()
    context = _build_context()
    match_stream_service = _FakeMatchStreamService()

    class _FakeKafkaConsumer:
        @staticmethod
        def topic_names(*, prefix: str, topics: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(f"{prefix}.{topic}" for topic in topics)

        def __init__(self, **_kwargs) -> None:
            return None

    class _FakeRuntime:
        def __init__(self, **_kwargs) -> None:
            self.stop_calls = 0

        def start(self) -> None:
            raise RuntimeError("simulation-start-failed")

        def stop(self) -> None:
            self.stop_calls += 1

    runtime_holder: dict[str, _FakeRuntime] = {}

    def _build_runtime(**kwargs) -> _FakeRuntime:
        runtime = _FakeRuntime(**kwargs)
        runtime_holder["runtime"] = runtime
        return runtime

    monkeypatch.setattr(simulation_worker_main, "get_settings", lambda: settings)
    monkeypatch.setattr(simulation_worker_main, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(simulation_worker_main, "configure_tracing", lambda **_kwargs: None)
    monkeypatch.setattr(simulation_worker_main, "build_application_context", lambda **_kwargs: context)
    monkeypatch.setattr(simulation_worker_main, "DurableQueuePublisher", lambda **_kwargs: object())
    monkeypatch.setattr(simulation_worker_main, "MatchDispatcher", lambda **_kwargs: object())
    monkeypatch.setattr(
        simulation_worker_main,
        "MatchStreamService",
        SimpleNamespace(from_settings=lambda *_args, **_kwargs: match_stream_service),
    )
    monkeypatch.setattr(simulation_worker_main, "LocalMatchExecutionWorker", lambda **_kwargs: object())
    monkeypatch.setattr(simulation_worker_main, "SyntheticSquadFactory", lambda **_kwargs: object())
    monkeypatch.setattr(simulation_worker_main, "SpectatorVisibilityPolicyService", lambda: object())
    monkeypatch.setattr(simulation_worker_main, "DatabaseReplayArchiveRepository", lambda **_kwargs: object())
    monkeypatch.setattr(
        simulation_worker_main, "ReplayArchiveService", lambda **_kwargs: SimpleNamespace(handle_event=object())
    )
    monkeypatch.setattr(simulation_worker_main, "KafkaJsonConsumer", _FakeKafkaConsumer)
    monkeypatch.setattr(simulation_worker_main, "SimulationQueueConsumerService", _build_runtime)

    with pytest.raises(RuntimeError, match="simulation-start-failed"):
        simulation_worker_main.main()

    runtime = runtime_holder["runtime"]
    assert runtime.stop_calls == 1
    assert context.outbox_relay.stop_calls == 1
    assert context.event_publisher.closed is True
    assert match_stream_service.closed is True
    assert context.metrics.http_server_ports == [9100]
    assert context.metrics.refresh_calls == 1
    assert len(context.event_publisher.subscribers) == 1


def test_projection_worker_main_starts_and_cleans_up(monkeypatch) -> None:
    settings = _build_settings()
    context = _build_context()

    class _FakeKafkaConsumer:
        @staticmethod
        def topic_names(*, prefix: str, topics: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(f"{prefix}.{topic}" for topic in topics)

        def __init__(self, **_kwargs) -> None:
            return None

    class _FakeRuntime:
        def __init__(self, **_kwargs) -> None:
            self.started = False
            self.stop_calls = 0

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stop_calls += 1

    runtime_holder: dict[str, _FakeRuntime] = {}

    def _build_runtime(**kwargs) -> _FakeRuntime:
        runtime = _FakeRuntime(**kwargs)
        runtime_holder["runtime"] = runtime
        return runtime

    monkeypatch.setattr(projection_worker_main, "get_settings", lambda: settings)
    monkeypatch.setattr(projection_worker_main, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(projection_worker_main, "configure_tracing", lambda **_kwargs: None)
    monkeypatch.setattr(projection_worker_main, "build_application_context", lambda **_kwargs: context)
    monkeypatch.setattr(projection_worker_main, "KafkaJsonConsumer", _FakeKafkaConsumer)
    monkeypatch.setattr(projection_worker_main, "ProjectionWorkerService", _build_runtime)
    monkeypatch.setattr(projection_worker_main, "ThreadEvent", _FakeWaitEvent)

    projection_worker_main.main()

    runtime = runtime_holder["runtime"]
    assert runtime.started is True
    assert runtime.stop_calls == 1
    assert context.outbox_relay.stop_calls == 1
    assert context.event_publisher.closed is True
    assert context.metrics.http_server_ports == [9100]
    assert context.metrics.refresh_calls == 1


def test_feed_worker_main_cleans_up_on_runtime_start_failure(monkeypatch) -> None:
    settings = _build_settings()
    database = _FakeDatabaseRuntime()
    app = _FakeScaleApp()

    class _FakeKafkaConsumer:
        @staticmethod
        def topic_names(*, prefix: str, topics: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(f"{prefix}.{topic}" for topic in topics)

        def __init__(self, **_kwargs) -> None:
            return None

    class _FakeRuntime:
        def __init__(self, **_kwargs) -> None:
            self.stop_calls = 0

        def start(self) -> None:
            raise RuntimeError("feed-start-failed")

        def stop(self) -> None:
            self.stop_calls += 1

    runtime_holder: dict[str, _FakeRuntime] = {}

    def _build_runtime(**kwargs) -> _FakeRuntime:
        runtime = _FakeRuntime(**kwargs)
        runtime_holder["runtime"] = runtime
        return runtime

    monkeypatch.setattr(feed_worker_main, "get_settings", lambda: settings)
    monkeypatch.setattr(feed_worker_main, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(feed_worker_main, "DatabaseRuntime", SimpleNamespace(build=lambda **_kwargs: database))
    monkeypatch.setattr(feed_worker_main, "build_worker_app", lambda **_kwargs: app)
    monkeypatch.setattr(feed_worker_main, "KafkaJsonConsumer", _FakeKafkaConsumer)
    monkeypatch.setattr(feed_worker_main, "feed_refresh_handler", lambda **_kwargs: object())
    monkeypatch.setattr(feed_worker_main, "ScaleTopicConsumerService", _build_runtime)

    with pytest.raises(RuntimeError, match="feed-start-failed"):
        feed_worker_main.main()

    runtime = runtime_holder["runtime"]
    assert runtime.stop_calls == 1
    assert database.initialize_calls == [False]
    assert database.close_calls == 1
    assert app.state.metrics.http_server_ports == [9100]
    assert app.state.metrics.refresh_calls == 1


def test_outbox_relay_main_shutdowns_context_when_relay_is_unavailable(monkeypatch) -> None:
    settings = _build_settings()
    context = _build_context()
    context.shutdown_calls = 0
    context.shutdown = lambda: setattr(context, "shutdown_calls", context.shutdown_calls + 1)
    context.outbox_relay = None

    monkeypatch.setattr(outbox_relay_main, "get_settings", lambda: settings)
    monkeypatch.setattr(outbox_relay_main, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(outbox_relay_main, "configure_tracing", lambda **_kwargs: None)
    monkeypatch.setattr(outbox_relay_main, "build_application_context", lambda **_kwargs: context)

    with pytest.raises(RuntimeError, match="Outbox relay is not enabled"):
        outbox_relay_main.main()

    assert context.shutdown_calls == 1
    assert context.metrics.http_server_ports == [9100]
    assert context.metrics.refresh_calls == 1
