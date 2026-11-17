"""PostgreSQL locking for canonical live execution.

`test_skip_locked_hides_a_row_held_by_another_connection` proves the SQL clause.
`test_two_workers_claim_one_canonical_execution` runs the real
CanonicalLiveExecutionService.claim_and_advance_due_executions on two connections.

SQLite ignores FOR UPDATE SKIP LOCKED. Both tests run only when
GTE_TEST_POSTGRES_URL points at a local disposable database.
"""

from __future__ import annotations

import importlib.util
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.sql.schema import DefaultClause

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.models.base import Base
from app.models.competition_match_execution import CompetitionMatchExecution
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService

pytestmark = pytest.mark.skipif(
    not os.getenv("GTE_TEST_POSTGRES_URL"),
    reason="GTE_TEST_POSTGRES_URL is required to prove PostgreSQL SKIP LOCKED",
)


def test_skip_locked_hides_a_row_held_by_another_connection() -> None:
    engine = create_database_engine(os.environ["GTE_TEST_POSTGRES_URL"])
    holder = other = None
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS gtex_lease_probe"))
            connection.execute(text("CREATE TABLE gtex_lease_probe (id integer primary key, owner text)"))
            connection.execute(text("INSERT INTO gtex_lease_probe (id, owner) VALUES (1, 'worker-a')"))
        holder = engine.connect()
        transaction = holder.begin()
        holder.execute(text("SELECT id FROM gtex_lease_probe WHERE id = 1 FOR UPDATE"))
        other = engine.connect()
        hidden = other.execute(text("SELECT id FROM gtex_lease_probe WHERE id = 1 FOR UPDATE SKIP LOCKED")).all()
        assert hidden == []
        transaction.rollback()
    finally:
        if other is not None:
            other.close()
        if holder is not None:
            holder.close()
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS gtex_lease_probe"))
        engine.dispose()


def _local_postgres_url() -> str:
    url = os.environ["GTE_TEST_POSTGRES_URL"]
    host = (make_url(url).host or "").lower()
    if host not in {"localhost", "127.0.0.1"}:
        pytest.skip("refusing to run the concurrency fixture against a non-local database")
    return url


def _phase1():
    path = Path(__file__).with_name("test_canonical_live_execution_phase1.py")
    spec = importlib.util.spec_from_file_location("gtex_postgres_claim_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_postgres_metadata() -> None:
    """Let create_all emit a timestamp default PostgreSQL accepts.

    Two models store the server default CURRENT_TIMESTAMP as a Python string.
    SQLAlchemy then quotes it, and PostgreSQL rejects the quoted literal.
    The migrations use an unquoted expression. This adjustment is in-memory
    for the disposable test database and does not change the model source.
    """

    for table in Base.metadata.tables.values():
        for column in table.columns:
            default = column.server_default
            if default is not None and getattr(default, "arg", None) == "CURRENT_TIMESTAMP":
                column.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))


def test_two_workers_claim_one_canonical_execution() -> None:
    """Application-level claim. This is not the standalone SKIP LOCKED probe."""

    engine = create_database_engine(_local_postgres_url())
    load_model_modules()
    _prepare_postgres_metadata()
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)
    helpers = _phase1()
    now = datetime.now(timezone.utc)
    try:
        with session_factory() as session:
            _, match, _, _ = helpers._seed_canonical_fixture(session)
            match.scheduled_at = now - timedelta(minutes=5)
            service = CanonicalLiveExecutionService(session)
            service.start_live_execution(match.id, step_interval_seconds=0)
            _, execution, _ = service.step_execution(match.id, step_minutes=15, step_interval_seconds=0)
            match_id = match.id
            execution.lease_owner = None
            execution.lease_expires_at = None
            execution.next_step_at = now - timedelta(seconds=5)
            before_ids = [str(item.get("event_id")) for item in execution.committed_events_json or []]
            session.commit()

        barrier = threading.Barrier(2)
        results: dict[str, dict] = {}
        errors: dict[str, BaseException] = {}

        def claim(owner: str) -> None:
            try:
                barrier.wait(timeout=60)
                with session_factory() as session:
                    summary = CanonicalLiveExecutionService(session).claim_and_advance_due_executions(
                        reference_at=now,
                        step_minutes=15,
                        lease_owner=owner,
                        step_interval_seconds=0,
                    )
                    session.commit()
                    results[owner] = summary
            except BaseException as exc:  # noqa: BLE001 - reported below with the owner name
                errors[owner] = exc

        threads = [threading.Thread(target=claim, args=(owner,)) for owner in ("worker-a", "worker-b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=180)

        assert not errors, errors
        assert sorted(item["advanced"] for item in results.values()) == [0, 1]
        with session_factory() as session:
            row = session.scalar(
                select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
            )
            assert row is not None
            raced_ids = [str(item.get("event_id")) for item in row.committed_events_json or []]
            assert row.current_minute == 30
            assert raced_ids[: len(before_ids)] == before_ids
            assert len(raced_ids) == len(set(raced_ids))
            row.lease_owner = "stale-worker"
            row.lease_expires_at = now - timedelta(seconds=30)
            row.next_step_at = now - timedelta(seconds=5)
            session.commit()

        with session_factory() as session:
            recovered = CanonicalLiveExecutionService(session).claim_and_advance_due_executions(
                reference_at=datetime.now(timezone.utc),
                step_minutes=15,
                lease_owner="recovered-worker",
                step_interval_seconds=0,
            )
            session.commit()
            row = session.scalar(
                select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
            )
            assert row is not None
            recovered_ids = [str(item.get("event_id")) for item in row.committed_events_json or []]
        assert recovered["recovered_leases"] >= 1
        assert recovered["advanced"] == 1
        assert row.current_minute > 30
        assert row.lease_owner != "stale-worker"
        assert recovered_ids[: len(raced_ids)] == raced_ids
        assert len(recovered_ids) == len(set(recovered_ids))
    finally:
        engine.dispose()
