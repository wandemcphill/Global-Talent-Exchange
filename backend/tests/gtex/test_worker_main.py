from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.gtex import worker_main, worker_runtime


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


class _FakeContext:
    def __init__(self, *, name: str) -> None:
        self.name = name
        self.shutdown_calls = 0

    def shutdown(self) -> None:
        self.shutdown_calls += 1


def test_worker_main_initializes_database_once_before_spawning_threads(monkeypatch) -> None:
    events: list[tuple] = []
    database = _FakeDatabaseRuntime()
    settings = SimpleNamespace(app_env="production", run_migration_check=True)
    built_contexts: list[dict[str, object]] = []
    started_threads: list[object] = []

    def _fake_initialize(*, run_migration_check: bool) -> None:
        database.initialize_calls.append(run_migration_check)
        events.append(("db_initialize", run_migration_check))

    database.initialize = _fake_initialize  # type: ignore[method-assign]

    def _fake_build_worker_context(*, settings, database, run_migration_check: bool, seed_defaults: bool):
        context = _FakeContext(name=f"ctx-{len(built_contexts)}")
        built_contexts.append(
            {
                "settings": settings,
                "database": database,
                "run_migration_check": run_migration_check,
                "seed_defaults": seed_defaults,
                "context": context,
            }
        )
        events.append(("build_context", run_migration_check, seed_defaults))
        return context

    class _FakeThread:
        def __init__(self, *, target, kwargs=None, name=None, daemon=None) -> None:
            self.target = target
            self.kwargs = kwargs or {}
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            started_threads.append(self)
            events.append(("thread_start", self.name))

        def join(self) -> None:
            events.append(("thread_join", self.name))

    monkeypatch.setenv("GTE_GTEX_WORKERS", "valuation,matchmaker,brain,jackpot")
    monkeypatch.setattr(worker_main, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_main, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(worker_main, "DatabaseRuntime", SimpleNamespace(build=lambda **_kwargs: database))
    monkeypatch.setattr(worker_main, "build_worker_context", _fake_build_worker_context)
    monkeypatch.setattr(worker_main, "Thread", _FakeThread)

    with pytest.raises(RuntimeError, match="GTEX worker thread exited unexpectedly: gtex-valuation-worker"):
        worker_main.main()

    assert database.initialize_calls == [True]
    assert len(built_contexts) == 4
    assert [item["run_migration_check"] for item in built_contexts] == [False, False, False, False]
    assert [item["seed_defaults"] for item in built_contexts] == [True, False, False, False]
    assert all(item["database"] is database for item in built_contexts)
    assert [thread.name for thread in started_threads] == [
        "gtex-valuation-worker",
        "gtex-matchmaker-worker",
        "gtex-brain-worker",
        "gtex-jackpot-worker",
    ]
    for thread, item in zip(started_threads, built_contexts, strict=True):
        assert thread.kwargs == {"context": item["context"]}
    first_thread_idx = events.index(("thread_start", "gtex-valuation-worker"))
    assert events.index(("db_initialize", True)) < first_thread_idx
    assert database.close_calls == 0


def test_worker_main_cleans_up_built_contexts_if_startup_fails(monkeypatch) -> None:
    database = _FakeDatabaseRuntime()
    settings = SimpleNamespace(app_env="production", run_migration_check=True)
    built_contexts: list[_FakeContext] = []

    def _fake_build_worker_context(*, settings, database, run_migration_check: bool, seed_defaults: bool):
        del settings, database, run_migration_check, seed_defaults
        if len(built_contexts) == 1:
            raise RuntimeError("context-build-failed")
        context = _FakeContext(name="ctx-0")
        built_contexts.append(context)
        return context

    class _UnexpectedThread:
        def __init__(self, **_kwargs) -> None:  # pragma: no cover - must never spawn threads on failure
            raise AssertionError("Thread should not be constructed when pre-flight initialization fails")

    monkeypatch.setenv("GTE_GTEX_WORKERS", "valuation,matchmaker")
    monkeypatch.setattr(worker_main, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_main, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(worker_main, "DatabaseRuntime", SimpleNamespace(build=lambda **_kwargs: database))
    monkeypatch.setattr(worker_main, "build_worker_context", _fake_build_worker_context)
    monkeypatch.setattr(worker_main, "Thread", _UnexpectedThread)

    with pytest.raises(RuntimeError, match="context-build-failed"):
        worker_main.main()

    assert len(built_contexts) == 1
    assert built_contexts[0].shutdown_calls == 1
    assert database.close_calls == 1


def test_build_worker_context_reuses_preinitialized_database_without_reinitializing(monkeypatch) -> None:
    database = _FakeDatabaseRuntime()
    settings = SimpleNamespace(
        run_migration_check=True,
        redis_url=None,
        redis_event_channel="gtex.events",
        redis_realtime_channel="gtex.realtime",
    )
    fake_runtime = SimpleNamespace(
        jackpot=SimpleNamespace(ensure_open_round=lambda _session: None),
        ai_leagues=SimpleNamespace(seed_defaults=lambda _session: None),
        universe=SimpleNamespace(seed_defaults=lambda _session: None),
    )

    monkeypatch.setattr(worker_runtime, "build_gtex_runtime", lambda **_kwargs: fake_runtime)

    context = worker_runtime.build_worker_context(
        settings=settings,
        database=database,
        run_migration_check=False,
        seed_defaults=False,
    )

    assert context.database is database
    assert context.runtime is fake_runtime
    assert database.initialize_calls == []
