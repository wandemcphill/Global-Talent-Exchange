from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.common.enums.match_status import MatchStatus
from app.match_engine.schemas import MatchReplayPayloadView, MatchSimulationRequest
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.match_engine.simulation.event_generator import MatchEventGenerator
from app.match_engine.simulation.live_execution import (
    MatchExecutionCheckpoint,
    advance_checkpoint,
    finalize_checkpoint,
    initialize_execution,
    resume_from_halftime,
    serialize_match_event,
)
from app.match_engine.simulation.models import MatchEvent, SimulationResult, TeamRuntimeState
from app.match_engine.simulation.offside_var import (
    BROADCAST_CATEGORY_MAX_SECONDS,
    resolve_match_broadcast_category,
)
from app.matches.lifecycle import assert_transition, is_terminal
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_match_execution import CompetitionMatchExecution
from app.models.event_backbone import EventOutbox
from app.players.performance_recorder import PlayerMatchPerformanceRecorder
from app.services.competition_lifecycle_service import CompetitionLifecycleService
from app.services.match_timeline_service import MatchTimelineService

logger = logging.getLogger(__name__)

DEFAULT_STEP_INTERVAL_SECONDS = 10
DEFAULT_HALFTIME_PAUSE_SECONDS = 15
DEFAULT_LEASE_TTL_SECONDS = 30
LIVE_EXECUTION_STATUSES = frozenset({"in_progress", "paused"})


class CanonicalExecutionError(Exception):
    status_code: int = 400
    reason_code: str = "execution_error"

    def __init__(self, detail: str, *, reason_code: str | None = None) -> None:
        self.detail = detail
        if reason_code is not None:
            self.reason_code = reason_code
        super().__init__(detail)


class CanonicalMatchNotFoundError(CanonicalExecutionError):
    status_code = 404
    reason_code = "match_not_found"


class CanonicalMatchNotLiveError(CanonicalExecutionError):
    status_code = 409
    reason_code = "match_not_live"


class CanonicalExecutionConflictError(CanonicalExecutionError):
    status_code = 409
    reason_code = "execution_conflict"


class CanonicalExecutionHaltedError(CanonicalExecutionError):
    status_code = 409
    reason_code = "match_halted"


class CanonicalExecutionValidationError(CanonicalExecutionError):
    status_code = 400
    reason_code = "invalid_execution_command"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _supports_row_locks(session: Session) -> bool:
    bind = session.get_bind()
    return bind is not None and bind.dialect.name != "sqlite"


def _extract_tactics_snapshot(state: TeamRuntimeState, revision: int) -> dict[str, Any]:
    return {
        "team_id": state.team_id,
        "team_name": state.team_name,
        "execution_revision": int(revision),
        "formation": state.current_formation,
        "mentality": state.tactics.mentality.value,
        "style": state.tactics.style.value,
        "pressing": int(state.tactics.pressing),
        "press_intensity": int(state.tactics.pressing),
        "defensive_line": int(state.tactics.defensive_line),
        "tempo": int(state.tactics.tempo),
        "aggression": int(state.tactics.aggression),
        "risk_level": int(state.tactics.aggression),
        "width": int(state.tactics.width),
        "substitution_count": int(state.substitutions_used),
        "substitutions_used": int(state.substitutions_used),
        "max_substitutions": int(state.tactics.max_substitutions),
        "active_player_ids": list(state.active_player_ids),
        "bench_player_ids": list(state.bench_player_ids),
        "yellow_carded_ids": sorted(state.yellow_carded_ids),
        "red_carded_ids": sorted(state.red_carded_ids),
        "injured_ids": sorted(state.injured_ids),
    }


def _resolve_broadcast_bounds(request: MatchSimulationRequest) -> tuple[str, int]:
    category = resolve_match_broadcast_category(
        is_final=bool(request.competition.is_final),
        stage=request.competition.stage,
        competition_type=request.competition.competition_type.value,
        approved_shorter_presentation=bool(getattr(request.competition, "approved_shorter_presentation", False)),
        metadata={
            "designated_major_knockout": bool(getattr(request.competition, "designated_major_knockout", False)),
        },
    )
    max_seconds = int(BROADCAST_CATEGORY_MAX_SECONDS[category])
    return category.value, max_seconds


def _compute_elapsed_broadcast_seconds(
    assigned_duration_seconds: int,
    current_minute: int,
    target_end_minute: int,
) -> int:
    denominator = max(90, int(target_end_minute))
    clamped_minute = max(0, min(int(current_minute), denominator))
    return min(
        int(assigned_duration_seconds),
        max(0, round((clamped_minute / denominator) * int(assigned_duration_seconds))),
    )


def _event_highlight(event_type: str) -> bool:
    return event_type in {
        "goal",
        "penalty_goal",
        "penalty_scored",
        "red_card",
        "injury",
        "fulltime",
        "halftime",
        "substitution",
        "tactical_change",
    }


