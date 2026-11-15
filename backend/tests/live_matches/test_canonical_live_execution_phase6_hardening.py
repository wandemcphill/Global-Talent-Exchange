from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.common.enums.match_status import MatchStatus
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_match_execution import CompetitionMatchExecution
from app.models.player_match_performance import PlayerMatchPerformance
from app.services.canonical_live_execution_service import (
    CanonicalExecutionConflictError,
    CanonicalExecutionError,
    CanonicalLiveExecutionService,
    CanonicalMatchNotLiveError,
)
from backend.tests.live_matches.test_canonical_live_execution_phase1 import (
    _seed_canonical_fixture,
    _setup_session_factory,
)


def test_duplicate_kickoff_is_idempotent_and_does_not_reset_execution() -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        _, first = service.start_live_execution(match.id, step_interval_seconds=0)
        service.step_execution(match.id, step_minutes=10)
        session.commit()
        minute_after_step = int(first.current_minute)
        assert minute_after_step > 0

        _, second = service.start_live_execution(match.id, step_interval_seconds=0)
        session.commit()
        assert second.id == first.id
        assert int(second.current_minute) == minute_after_step
        count = session.scalar(
            select(func.count())
            .select_from(CompetitionMatchExecution)
            .where(CompetitionMatchExecution.match_id == match.id)
        )
        assert count == 1


def test_expired_lease_is_recovered_and_reported_with_structured_log(caplog) -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        _, execution = service.start_live_execution(
            match.id,
            step_interval_seconds=0,
            lease_owner="crashed-worker",
        )
        execution.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        execution.next_step_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

        with caplog.at_level(logging.WARNING):
            summary = service.claim_and_advance_due_executions(
                step_minutes=10,
                lease_owner="healthy-worker",
                step_interval_seconds=0,
            )
        session.commit()
        assert summary["recovered_leases"] == 1
        assert summary["advanced"] == 1
        assert summary["failed"] == 0
        assert any(
            "canonical_execution.lease_recovered" in rec.getMessage()
            and match.id in rec.getMessage()
            and "crashed-worker" in rec.getMessage()
            for rec in caplog.records
        )


def test_stale_expected_revision_and_post_fulltime_commands_are_rejected() -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        service.step_execution(match.id, step_minutes=20)
        session.commit()

        accepted = service.apply_live_tactical_command(
            match.id,
            side="home",
            actor_user_id="manager-home",
            expected_revision=1,
            idempotency_key="cmd-1",
            press_intensity=80,
        )
        session.commit()
        new_revision = int(accepted["execution_revision"])
        assert new_revision == 2

        # Same key and payload replays without a new revision.
        replay = service.apply_live_tactical_command(
            match.id,
            side="home",
            actor_user_id="manager-home",
            expected_revision=1,
            idempotency_key="cmd-1",
            press_intensity=80,
        )
        session.commit()
        assert int(replay["execution_revision"]) == new_revision
        assert replay.get("idempotent_replay") is True

        # Same key with a different payload is a conflict.
        with pytest.raises(CanonicalExecutionError):
            service.apply_live_tactical_command(
                match.id,
                side="home",
                actor_user_id="manager-home",
                expected_revision=1,
                idempotency_key="cmd-1",
                press_intensity=20,
            )
        session.rollback()

        # Stale revision with a fresh key is a conflict.
        with pytest.raises(CanonicalExecutionConflictError):
            service.apply_live_tactical_command(
                match.id,
                side="away",
                actor_user_id="manager-away",
                expected_revision=1,
                idempotency_key="cmd-2",
                tempo=70,
            )
        session.rollback()

        # Finish the match; later commands must be rejected.
        service.execute_to_completion(match.id)
        session.commit()
        session.refresh(match)
        assert match.status == MatchStatus.COMPLETED.value
        with pytest.raises(CanonicalMatchNotLiveError):
            service.apply_live_tactical_command(
                match.id,
                side="home",
                actor_user_id="manager-home",
                idempotency_key="cmd-3",
                tempo=60,
            )
        session.rollback()


def test_settlement_is_not_duplicated_when_repeated() -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        service.execute_to_completion(match.id)
        session.commit()
        session.refresh(match)
        assert match.status == MatchStatus.COMPLETED.value
        events_before = session.scalar(
            select(func.count()).select_from(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match.id)
        )
        perf_before = session.scalar(
            select(func.count()).select_from(PlayerMatchPerformance).where(PlayerMatchPerformance.match_id == match.id)
        )
        score = (match.home_score, match.away_score)

        execution = service.get_execution(match.id)
        assert execution is not None
        again = service.settle_completed_execution(match, execution)
        session.commit()
        assert (again.home_score, again.away_score) == score
        assert (
            session.scalar(
                select(func.count())
                .select_from(CompetitionMatchEvent)
                .where(CompetitionMatchEvent.match_id == match.id)
            )
            == events_before
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(PlayerMatchPerformance)
                .where(PlayerMatchPerformance.match_id == match.id)
            )
            == perf_before
        )


def test_halt_resume_and_termination_emit_structured_logs(caplog) -> None:
    session_factory = _setup_session_factory()
    with session_factory() as session:
        _, match, _, _ = _seed_canonical_fixture(session)
        service = CanonicalLiveExecutionService(session)
        service.start_live_execution(match.id, step_interval_seconds=0)
        with caplog.at_level(logging.INFO):
            service.halt_execution(match.id, reason="review", actor_user_id="admin-1")
            service.resume_halted_execution(match.id, actor_user_id="admin-1")
            service.cancel_or_abandon_execution(match.id, reason="unsafe", actor_user_id="admin-1")
        session.commit()
        text = "\n".join(rec.getMessage() for rec in caplog.records)
        assert "canonical_execution.halted" in text
        assert "canonical_execution.resumed" in text
        assert "canonical_execution.terminated" in text
        assert "actor_user_id=admin-1" in text
