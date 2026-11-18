"""Three independent spectators read one canonical match, including a cold API."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from app.common.enums.match_status import MatchStatus
from app.core.cache import NullCacheBackend
from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.live_matches.router import _v2_match_state_payload
from app.live_matches.service import LiveMatchHub
from app.models.base import Base
from app.models.competition_match_execution import CompetitionMatchExecution
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService


def _helpers():
    path = Path(__file__).with_name("test_canonical_live_execution_phase1.py")
    spec = importlib.util.spec_from_file_location("gtex_three_spectator_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _factory(database_path: Path):
    engine = create_database_engine(f"sqlite+pysqlite:///{database_path}")
    load_model_modules()
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)


def _spectator(session_factory, match_id: str) -> tuple[dict, LiveMatchHub]:
    """A new hub is a new API process. It does not share another spectator's memory."""

    cache = NullCacheBackend()
    hub = LiveMatchHub(session_factory=session_factory, cache_backend=cache)
    app = SimpleNamespace(
        state=SimpleNamespace(
            session_factory=session_factory,
            cache_backend=cache,
            settings=None,
            event_publisher=None,
            live_match_hub=hub,
        )
    )
    return _v2_match_state_payload(match_id, app), hub


def _signature(payload: dict) -> dict:
    events = payload.get("events") or []
    return {
        "match_id": payload.get("match_id"),
        "status": payload.get("status"),
        "phase": payload.get("phase"),
        "minute": payload.get("minute"),
        "is_live": payload.get("is_live"),
        "execution_revision": payload.get("execution_revision"),
        "home_score": (payload.get("home") or {}).get("score"),
        "away_score": (payload.get("away") or {}).get("score"),
        "event_ids": [item.get("id") for item in events],
    }


def _assert_same(views: list[dict]) -> dict:
    signatures = [_signature(view) for view in views]
    first = signatures[0]
    for index, signature in enumerate(signatures[1:], start=1):
        assert signature == first, f"spectator {index} diverged: {signature} != {first}"
    return first


def test_three_spectators_see_a_scheduled_match_at_minute_zero(tmp_path: Path) -> None:
    helpers = _helpers()
    session_factory = _factory(tmp_path / "scheduled.db")
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        match.scheduled_at = datetime.now(timezone.utc) + timedelta(hours=2)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        execution = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match.id)
        )
        assert execution is not None
        match.status = MatchStatus.SCHEDULED.value
        execution.execution_status = "scheduled"
        execution.current_minute = 0
        execution.clock_phase = "pre_match"
        execution.elapsed_broadcast_seconds = 0
        match.home_score = 0
        match.away_score = 0
        match_id = match.id
        session.commit()

    views = [_spectator(session_factory, match_id)[0] for _ in range(3)]
    agreed = _assert_same(views)
    assert agreed["status"] == "SCHEDULED"
    assert agreed["phase"] == "pre_match"
    assert agreed["minute"] == 0
    assert agreed["is_live"] is False
    assert agreed["home_score"] == 0
    assert agreed["away_score"] == 0


def test_three_spectators_survive_api_and_worker_restart(tmp_path: Path) -> None:
    helpers = _helpers()
    session_factory = _factory(tmp_path / "live.db")
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        match.scheduled_at = now - timedelta(minutes=5)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        service.step_execution(match.id, step_minutes=15, step_interval_seconds=0)
        match_id = match.id
        session.commit()

    first_wave = [_spectator(session_factory, match_id)[0] for _ in range(3)]
    at_fifteen = _assert_same(first_wave)
    assert at_fifteen["status"] == "LIVE"
    assert at_fifteen["minute"] == 15
    assert at_fifteen["is_live"] is True
    assert at_fifteen["status"] != "FT"

    # The first hubs are discarded here. The next reads are a restarted API.
    restarted = [_spectator(session_factory, match_id)[0] for _ in range(3)]
    assert _assert_same(restarted) == at_fifteen

    with session_factory() as session:
        execution = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
        )
        assert execution is not None
        execution.lease_owner = "worker-a"
        execution.lease_expires_at = now + timedelta(minutes=5)
        execution.next_step_at = now - timedelta(seconds=5)
        committed_ids = [str(item.get("event_id")) for item in execution.committed_events_json or []]
        session.commit()

    with session_factory() as session_b:
        blocked = CanonicalLiveExecutionService(session_b).claim_and_advance_due_executions(
            reference_at=now,
            step_minutes=15,
            lease_owner="worker-b",
            step_interval_seconds=0,
        )
        session_b.commit()
    assert blocked["advanced"] == 0
    assert _assert_same([_spectator(session_factory, match_id)[0] for _ in range(3)])["minute"] == 15

    with session_factory() as session_a:
        owner = CanonicalLiveExecutionService(session_a).claim_and_advance_due_executions(
            reference_at=now,
            step_minutes=15,
            lease_owner="worker-a",
            step_interval_seconds=0,
        )
        session_a.commit()
        row = session_a.scalar(select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id))
        assert row is not None
        resumed_ids = [str(item.get("event_id")) for item in row.committed_events_json or []]
        assert row.lease_owner is None
    assert owner["advanced"] == 1
    assert resumed_ids[: len(committed_ids)] == committed_ids
    assert len(resumed_ids) == len(set(resumed_ids))

    at_thirty = _assert_same([_spectator(session_factory, match_id)[0] for _ in range(3)])
    late_joiner = _signature(_spectator(session_factory, match_id)[0])
    assert late_joiner == at_thirty
    assert at_thirty["minute"] == 30
    assert at_thirty["status"] == "LIVE"
    assert at_thirty["event_ids"][: len(at_fifteen["event_ids"])] == at_fifteen["event_ids"]

    _, reconnected = _spectator(session_factory, match_id)
    first_events, cursor = reconnected.get_events_since(match_id, 0)
    second_events, _ = reconnected.get_events_since(match_id, cursor)
    assert [event.event_id for event in first_events] == list(dict.fromkeys(event.event_id for event in first_events))
    assert second_events == []

    with session_factory() as session:
        service = CanonicalLiveExecutionService(session)
        service.step_execution(match_id, step_minutes=80, step_interval_seconds=0, stop_at_halftime=True)
        session.commit()
    halftime = _assert_same([_spectator(session_factory, match_id)[0] for _ in range(3)])
    assert halftime["status"] == "HALFTIME"
    assert halftime["status"] != "FT"

    with session_factory() as session:
        row = session.scalar(select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id))
        assert row is not None
        row.halftime_resume_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
        service = CanonicalLiveExecutionService(session)
        service.step_execution(
            match_id,
            step_minutes=80,
            step_interval_seconds=0,
            stop_at_halftime=True,
            resume_halftime=True,
        )
        session.commit()
        finished = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
        )
        assert finished is not None
        finished_ids = [str(item.get("event_id")) for item in finished.committed_events_json or []]
        finished_status = finished.execution_status

    full_time = _assert_same([_spectator(session_factory, match_id)[0] for _ in range(3)])
    assert finished_status == "completed"
    assert full_time["status"] == "FT"
    assert full_time["is_live"] is False

    with session_factory() as session:
        again = CanonicalLiveExecutionService(session).claim_and_advance_due_executions(
            step_minutes=15,
            lease_owner="worker-after-full-time",
            step_interval_seconds=0,
        )
        session.commit()
        row = session.scalar(select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id))
        assert row is not None
        repeated_ids = [str(item.get("event_id")) for item in row.committed_events_json or []]
    assert again["advanced"] == 0
    assert repeated_ids == finished_ids
    assert _signature(_spectator(session_factory, match_id)[0])["status"] == "FT"
