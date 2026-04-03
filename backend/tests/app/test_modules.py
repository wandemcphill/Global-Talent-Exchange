from __future__ import annotations

from types import ModuleType, SimpleNamespace
import sys

import pytest

from app import modules as app_modules


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def __enter__(self) -> "_FakeSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False

    def commit(self) -> None:
        self.commit_calls += 1


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.calls = 0
        self.last_session: _FakeSession | None = None

    def __call__(self) -> _FakeSession:
        self.calls += 1
        session = _FakeSession()
        self.last_session = session
        return session


def _build_context(*, app_env: str) -> tuple[SimpleNamespace, _FakeSessionFactory]:
    session_factory = _FakeSessionFactory()
    context = SimpleNamespace(
        settings=SimpleNamespace(run_startup_seeding=True, environment=app_env),
        database=SimpleNamespace(session_factory=session_factory),
    )
    return context, session_factory


@pytest.mark.parametrize(
    ("seed_attr", "module_name", "class_name"),
    (
        ("_seed_football_event_defaults", "app.football_events_engine.service", "RealWorldFootballEventService"),
        ("_seed_world_simulation_defaults", "app.world_simulation.service", "FootballWorldService"),
    ),
)
def test_local_only_startup_seeds_skip_outside_local_environment(
    monkeypatch,
    seed_attr: str,
    module_name: str,
    class_name: str,
) -> None:
    calls: list[str] = []
    fake_module = ModuleType(module_name)

    class _FakeService:
        def __init__(self, session) -> None:
            del session
            calls.append("init")

        def seed_defaults(self) -> None:
            calls.append("seed")

    setattr(fake_module, class_name, _FakeService)
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    context, session_factory = _build_context(app_env="production")
    getattr(app_modules, seed_attr)(None, context)

    assert calls == []
    assert session_factory.calls == 0


@pytest.mark.parametrize(
    ("seed_attr", "module_name", "class_name"),
    (
        ("_seed_football_event_defaults", "app.football_events_engine.service", "RealWorldFootballEventService"),
        ("_seed_world_simulation_defaults", "app.world_simulation.service", "FootballWorldService"),
    ),
)
def test_local_only_startup_seeds_run_in_local_environment(
    monkeypatch,
    seed_attr: str,
    module_name: str,
    class_name: str,
) -> None:
    calls: list[str] = []
    fake_module = ModuleType(module_name)

    class _FakeService:
        def __init__(self, session) -> None:
            del session
            calls.append("init")

        def seed_defaults(self) -> None:
            calls.append("seed")

    setattr(fake_module, class_name, _FakeService)
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    context, session_factory = _build_context(app_env="LOCAL")
    getattr(app_modules, seed_attr)(None, context)

    assert calls == ["init", "seed"]
    assert session_factory.calls == 1
    assert session_factory.last_session is not None
    assert session_factory.last_session.commit_calls == 1