class CanonicalLiveExecutionService:
    """Authoritative database-backed lifecycle and checkpoint execution owner for canonical matches."""

    def __init__(
        self,
        session: Session,
        *,
        match_service: MatchSimulationService | None = None,
        timeline_service: MatchTimelineService | None = None,
        team_factory: SyntheticSquadFactory | None = None,
        lifecycle_service: CompetitionLifecycleService | None = None,
        hub: Any | None = None,
        match_stream_service: Any | None = None,
    ) -> None:
        self.session = session
        self.match_service = match_service or MatchSimulationService()
        self.event_generator: MatchEventGenerator = self.match_service.event_generator
        self.timeline_service = timeline_service or MatchTimelineService()
        self.team_factory = team_factory or SyntheticSquadFactory()
        self.lifecycle_service = lifecycle_service or CompetitionLifecycleService(session)
        self.hub = hub
        self.match_stream_service = match_stream_service

    def _lock_match(self, match_id: str) -> CompetitionMatch | None:
        stmt = select(CompetitionMatch).where(CompetitionMatch.id == match_id)
        if _supports_row_locks(self.session):
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt.execution_options(populate_existing=True))

    def _lock_execution(self, match_id: str) -> CompetitionMatchExecution | None:
        stmt = select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
        if _supports_row_locks(self.session):
            stmt = stmt.with_for_update()
        return self.session.scalar(stmt.execution_options(populate_existing=True))

    def get_execution(self, match_id: str) -> CompetitionMatchExecution | None:
        return self.session.scalar(
            select(CompetitionMatchExecution).where(CompetitionMatchExecution.match_id == match_id)
        )

    def _build_simulation_request(
        self,
        competition: Competition,
        match: CompetitionMatch,
    ) -> MatchSimulationRequest:
        from app.services.competition_auto_runner import CompetitionAutoRunner

        runner = CompetitionAutoRunner(
            self.session,
            match_service=self.match_service,
            timeline_service=self.timeline_service,
        )
        job = runner._simulation_job(competition, match)
        request = runner.team_factory.build_request(job, session=self.session)
        request = runner._apply_owner_pre_match_tactics(request, match)
        runner._capture_institutional_match_context(match, competition, request)
        return request

    def _sync_live_metadata(
        self,
        match: CompetitionMatch,
        execution: CompetitionMatchExecution,
        checkpoint: MatchExecutionCheckpoint,
    ) -> None:
        metadata = dict(match.metadata_json or {})
        metadata["tactics"] = {
            "home": _extract_tactics_snapshot(checkpoint.home_state, execution.execution_revision),
            "away": _extract_tactics_snapshot(checkpoint.away_state, execution.execution_revision),
        }
        metadata["live_execution"] = {
            "execution_id": execution.id,
            "execution_status": execution.execution_status,
            "execution_revision": int(execution.execution_revision),
            "current_minute": int(execution.current_minute),
            "target_end_minute": int(execution.target_end_minute),
            "clock_phase": execution.clock_phase,
            "broadcast_category": execution.broadcast_category,
            "assigned_duration_seconds": int(execution.assigned_duration_seconds),
            "elapsed_broadcast_seconds": int(execution.elapsed_broadcast_seconds),
            "paused_reason": execution.paused_reason,
            "halftime_resume_at": execution.halftime_resume_at.isoformat() if execution.halftime_resume_at else None,
        }
        match.metadata_json = metadata

    def _record_raw_match_event(
        self,
        match: CompetitionMatch,
        raw_event: MatchEvent,
        *,
        revision: int,
    ) -> CompetitionMatchEvent:
        event_type = raw_event.event_type.value
        card_type = None
        if event_type == "yellow_card":
            card_type = "yellow"
        elif event_type == "red_card":
            card_type = "red"
        event_key = f"r{int(revision)}:{int(raw_event.sequence)}:{event_type}"
        meta = dict(raw_event.metadata or {})
        meta.setdefault("home_score", raw_event.home_score)
        meta.setdefault("away_score", raw_event.away_score)
        meta.setdefault("execution_revision", int(revision))
        meta.setdefault("source_event_id", raw_event.event_id)
        return self.lifecycle_service.record_match_event(
            match=match,
            event_type=event_type,
            minute=raw_event.minute,
            added_time=raw_event.added_time,
            club_id=raw_event.team_id,
            player_id=raw_event.primary_player_id,
            secondary_player_id=raw_event.secondary_player_id,
            card_type=card_type,
            highlight=_event_highlight(event_type),
            metadata_json=meta,
            sequence=raw_event.sequence,
            execution_revision=int(revision),
            event_key=event_key,
        )

    def _emit_outbox(
        self,
        *,
        event_type: str,
        match: CompetitionMatch,
        execution: CompetitionMatchExecution,
        payload: dict[str, Any],
    ) -> None:
        now = _utcnow()
        event_id = f"{match.id}:r{execution.execution_revision}:s{execution.step_sequence}:{event_type}"
        existing = self.session.scalar(select(EventOutbox.id).where(EventOutbox.event_id == event_id))
        if existing is not None:
            return
        self.session.add(
            EventOutbox(
                event_id=event_id,
                event_type=event_type,
                aggregate_type="competition_match",
                aggregate_id=match.id,
                partition_key=match.id,
                producer="canonical-live-execution",
                version=int(execution.execution_revision),
                occurred_at=now,
                payload_json=payload,
                headers_json={
                    "match_id": match.id,
                    "competition_id": match.competition_id,
                    "execution_revision": int(execution.execution_revision),
                },
                status="pending",
                relay_attempts=0,
            )
        )

    def _publish_stream_events(
        self,
        match: CompetitionMatch,
        execution: CompetitionMatchExecution,
        new_events: list[MatchEvent],
        *,
        kind: str = "step",
    ) -> None:
        if self.match_stream_service is None and self.hub is None:
            return
        payload = {
            "kind": kind,
            "match_id": match.id,
            "execution_revision": int(execution.execution_revision),
            "execution_status": execution.execution_status,
            "clock_phase": execution.clock_phase,
            "current_minute": int(execution.current_minute),
            "home_score": int(match.home_score),
            "away_score": int(match.away_score),
            "events": [serialize_match_event(ev) for ev in new_events],
        }
        if self.match_stream_service is not None:
            try:
                self.match_stream_service.publish_event(
                    match_id=match.id,
                    event_payload=payload,
                    event_type=f"match.{kind}",
                )
            except Exception:
                logger.exception("match.stream_publish_failed match_id=%s", match.id)
        if self.hub is not None and hasattr(self.hub, "sync_canonical_execution"):
            try:
                self.hub.sync_canonical_execution(match=match, execution=execution, new_events=new_events)
            except Exception:
                logger.exception("match.hub_sync_failed match_id=%s", match.id)

    def start_live_execution(
        self,
        match_id: str,
        *,
        competition: Competition | None = None,
        request: MatchSimulationRequest | None = None,
        step_interval_seconds: int = DEFAULT_STEP_INTERVAL_SECONDS,
        lease_owner: str | None = None,
        lease_ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
    ) -> tuple[CompetitionMatch, CompetitionMatchExecution]:
        """Atomically start canonical progressive live execution for a scheduled/queued match."""

        match = self._lock_match(match_id)
        if match is None:
            raise CanonicalMatchNotFoundError(f"Canonical match '{match_id}' was not found.")
        if is_terminal(match.status) or match.completed_at is not None:
            raise CanonicalMatchNotLiveError(f"Canonical match '{match_id}' is already in terminal state '{match.status}'.")

        existing = self._lock_execution(match_id)
        if existing is not None:
            if existing.execution_status in LIVE_EXECUTION_STATUSES or existing.execution_status == "halted":
                return match, existing
            if existing.execution_status == "completed":
                raise CanonicalMatchNotLiveError(f"Canonical match '{match_id}' execution already settled.")

        resolved_comp = competition or self.session.get(Competition, match.competition_id)
        if resolved_comp is None and request is None:
            raise CanonicalMatchNotFoundError(
                f"Competition '{match.competition_id}' for match '{match_id}' was not found."
            )

        assert_transition(match.status, MatchStatus.IN_PROGRESS.value, match_id=match.id)
        sim_request = request or self._build_simulation_request(resolved_comp, match)  # type: ignore[arg-type]
        category_value, max_duration_seconds = _resolve_broadcast_bounds(sim_request)
        checkpoint = initialize_execution(self.event_generator, sim_request, revision=1)
        now = _utcnow()

        match.status = MatchStatus.IN_PROGRESS.value
        match.home_score = 0
        match.away_score = 0
        match.winner_club_id = None
        match.decided_by_penalties = False
        match.stats_applied = False
        match.completed_at = None

        execution = existing or CompetitionMatchExecution(
            match_id=match.id,
            competition_id=match.competition_id,
        )
        execution.execution_status = "in_progress"
        execution.execution_revision = 1
        execution.current_minute = checkpoint.current_minute
        execution.target_end_minute = checkpoint.target_end_minute
        execution.step_sequence = 0
        execution.last_event_sequence = max(0, checkpoint.next_event_sequence - 1)
        execution.clock_phase = checkpoint.clock_phase
        execution.broadcast_category = category_value
        execution.assigned_duration_seconds = max_duration_seconds
        execution.elapsed_broadcast_seconds = 0
        execution.paused_reason = None
        execution.halftime_resume_at = None
        execution.started_at = execution.started_at or now
        execution.settled_at = None
        execution.next_step_at = now + timedelta(seconds=max(0, int(step_interval_seconds)))
        execution.lease_owner = lease_owner
        execution.lease_expires_at = now + timedelta(seconds=max(1, int(lease_ttl_seconds))) if lease_owner else None
        execution.attempt_count = int(execution.attempt_count or 0) + 1
        execution.last_error = None
        execution.simulation_request_json = sim_request.model_dump(mode="json")
        execution.checkpoint_json = checkpoint.to_dict()
        execution.home_tactics_json = _extract_tactics_snapshot(checkpoint.home_state, 1)
        execution.away_tactics_json = _extract_tactics_snapshot(checkpoint.away_state, 1)
        execution.committed_events_json = [serialize_match_event(ev) for ev in checkpoint.committed_events]
        execution.projected_tail_events_json = []
        execution.metadata_json = {
            **dict(execution.metadata_json or {}),
            "broadcast_category": category_value,
            "assigned_duration_seconds": max_duration_seconds,
        }
        if existing is None:
            self.session.add(execution)
        self.session.flush()

        for ev in checkpoint.committed_events:
            self._record_raw_match_event(match, ev, revision=execution.execution_revision)

        self._sync_live_metadata(match, execution, checkpoint)
        self._emit_outbox(
            event_type="competition.match.execution.started",
            match=match,
            execution=execution,
            payload={
                "match_id": match.id,
                "competition_id": match.competition_id,
                "execution_revision": 1,
                "broadcast_category": category_value,
                "assigned_duration_seconds": max_duration_seconds,
            },
        )
        self.session.flush()
        self._publish_stream_events(match, execution, list(checkpoint.committed_events), kind="kickoff")
        return match, execution

    def step_execution(
        self,
        match_id: str,
        *,
        step_minutes: int = 15,
        target_minute: int | None = None,
        stop_at_halftime: bool = True,
        resume_halftime: bool = False,
        settle_on_completion: bool = True,
        step_interval_seconds: int = DEFAULT_STEP_INTERVAL_SECONDS,
        halftime_pause_seconds: int = DEFAULT_HALFTIME_PAUSE_SECONDS,
        lease_owner: str | None = None,
        lease_ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
        reference_at: datetime | None = None,
    ) -> tuple[CompetitionMatch, CompetitionMatchExecution, list[MatchEvent]]:
        """Advance an active canonical match execution deterministically by one bounded checkpoint."""

        now = _as_utc(reference_at) or _utcnow()
        match = self._lock_match(match_id)
        if match is None:
            raise CanonicalMatchNotFoundError(f"Canonical match '{match_id}' was not found.")
        execution = self._lock_execution(match_id)
        if execution is None:
            raise CanonicalMatchNotFoundError(f"Canonical execution state for match '{match_id}' was not found.")

        if is_terminal(match.status) or execution.execution_status in {"completed", "cancelled", "abandoned"}:
            return match, execution, []

        if (
            lease_owner is not None
            and execution.lease_owner
            and execution.lease_owner != lease_owner
            and execution.lease_expires_at is not None
            and _as_utc(execution.lease_expires_at) > now
        ):
            raise CanonicalExecutionConflictError(
                f"Match '{match_id}' execution lease is currently held by '{execution.lease_owner}'."
            )

        if execution.execution_status == "halted" or execution.paused_reason == "admin_halt":
            return match, execution, []

        sim_request = MatchSimulationRequest.model_validate(execution.simulation_request_json)
        checkpoint = MatchExecutionCheckpoint.from_dict(
            execution.checkpoint_json,
            generator=self.event_generator,
            request=sim_request,
        )

        if execution.execution_status == "paused" or match.status == MatchStatus.PAUSED.value:
            if execution.paused_reason == "halftime":
                due = resume_halftime or (
                    execution.halftime_resume_at is not None and _as_utc(execution.halftime_resume_at) <= now
                )
                if not due:
                    return match, execution, []
                assert_transition(match.status, MatchStatus.IN_PROGRESS.value, match_id=match.id)
                match.status = MatchStatus.IN_PROGRESS.value
                execution.execution_status = "in_progress"
                execution.paused_reason = None
                execution.halftime_resume_at = None
                checkpoint = resume_from_halftime(checkpoint)
            else:
                return match, execution, []

        if lease_owner is not None:
            execution.lease_owner = lease_owner
            execution.lease_expires_at = now + timedelta(seconds=max(1, int(lease_ttl_seconds)))

        until = (
            int(target_minute)
            if target_minute is not None
            else min(checkpoint.current_minute + max(1, int(step_minutes)), checkpoint.target_end_minute)
        )
        checkpoint, new_events = advance_checkpoint(
            self.event_generator,
            sim_request,
            checkpoint,
            until_minute=until,
            stop_at_halftime=stop_at_halftime,
        )

        execution.current_minute = int(checkpoint.current_minute)
        execution.target_end_minute = int(checkpoint.target_end_minute)
        execution.clock_phase = checkpoint.clock_phase
        execution.step_sequence = int(execution.step_sequence) + 1
        execution.last_event_sequence = max(0, checkpoint.next_event_sequence - 1)
        execution.elapsed_broadcast_seconds = _compute_elapsed_broadcast_seconds(
            execution.assigned_duration_seconds,
            checkpoint.current_minute,
            checkpoint.target_end_minute,
        )
        execution.checkpoint_json = checkpoint.to_dict()
        execution.home_tactics_json = _extract_tactics_snapshot(checkpoint.home_state, execution.execution_revision)
        execution.away_tactics_json = _extract_tactics_snapshot(checkpoint.away_state, execution.execution_revision)
        execution.committed_events_json = [serialize_match_event(ev) for ev in checkpoint.committed_events]
        execution.last_error = None

        match.home_score = int(checkpoint.home_state.stats.goals)
        match.away_score = int(checkpoint.away_state.stats.goals)

        for ev in new_events:
            self._record_raw_match_event(match, ev, revision=execution.execution_revision)

        if checkpoint.clock_phase == "halftime":
            assert_transition(match.status, MatchStatus.PAUSED.value, match_id=match.id)
            match.status = MatchStatus.PAUSED.value
            execution.execution_status = "paused"
            execution.paused_reason = "halftime"
            execution.halftime_resume_at = now + timedelta(seconds=max(0, int(halftime_pause_seconds)))
            execution.next_step_at = execution.halftime_resume_at
            execution.lease_owner = None
            execution.lease_expires_at = None
            self._sync_live_metadata(match, execution, checkpoint)
            self.session.flush()
            self._publish_stream_events(match, execution, new_events, kind="halftime")
            return match, execution, new_events

        if checkpoint.clock_phase == "completed":
            execution.next_step_at = None
            execution.lease_owner = None
            execution.lease_expires_at = None
            self._sync_live_metadata(match, execution, checkpoint)
            if settle_on_completion:
                self.settle_completed_execution(
                    match,
                    execution,
                    request=sim_request,
                    checkpoint=checkpoint,
                )
            self.session.flush()
            self._publish_stream_events(match, execution, new_events, kind="fulltime")
            return match, execution, new_events

        execution.execution_status = "in_progress"
        execution.next_step_at = now + timedelta(seconds=max(0, int(step_interval_seconds)))
        execution.lease_owner = None
        execution.lease_expires_at = None
        self._sync_live_metadata(match, execution, checkpoint)
        self.session.flush()
        self._publish_stream_events(match, execution, new_events, kind="step")
        return match, execution, new_events

    def execute_to_completion(
        self,
        match_id: str,
        *,
        competition: Competition | None = None,
        request: MatchSimulationRequest | None = None,
        settle: bool = True,
    ) -> tuple[CompetitionMatch, CompetitionMatchExecution, SimulationResult, MatchReplayPayloadView]:
        """Run an entire canonical match cleanly through the checkpoint engine to full-time."""

        execution = self.get_execution(match_id)
        if execution is None:
            match, execution = self.start_live_execution(
                match_id,
                competition=competition,
                request=request,
                step_interval_seconds=0,
            )
        else:
            match = self._lock_match(match_id)
            if match is None:
                raise CanonicalMatchNotFoundError(f"Canonical match '{match_id}' was not found.")
        if execution.execution_status != "completed":
            match, execution, _ = self.step_execution(
                match_id,
                target_minute=120,
                stop_at_halftime=False,
                resume_halftime=True,
                settle_on_completion=settle,
            )
        sim_request = MatchSimulationRequest.model_validate(execution.simulation_request_json)
        checkpoint = MatchExecutionCheckpoint.from_dict(
            execution.checkpoint_json,
            generator=self.event_generator,
            request=sim_request,
        )
        result = finalize_checkpoint(self.event_generator, sim_request, checkpoint)
        replay_payload = self.match_service.build_replay_payload_from_result(sim_request, result)
        return match, execution, result, replay_payload

    def settle_completed_execution(
        self,
        match: CompetitionMatch,
        execution: CompetitionMatchExecution,
        *,
        request: MatchSimulationRequest | None = None,
        checkpoint: MatchExecutionCheckpoint | None = None,
    ) -> CompetitionMatch:
        """Atomically reconcile events, viewer replay, standings, performances, and projections at FT."""

        if match.status == MatchStatus.COMPLETED.value and match.stats_applied and execution.execution_status == "completed":
            return match

        sim_request = request or MatchSimulationRequest.model_validate(execution.simulation_request_json)
        resolved_checkpoint = checkpoint or MatchExecutionCheckpoint.from_dict(
            execution.checkpoint_json,
            generator=self.event_generator,
            request=sim_request,
        )
        result = finalize_checkpoint(self.event_generator, sim_request, resolved_checkpoint)
        replay_payload = self.match_service.build_replay_payload_from_result(sim_request, result)

        # Remove any stale non-authoritative or prior-revision rows before reconciling the final timeline.
        existing_rows = list(
            self.session.scalars(
                select(CompetitionMatchEvent).where(CompetitionMatchEvent.match_id == match.id)
            ).all()
        )
        canonical_keys: set[str] = set()
        for timeline_event in replay_payload.timeline.events:
            event_type = getattr(timeline_event.event_type, "value", str(timeline_event.event_type))
            seq = int(getattr(timeline_event, "sequence", 0) or 0)
            canonical_keys.add(f"r{int(execution.execution_revision)}:{seq}:{event_type}")

        stale_ids = [
            row.id
            for row in existing_rows
            if row.event_key is None or row.event_key not in canonical_keys
        ]
        if stale_ids:
            self.session.execute(
                delete(CompetitionMatchEvent).where(CompetitionMatchEvent.id.in_(stale_ids))
            )
            self.session.flush()

        for timeline_event in replay_payload.timeline.events:
            event_type = getattr(timeline_event.event_type, "value", str(timeline_event.event_type))
            card_type = None
            if event_type == "yellow_card":
                card_type = "yellow"
            elif event_type == "red_card":
                card_type = "red"
            seq = int(getattr(timeline_event, "sequence", 0) or 0)
            event_key = f"r{int(execution.execution_revision)}:{seq}:{event_type}"
            self.lifecycle_service.record_match_event(
                match=match,
                event_type=event_type,
                minute=timeline_event.minute,
                added_time=timeline_event.added_time,
                club_id=timeline_event.team_id,
                player_id=timeline_event.primary_player.player_id if timeline_event.primary_player else None,
                secondary_player_id=(
                    timeline_event.secondary_player.player_id if timeline_event.secondary_player else None
                ),
                card_type=card_type,
                highlight=_event_highlight(event_type),
                metadata_json={
                    "commentary": timeline_event.commentary,
                    "analyst_commentary": timeline_event.analyst_commentary,
                    "clock_label": timeline_event.clock_label,
                    "home_score": timeline_event.home_score,
                    "away_score": timeline_event.away_score,
                    "presentation_second": timeline_event.presentation_second,
                    "execution_revision": int(execution.execution_revision),
                    **dict(timeline_event.metadata or {}),
                },
                sequence=seq,
                execution_revision=int(execution.execution_revision),
                event_key=event_key,
            )

        viewer_payload = self.timeline_service.build_from_replay_payload(replay_payload)
        match.metadata_json = {
            **dict(match.metadata_json or {}),
            "match_viewer": viewer_payload.model_dump(mode="json"),
            "replay_payload": replay_payload.model_dump(mode="json"),
            "simulation_summary": replay_payload.summary.model_dump(mode="json"),
            "simulation_seed": replay_payload.seed,
            "tactics": {
                "home": _extract_tactics_snapshot(resolved_checkpoint.home_state, execution.execution_revision),
                "away": _extract_tactics_snapshot(resolved_checkpoint.away_state, execution.execution_revision),
            },
        }

        completed = self.lifecycle_service.complete_match(
            match=match,
            home_score=replay_payload.summary.home_score,
            away_score=replay_payload.summary.away_score,
            decided_by_penalties=replay_payload.summary.decided_by_penalties,
            winner_club_id=replay_payload.summary.winner_team_id,
        )

        # Record per-player stats strictly inside savepoint after completion timestamp exists.
        try:
            with self.session.begin_nested():
                PlayerMatchPerformanceRecorder(self.session).record_match(
                    match=completed,
                    player_stats=replay_payload.summary.player_stats,
                )
        except SQLAlchemyError:
            logger.exception(
                "canonical_execution.performance_recording_failed match_id=%s competition_id=%s",
                completed.id,
                completed.competition_id,
            )

        try:
            from app.owner_console.canonical_match_projection import project_completed_canonical_match

            with self.session.begin_nested():
                project_completed_canonical_match(self.session, completed.id)
        except Exception:
            logger.exception(
                "canonical_match.institutional_projection_deferred match_id=%s",
                completed.id,
            )

        execution.execution_status = "completed"
        execution.clock_phase = "completed"
        execution.settled_at = completed.completed_at or _utcnow()
        execution.next_step_at = None
        execution.lease_owner = None
        execution.lease_expires_at = None
        execution.checkpoint_json = resolved_checkpoint.to_dict()
        execution.committed_events_json = [serialize_match_event(ev) for ev in resolved_checkpoint.committed_events]
        execution.projected_tail_events_json = []
        self._sync_live_metadata(completed, execution, resolved_checkpoint)
        self._emit_outbox(
            event_type="competition.match.execution.settled",
            match=completed,
            execution=execution,
            payload={
                "match_id": completed.id,
                "competition_id": completed.competition_id,
                "execution_revision": int(execution.execution_revision),
                "home_score": int(completed.home_score),
                "away_score": int(completed.away_score),
                "winner_club_id": completed.winner_club_id,
                "decided_by_penalties": bool(completed.decided_by_penalties),
            },
        )
        self.session.flush()
        return completed

    def halt_execution(
        self,
        match_id: str,
        *,
        reason: str | None = None,
        actor_user_id: str | None = None,
    ) -> tuple[CompetitionMatch, CompetitionMatchExecution]:
        match = self._lock_match(match_id)
        if match is None:
            raise CanonicalMatchNotFoundError(f"Canonical match '{match_id}' was not found.")
        execution = self._lock_execution(match_id)
        if execution is None:
            raise CanonicalMatchNotFoundError(f"Canonical execution state for match '{match_id}' was not found.")
        if is_terminal(match.status):
            raise CanonicalMatchNotLiveError(f"Match '{match_id}' is already terminal ('{match.status}').")

        assert_transition(match.status, MatchStatus.PAUSED.value, match_id=match.id)
        match.status = MatchStatus.PAUSED.value
        execution.execution_status = "halted"
        execution.paused_reason = "admin_halt"
        execution.next_step_at = None
        execution.lease_owner = None
        execution.lease_expires_at = None
        halt_info = {
            "enabled": True,
            "reason": (reason or "").strip() or None,
            "actor_user_id": actor_user_id,
            "halted_at": _utcnow().isoformat(),
        }
        execution.metadata_json = {**dict(execution.metadata_json or {}), "admin_halt": halt_info}
        match.metadata_json = {**dict(match.metadata_json or {}), "admin_halt": halt_info}
        if self.hub is not None:
            self.hub.halt_match(match.id, reason=reason, actor_user_id=actor_user_id)
        self.session.flush()
        return match, execution

    def resume_halted_execution(
        self,
        match_id: str,
        *,
        actor_user_id: str | None = None,
        step_interval_seconds: int = DEFAULT_STEP_INTERVAL_SECONDS,
    ) -> tuple[CompetitionMatch, CompetitionMatchExecution]:
        match = self._lock_match(match_id)
        if match is None:
            raise CanonicalMatchNotFoundError(f"Canonical match '{match_id}' was not found.")
        execution = self._lock_execution(match_id)
        if execution is None:
            raise CanonicalMatchNotFoundError(f"Canonical execution state for match '{match_id}' was not found.")
        if execution.execution_status != "halted":
            raise CanonicalExecutionConflictError(f"Match '{match_id}' is not halted ('{execution.execution_status}').")

        now = _utcnow()
        sim_request = MatchSimulationRequest.model_validate(execution.simulation_request_json)
        checkpoint = MatchExecutionCheckpoint.from_dict(
            execution.checkpoint_json,
            generator=self.event_generator,
            request=sim_request,
        )
        if checkpoint.clock_phase == "halftime":
            match.status = MatchStatus.PAUSED.value
            execution.execution_status = "paused"
            execution.paused_reason = "halftime"
            execution.halftime_resume_at = now
            execution.next_step_at = now
        else:
            assert_transition(match.status, MatchStatus.IN_PROGRESS.value, match_id=match.id)
            match.status = MatchStatus.IN_PROGRESS.value
            execution.execution_status = "in_progress"
            execution.paused_reason = None
            execution.next_step_at = now + timedelta(seconds=max(0, int(step_interval_seconds)))

        exec_meta = dict(execution.metadata_json or {})
        exec_meta["admin_halt"] = {"enabled": False, "resumed_by": actor_user_id, "resumed_at": now.isoformat()}
        execution.metadata_json = exec_meta
        match_meta = dict(match.metadata_json or {})
        match_meta["admin_halt"] = exec_meta["admin_halt"]
        match.metadata_json = match_meta
        if self.hub is not None:
            self.hub.clear_match_halt(match.id)
        self._sync_live_metadata(match, execution, checkpoint)
        self.session.flush()
        return match, execution

    def cancel_or_abandon_execution(
        self,
        match_id: str,
        *,
        reason: str | None = None,
        actor_user_id: str | None = None,
    ) -> CompetitionMatch:
        match = self._lock_match(match_id)
        if match is None:
            raise CanonicalMatchNotFoundError(f"Canonical match '{match_id}' was not found.")
        execution = self._lock_execution(match_id)
        if is_terminal(match.status):
            raise CanonicalMatchNotLiveError(f"Match '{match_id}' is already terminal ('{match.status}').")

        target_status = (
            MatchStatus.ABANDONED.value
            if match.status in {MatchStatus.IN_PROGRESS.value, MatchStatus.PAUSED.value}
            else MatchStatus.CANCELLED.value
        )
        assert_transition(match.status, target_status, match_id=match.id)
        match.status = target_status
        match.completed_at = None
        match.stats_applied = False
        match.winner_club_id = None
        cancel_meta = {
            "status": target_status,
            "reason": (reason or "").strip() or None,
            "actor_user_id": actor_user_id,
            "updated_at": _utcnow().isoformat(),
        }
        match.metadata_json = {**dict(match.metadata_json or {}), "termination": cancel_meta}
        if execution is not None:
            execution.execution_status = target_status
            execution.next_step_at = None
            execution.lease_owner = None
            execution.lease_expires_at = None
            execution.metadata_json = {**dict(execution.metadata_json or {}), "termination": cancel_meta}
        if self.hub is not None:
            self.hub.halt_match(match.id, reason=reason or target_status, actor_user_id=actor_user_id)
        self.session.flush()
        return match

    def claim_and_advance_due_executions(
        self,
        *,
        reference_at: datetime | None = None,
        step_minutes: int = 15,
        limit: int = 50,
        lease_owner: str = "canonical-live-worker",
        step_interval_seconds: int = DEFAULT_STEP_INTERVAL_SECONDS,
        halftime_pause_seconds: int = DEFAULT_HALFTIME_PAUSE_SECONDS,
    ) -> dict[str, Any]:
        """Advance due active executions and recover stalled expired leases without losing state."""

        now = _as_utc(reference_at) or _utcnow()
        stmt = (
            select(CompetitionMatchExecution)
            .where(
                or_(
                    and_(
                        CompetitionMatchExecution.execution_status == "in_progress",
                        or_(
                            CompetitionMatchExecution.next_step_at.is_(None),
                            CompetitionMatchExecution.next_step_at <= now,
                        ),
                    ),
                    and_(
                        CompetitionMatchExecution.execution_status == "paused",
                        CompetitionMatchExecution.paused_reason == "halftime",
                        or_(
                            CompetitionMatchExecution.halftime_resume_at.is_(None),
                            CompetitionMatchExecution.halftime_resume_at <= now,
                        ),
                    ),
                ),
                or_(
                    CompetitionMatchExecution.lease_expires_at.is_(None),
                    CompetitionMatchExecution.lease_expires_at <= now,
                    CompetitionMatchExecution.lease_owner == lease_owner,
                ),
            )
            .order_by(
                CompetitionMatchExecution.next_step_at.asc().nullslast(),
                CompetitionMatchExecution.updated_at.asc(),
            )
            .limit(max(1, int(limit)))
        )
        candidates = list(self.session.scalars(stmt).all())
        advanced = 0
        settled = 0
        settled_match_ids: list[str] = []
        failed = 0
        errors: list[str] = []

        for item in candidates:
            match_id = item.match_id
            # Clear expired leases belonging to a crashed worker before taking ownership.
            if (
                item.lease_owner
                and item.lease_owner != lease_owner
                and item.lease_expires_at is not None
                and _as_utc(item.lease_expires_at) <= now
            ):
                item.lease_owner = None
                item.lease_expires_at = None
                self.session.flush()
            try:
                with self.session.begin_nested():
                    match, updated_exec, _ = self.step_execution(
                        match_id,
                        step_minutes=step_minutes,
                        stop_at_halftime=True,
                        resume_halftime=True,
                        settle_on_completion=True,
                        step_interval_seconds=step_interval_seconds,
                        halftime_pause_seconds=halftime_pause_seconds,
                        lease_owner=lease_owner,
                        reference_at=now,
                    )
                    advanced += 1
                    if updated_exec.execution_status == "completed" and match.status == MatchStatus.COMPLETED.value:
                        settled += 1
                        settled_match_ids.append(match.id)
            except Exception as exc:
                failed += 1
                errors.append(f"{match_id}: {exc}")
                logger.exception("canonical_execution.step_failed match_id=%s", match_id)
                try:
                    with self.session.begin_nested():
                        row = self._lock_execution(match_id)
                        if row is not None:
                            row.attempt_count = int(row.attempt_count or 0) + 1
                            row.last_error = str(exc)
                            row.lease_owner = None
                            row.lease_expires_at = None
                            self.session.flush()
                except Exception:
                    logger.exception("canonical_execution.error_record_failed match_id=%s", match_id)

        return {
            "discovered": len(candidates),
            "advanced": advanced,
            "settled": settled,
            "settled_match_ids": settled_match_ids,
            "failed": failed,
            "errors": errors,
        }


__all__ = [
    "CanonicalExecutionConflictError",
    "CanonicalExecutionError",
    "CanonicalExecutionHaltedError",
    "CanonicalExecutionValidationError",
    "CanonicalLiveExecutionService",
    "CanonicalMatchNotFoundError",
    "CanonicalMatchNotLiveError",
]
