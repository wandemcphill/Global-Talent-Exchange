"""Guards the Postgres connect-args branch of ``create_database_engine``.

Commit 9cb58601 added TCP keepalives here to stop a silently-dead Supabase
pooler connection from hanging ``pool_pre_ping``'s liveness check forever on
``recv()``.  It shipped with no test, and neither did the rest of that branch:
nothing in the suite called ``create_database_engine`` at all, so the
connect-timeout, pool-sizing and ``prepare_threshold`` settings that keep the
production pooler healthy were equally unguarded.

The risk this covers is a regression that leaks Postgres-only libpq parameters
onto a SQLite engine.  ``keepalives`` and friends are libpq conninfo keys; a
SQLite DBAPI rejects them outright, so widening the branch would break every
local and CI run that builds an engine.  The reverse direction matters too --
dropping the keepalives silently restores the production hang.

The engine is never connected: ``create_engine`` is captured so the assertions
read the arguments the module actually passes, without needing a database or a
psycopg install.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core import database


@pytest.fixture()
def captured_engine_kwargs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Capture the kwargs ``create_database_engine`` hands to ``create_engine``."""
    captured: dict[str, Any] = {}

    def _fake_create_engine(url: str, **kwargs: Any) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(database, "create_engine", _fake_create_engine)
    return captured


KEEPALIVE_KEYS = ("keepalives", "keepalives_idle", "keepalives_interval", "keepalives_count")


def test_postgres_engine_enables_tcp_keepalives(
    captured_engine_kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in ("GTE_DATABASE_KEEPALIVES_IDLE", "GTE_DATABASE_KEEPALIVES_INTERVAL", "GTE_DATABASE_KEEPALIVES_COUNT"):
        monkeypatch.delenv(key, raising=False)

    database.create_database_engine("postgresql+psycopg://user:pw@example.invalid:6543/gtex")

    connect_args = captured_engine_kwargs["connect_args"]
    assert connect_args["keepalives"] == 1
    # A dead connection is detected after keepalives_idle + (interval * count),
    # i.e. 60s with these defaults, rather than never.
    assert connect_args["keepalives_idle"] == 30
    assert connect_args["keepalives_interval"] == 10
    assert connect_args["keepalives_count"] == 3
    # Keepalives only help if the pool actually re-checks connections.
    assert captured_engine_kwargs["pool_pre_ping"] is True


def test_keepalive_intervals_are_env_tunable(
    captured_engine_kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GTE_DATABASE_KEEPALIVES_IDLE", "5")
    monkeypatch.setenv("GTE_DATABASE_KEEPALIVES_INTERVAL", "2")
    monkeypatch.setenv("GTE_DATABASE_KEEPALIVES_COUNT", "4")

    database.create_database_engine("postgresql+psycopg://user:pw@example.invalid:6543/gtex")

    connect_args = captured_engine_kwargs["connect_args"]
    assert connect_args["keepalives_idle"] == 5
    assert connect_args["keepalives_interval"] == 2
    assert connect_args["keepalives_count"] == 4


def test_unparsable_keepalive_env_falls_back_to_the_default(
    captured_engine_kwargs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed operational setting must not stop the API from booting."""
    monkeypatch.setenv("GTE_DATABASE_KEEPALIVES_IDLE", "not-a-number")

    database.create_database_engine("postgresql+psycopg://user:pw@example.invalid:6543/gtex")

    assert captured_engine_kwargs["connect_args"]["keepalives_idle"] == 30


def test_sqlite_engine_gets_no_libpq_connect_args(captured_engine_kwargs: dict[str, Any], tmp_path: Any) -> None:
    """libpq keys on a SQLite DBAPI raise on connect, so the branch must not widen."""
    database.create_database_engine(f"sqlite:///{tmp_path / 'guard.db'}")

    connect_args = captured_engine_kwargs["connect_args"]
    assert connect_args == {"check_same_thread": False}
    for key in KEEPALIVE_KEYS + ("connect_timeout", "prepare_threshold"):
        assert key not in connect_args
    # Pool sizing is a pooler concern; SQLite must not inherit it either.
    assert "pool_size" not in captured_engine_kwargs
    assert "max_overflow" not in captured_engine_kwargs
