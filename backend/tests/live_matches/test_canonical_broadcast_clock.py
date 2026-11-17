"""Scheduled fixtures stay at minute 0, and a restarted API rebuilds the canonical clock."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.common.enums.match_status import MatchStatus
from app.core.cache import NullCacheBackend
from app.live_matches.canonical_presentation import (
    canonical_sample_time_seconds,
    resolve_canonical_presentation,
)
from app.live_matches.router import _v2_match_state_payload, build_unity_live_payload_for_app
from app.live_matches.service import LiveMatchHub
from app.models.competition_match_execution import CompetitionMatchExecution
from app.services.canonical_live_execution_service import CanonicalLiveExecutionService


def _phase1():
    path = Path(__file__).with_name("test_canonical_live_execution_phase1.py")
    spec = importlib.util.spec_from_file_location("gtex_broadcast_clock_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _app(session_factory):
    state = SimpleNamespace(
        session_factory=session_factory,
        cache_backend=NullCacheBackend(),
        settings=None,
        event_publisher=None,
    )
    state.live_match_hub = LiveMatchHub(session_factory=session_factory, cache_backend=state.cache_backend)
    return SimpleNamespace(state=state)


def _payload(session_factory, match_id: str) -> dict:
    return _v2_match_state_payload(match_id, _app(session_factory))


def test_unknown_execution_state_is_not_full_time() -> None:
    presentation = resolve_canonical_presentation(
        match_status="scheduled",
        execution_status="mystery",
        clock_phase="pre_match",
    )
    assert presentation.presentation == "unknown"
    assert presentation.api_status == "UNKNOWN"
    assert presentation.is_terminal is False

    unfinished = resolve_canonical_presentation(
        match_status="completed",
        execution_status="scheduled",
        clock_phase="pre_match",
    )
    assert unfinished.presentation == "pre_match"
    assert unfinished.inconsistent is True

    disagreed = resolve_canonical_presentation(
        match_status="scheduled",
        execution_status="completed",
        clock_phase="completed",
    )
    assert disagreed.presentation == "pre_match"
    assert disagreed.api_status == "SCHEDULED"


def test_sampling_uses_the_canonical_minute_not_the_final_frame() -> None:
    opening = canonical_sample_time_seconds(
        first_time_seconds=0,
        last_time_seconds=600,
        duration_seconds=600,
        last_clock_minute=90,
        clock_minute=0,
        target_end_minute=90,
        presentation="pre_match",
    )
    assert opening == 0
    midpoint = canonical_sample_time_seconds(
        first_time_seconds=0,
        last_time_seconds=600,
        duration_seconds=600,
        last_clock_minute=90,
        clock_minute=30,
        target_end_minute=90,
        presentation="live",
    )
    assert midpoint == 200


def test_scheduled_match_stays_at_minute_zero_without_an_in_memory_runtime() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        service.step_execution(match.id, step_minutes=30, step_interval_seconds=0)
        session.commit()
        viewer = dict((match.metadata_json or {}).get("match_viewer") or {})
        assert viewer.get("frames"), "the stored viewer must contain later frames for this regression"
        last_minute = float(viewer["frames"][-1]["clock_minute"])
        assert last_minute > 1

        match.status = MatchStatus.SCHEDULED.value
        match.home_score = 0
        match.away_score = 0
        match.completed_at = None
        execution = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match.id)
        )
        assert execution is not None
        execution.execution_status = "scheduled"
        execution.current_minute = 0
        execution.elapsed_broadcast_seconds = 0
        execution.clock_phase = "pre_match"
        execution.checkpoint_json = {}
        execution.committed_events_json = []
        flag_modified(match, "metadata_json")
        flag_modified(execution, "checkpoint_json")
        session.commit()
        match_id = match.id

    payload = _payload(session_factory, match_id)
    assert payload["status"] == "SCHEDULED"
    assert payload["phase"] == "pre_match"
    assert payload["is_live"] is False
    assert payload["minute"] == 0
    assert payload["time_seconds"] == 0
    assert payload["home"]["score"] == 0
    assert payload["away"]["score"] == 0
    assert payload["broadcast_session"]["status"] == "pre_match"

    unity = build_unity_live_payload_for_app(_app(session_factory), match_id)
    assert unity["status"] == "pre_match"
    assert unity["clockMinute"] == 0
    assert unity["homeScore"] == 0
    assert unity["awayScore"] == 0
    assert unity["isLive"] is False


def test_active_match_survives_an_empty_api_runtime() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        _, execution, _ = service.step_execution(match.id, step_minutes=30, step_interval_seconds=0)
        session.commit()
        match_id = match.id
        expected_home = int(match.home_score or 0)
        expected_away = int(match.away_score or 0)
        expected_elapsed = int(execution.elapsed_broadcast_seconds)
        expected_events = len(execution.committed_events_json or [])
        revision = int(execution.execution_revision)

    fresh = _app(session_factory)
    assert fresh.state.live_match_hub._matches == {}
    payload = _v2_match_state_payload(match_id, fresh)
    assert payload["status"] == "LIVE"
    assert payload["is_live"] is True
    assert payload["minute"] == 30
    assert payload["phase"] == "first_half"
    assert payload["home"]["score"] == expected_home
    assert payload["away"]["score"] == expected_away
    assert payload["time_seconds"] == expected_elapsed
    assert payload["execution_revision"] == revision
    assert payload["commit_cursor"] == expected_events
    assert payload["status"] != "FT"
    assert float(payload["time_seconds"]) < float(payload["broadcast_session"]["assigned_duration_seconds"])

    unity = build_unity_live_payload_for_app(_app(session_factory), match_id)
    assert unity["status"] == "live"
    assert unity["clockMinute"] == 30
    assert unity["isLive"] is True
    assert unity["homeScore"] == expected_home
    assert unity["awayScore"] == expected_away


def test_halftime_is_not_full_time_and_a_completed_match_is() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, paused_match, _, _ = helpers._seed_canonical_fixture(session)
        _, finished_match, _, _ = helpers._seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(paused_match.id, step_interval_seconds=0)
        _, paused_execution, _ = service.step_execution(
            paused_match.id,
            step_minutes=60,
            stop_at_halftime=True,
            step_interval_seconds=0,
        )
        service.start_live_execution(finished_match.id, step_interval_seconds=0)
        service.step_execution(
            finished_match.id,
            target_minute=120,
            stop_at_halftime=False,
            resume_halftime=True,
            settle_on_completion=True,
            step_interval_seconds=0,
        )
        session.commit()
        assert paused_execution.execution_status == "paused"
        assert paused_execution.clock_phase == "halftime"
        paused_id = paused_match.id
        finished_id = finished_match.id
        finished_events = len(
            session.scalar(
                select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == finished_id)
            ).committed_events_json
            or []
        )

    paused_payload = _payload(session_factory, paused_id)
    assert paused_payload["status"] == "HALFTIME"
    assert paused_payload["phase"] == "halftime"
    assert paused_payload["is_live"] is False
    assert paused_payload["minute"] == 45
    assert paused_payload["status"] != "FT"

    finished_payload = _payload(session_factory, finished_id)
    assert finished_payload["status"] == "FT"
    assert finished_payload["phase"] == "full_time"
    assert finished_payload["is_live"] is False

    with session_factory() as session:
        service = CanonicalLiveExecutionService(session)
        service.claim_and_advance_due_executions(step_minutes=15, step_interval_seconds=0)
        session.commit()
        execution = session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == finished_id)
        )
        assert execution.execution_status == "completed"
        assert len(execution.committed_events_json or []) == finished_events


def test_stale_viewer_loses_to_the_later_checkpoint() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        service.step_execution(match.id, step_minutes=15, step_interval_seconds=0)
        session.commit()
        stale_viewer = dict((match.metadata_json or {}).get("match_viewer") or {})
        assert stale_viewer.get("frames")
        stale_last_minute = float(stale_viewer["frames"][-1]["clock_minute"])

        service.step_execution(match.id, step_minutes=30, step_interval_seconds=0)
        session.commit()
        metadata = dict(match.metadata_json or {})
        metadata["match_viewer"] = stale_viewer
        match.metadata_json = metadata
        flag_modified(match, "metadata_json")
        session.commit()
        match_id = match.id
        assert int(match.home_score or 0) >= 0
        home = int(match.home_score or 0)
        away = int(match.away_score or 0)

    payload = _payload(session_factory, match_id)
    assert payload["minute"] == 45
    assert payload["status"] == "HALFTIME"
    assert payload["phase"] == "halftime"
    assert payload["home"]["score"] == home
    assert payload["away"]["score"] == away
    assert payload["minute"] != int(round(stale_last_minute)) or stale_last_minute <= 45


def test_expired_lease_can_be_recovered_without_duplicating_events() -> None:
    helpers = _phase1()
    session_factory = helpers._setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = helpers._seed_canonical_fixture(session)
        now = datetime.now(timezone.utc)
        match.scheduled_at = now - timedelta(minutes=5)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        _, execution, _ = service.step_execution(match.id, step_minutes=15, step_interval_seconds=0)
        committed_ids = [str(item.get("event_id")) for item in execution.committed_events_json or []]
        execution.lease_owner = "crashed-worker"
        execution.lease_expires_at = now - timedelta(seconds=30)
        execution.next_step_at = now - timedelta(seconds=30)
        session.commit()

        summary = service.claim_and_advance_due_executions(
            reference_at=now,
            step_minutes=15,
            lease_owner="recovered-worker",
            step_interval_seconds=0,
        )
        session.commit()
        session.refresh(execution)
        recovered_ids = [str(item.get("event_id")) for item in execution.committed_events_json or []]

    assert summary["recovered_leases"] >= 1
    assert execution.current_minute == 30
    assert execution.execution_status == "in_progress"
    assert recovered_ids[: len(committed_ids)] == committed_ids
    assert len(recovered_ids) == len(set(recovered_ids))
    assert execution.lease_owner != "crashed-worker"
