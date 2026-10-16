from __future__ import annotations

from types import SimpleNamespace

from app.workers import jobs


def test_worker_context_uses_default_migration_policy(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    monkeypatch.setattr(jobs, "_TASK_CONTEXT", None)
    monkeypatch.setattr(jobs, "get_settings", lambda: sentinel)

    def _fake_build_application_context(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(jobs, "build_application_context", _fake_build_application_context)

    try:
        context = jobs._context()
    finally:
        jobs._TASK_CONTEXT = None

    assert isinstance(context, SimpleNamespace)
    assert captured["settings"] is sentinel
    assert "run_migration_check" not in captured
