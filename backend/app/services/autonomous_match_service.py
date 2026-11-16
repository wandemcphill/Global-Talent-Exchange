from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.match_status import MatchStatus
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.services.competition_auto_runner import CompetitionAutoRunner
from app.services.world_clock_service import WorldClockService

logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _supports_row_locks(session: Session) -> bool:
    bind = session.get_bind()
    dialect = getattr(bind, "dialect", None)
    return bool(getattr(dialect, "name", "") not in {"sqlite"})


@dataclass(slots=True)
class AutonomousMatchExecutionService:
    session: Session
    world_clock: WorldClockService = field(init=False)
    auto_runner: CompetitionAutoRunner = field(init=False)

    def __post_init__(self) -> None:
        self.world_clock = WorldClockService(self.session)
        self.auto_runner = CompetitionAutoRunner(self.session)

    def scan_and_execute_due_fixtures(
        self,
        *,
        reference_at: datetime | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Discover and execute all fixtures whose scheduled kickoff has arrived.

        Picks up fixtures missed during downtime in chronological order.
        Guarded against concurrent workers via row locking and state transitions.
        """
        eval_time = _as_utc(reference_at) or self.world_clock.now_virtual()

        # 1. Discover candidate due matches
        stmt = (
            select(CompetitionMatch)
            .where(
                CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                or_(
                    CompetitionMatch.scheduled_at <= eval_time,
                    and_(
                        CompetitionMatch.scheduled_at.is_(None),
                        CompetitionMatch.match_date.is_not(None),
                    ),
                    CompetitionMatch.scheduled_at.is_(None),
                ),
            )
            .order_by(
                CompetitionMatch.scheduled_at.asc().nullslast(),
                CompetitionMatch.match_date.asc().nullslast(),
                CompetitionMatch.created_at.asc(),
            )
            .limit(max(1, limit))
        )

        if _supports_row_locks(self.session):
            stmt = stmt.with_for_update(skip_locked=True)

        candidate_matches = list(self.session.scalars(stmt).all())

        # Resolve authoritative kickoff; exclude fixtures whose kickoff is unresolved or future
        executable_matches: list[tuple[CompetitionMatch, Competition, datetime]] = []
        for match in candidate_matches:
            comp = self.session.get(Competition, match.competition_id)
            if comp is None:
                continue
            kickoff = self.auto_runner.effective_kickoff_at(comp, match)
            if kickoff is None or kickoff > eval_time:
                continue
            if match.scheduled_at is None:
                match.scheduled_at = kickoff
            executable_matches.append((match, comp, kickoff))

        executed = 0
        failed = 0
        errors: list[str] = []
        settled_competitions: list[str] = []
        advanced_competitions: list[str] = []

        # Track competitions affected so we can finalize/advance them once their round completes
        competitions_to_check: dict[str, Competition] = {}

        for match, comp, kickoff in executable_matches:
            competitions_to_check[comp.id] = comp

            # If competition is not yet active (e.g. SEEDED), launch it
            comp_status = CompetitionStatus(comp.status)
            if comp_status is CompetitionStatus.SEEDED or self.auto_runner._should_launch(comp, now_virtual=eval_time):
                try:
                    with self.session.begin_nested():
                        self.auto_runner.lifecycle_service.launch_competition(comp)
                except Exception as exc:
                    logger.warning("Failed to auto-launch competition %s: %s", comp.id, exc)

            try:
                with self.session.begin_nested():
                    # Mark in-progress to claim fixture
                    match.status = MatchStatus.IN_PROGRESS.value
                    self.session.flush()

                    # Simulate through canonical MatchSimulationService & SyntheticSquadFactory
                    self.auto_runner._simulate_match(comp, match)
                    self.session.flush()
                executed += 1
            except Exception as exc:
                failed += 1
                errors.append(f"Match {match.id}: {exc}")
                logger.exception("Error executing due fixture %s in competition %s", match.id, comp.id)
                # Atomic savepoint rollback: clean up partial writes, restore SCHEDULED status, record retry
                try:
                    with self.session.begin_nested():
                        self.session.refresh(match)
                        match.status = MatchStatus.SCHEDULED.value
                        meta = dict(match.metadata_json or {})
                        meta["execution_attempts"] = int(meta.get("execution_attempts", 0)) + 1
                        meta["last_execution_error"] = str(exc)
                        meta["last_attempt_virtual_at"] = eval_time.isoformat()
                        match.metadata_json = meta
                        self.session.flush()
                except Exception as meta_exc:
                    logger.warning("Failed to record retry metadata on match %s: %s", match.id, meta_exc)

        # 2. Check and advance / finalize competitions where all matches in round are complete
        for comp_id, comp in competitions_to_check.items():
            try:
                with self.session.begin_nested():
                    self.session.refresh(comp)
                    matches = self.auto_runner._matches(comp.id)
                    if matches and self.auto_runner._all_matches_complete(matches):
                        if CompetitionFormat(comp.format) is CompetitionFormat.LEAGUE:
                            if CompetitionStatus(comp.status) is not CompetitionStatus.SETTLED:
                                self.auto_runner.lifecycle_service.finalize_competition(comp, settle=True)
                                settled_competitions.append(comp.id)
                        else:
                            prev_round = comp.current_round
                            self.auto_runner.lifecycle_service.advance_competition(comp, force=False)
                            matches_after = self.auto_runner._matches(comp.id)
                            if comp.current_round != prev_round:
                                advanced_competitions.append(comp.id)
                            if matches_after and self.auto_runner._all_matches_complete(matches_after):
                                if CompetitionStatus(comp.status) is not CompetitionStatus.SETTLED:
                                    self.auto_runner.lifecycle_service.finalize_competition(comp, settle=True)
                                    settled_competitions.append(comp.id)
                    self.session.flush()
            except Exception as exc:
                logger.exception("Failed to advance/settle competition %s: %s", comp_id, exc)

        # 3. Check for open competitions that are due to launch
        launched_competitions: list[str] = []
        pending_launch = list(
            self.session.scalars(
                select(Competition).where(
                    Competition.status.in_(
                        [
                            CompetitionStatus.OPEN.value,
                            CompetitionStatus.OPEN_FOR_JOIN.value,
                            CompetitionStatus.PUBLISHED.value,
                            CompetitionStatus.SEEDED.value,
                        ]
                    )
                )
            ).all()
        )
        for comp in pending_launch:
            if self.auto_runner._should_launch(comp, now_virtual=eval_time):
                try:
                    with self.session.begin_nested():
                        self.auto_runner.lifecycle_service.launch_competition(comp)
                        launched_competitions.append(comp.id)
                        self.session.flush()
                except Exception as exc:
                    logger.warning("Failed to auto-launch pending competition %s: %s", comp.id, exc)

        execution_status = "success"
        if failed:
            execution_status = "partial_failure" if executed else "failure"

        return {
            "status": execution_status,
            "eval_time": eval_time.isoformat(),
            "discovered_due": len(executable_matches),
            "executed": executed,
            "failed": failed,
            "settled_competitions": settled_competitions,
            "advanced_competitions": advanced_competitions,
            "launched_competitions": launched_competitions,
            "errors": errors,
        }

    def start_and_step_live_fixtures(
        self,
        *,
        reference_at: datetime | None = None,
        step_minutes: int = 15,
        limit: int = 50,
        lease_owner: str = "autonomous-live-worker",
        step_interval_seconds: int = 10,
    ) -> dict[str, Any]:
        """Start due fixtures as progressive canonical executions and advance active matches."""
        from app.services.canonical_live_execution_service import CanonicalLiveExecutionService

        eval_time = _as_utc(reference_at) or self.world_clock.now_virtual()
        live_service = CanonicalLiveExecutionService(
            self.session,
            match_service=self.auto_runner.match_service,
            timeline_service=self.auto_runner.timeline_service,
            team_factory=self.auto_runner.team_factory,
            lifecycle_service=self.auto_runner.lifecycle_service,
        )

        step_summary = live_service.claim_and_advance_due_executions(
            reference_at=eval_time,
            step_minutes=step_minutes,
            limit=limit,
            lease_owner=lease_owner,
            step_interval_seconds=step_interval_seconds,
        )

        stmt = (
            select(CompetitionMatch)
            .where(
                CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                or_(
                    CompetitionMatch.scheduled_at <= eval_time,
                    CompetitionMatch.scheduled_at.is_(None),
                ),
            )
            .order_by(
                CompetitionMatch.scheduled_at.asc().nullslast(),
                CompetitionMatch.match_date.asc().nullslast(),
                CompetitionMatch.created_at.asc(),
            )
            .limit(max(1, limit))
        )
        if _supports_row_locks(self.session):
            stmt = stmt.with_for_update(skip_locked=True)
        candidates = list(self.session.scalars(stmt).all())

        started = 0
        errors: list[str] = []
        affected_competitions: dict[str, Competition] = {}
        for settled_match_id in step_summary.get("settled_match_ids", []):
            settled_match = self.session.get(CompetitionMatch, settled_match_id)
            if settled_match is not None:
                settled_comp = self.session.get(Competition, settled_match.competition_id)
                if settled_comp is not None:
                    affected_competitions[settled_comp.id] = settled_comp
        for match in candidates:
            comp = self.session.get(Competition, match.competition_id)
            if comp is None:
                continue
            kickoff = self.auto_runner.effective_kickoff_at(comp, match)
            if kickoff is None or kickoff > eval_time:
                continue
            if match.scheduled_at is None:
                match.scheduled_at = kickoff
            affected_competitions[comp.id] = comp
            comp_status = CompetitionStatus(comp.status)
            if comp_status is CompetitionStatus.SEEDED or self.auto_runner._should_launch(comp, now_virtual=eval_time):
                try:
                    with self.session.begin_nested():
                        self.auto_runner.lifecycle_service.launch_competition(comp)
                except Exception as exc:
                    logger.warning("Failed to auto-launch competition %s: %s", comp.id, exc)
            try:
                with self.session.begin_nested():
                    live_service.start_live_execution(
                        match.id,
                        competition=comp,
                        step_interval_seconds=step_interval_seconds,
                        lease_owner=lease_owner,
                    )
                    live_service.step_execution(
                        match.id,
                        step_minutes=step_minutes,
                        stop_at_halftime=True,
                        settle_on_completion=True,
                        step_interval_seconds=step_interval_seconds,
                        lease_owner=lease_owner,
                        reference_at=eval_time,
                    )
                started += 1
            except Exception as exc:
                errors.append(f"Match {match.id}: {exc}")
                logger.exception("Failed starting live canonical fixture %s", match.id)

        settled_competitions: list[str] = []
        advanced_competitions: list[str] = []
        for comp_id, comp in affected_competitions.items():
            try:
                with self.session.begin_nested():
                    self.session.refresh(comp)
                    matches = self.auto_runner._matches(comp.id)
                    if matches and self.auto_runner._all_matches_complete(matches):
                        if CompetitionFormat(comp.format) is CompetitionFormat.LEAGUE:
                            if CompetitionStatus(comp.status) is not CompetitionStatus.SETTLED:
                                self.auto_runner.lifecycle_service.finalize_competition(comp, settle=True)
                                settled_competitions.append(comp.id)
                        else:
                            prev_round = comp.current_round
                            self.auto_runner.lifecycle_service.advance_competition(comp, force=False)
                            matches_after = self.auto_runner._matches(comp.id)
                            if comp.current_round != prev_round:
                                advanced_competitions.append(comp.id)
                            if matches_after and self.auto_runner._all_matches_complete(matches_after):
                                if CompetitionStatus(comp.status) is not CompetitionStatus.SETTLED:
                                    self.auto_runner.lifecycle_service.finalize_competition(comp, settle=True)
                                    settled_competitions.append(comp.id)
            except Exception as exc:
                logger.exception("Failed checking competition progression %s: %s", comp_id, exc)

        return {
            "eval_time": eval_time.isoformat(),
            "started": started,
            **step_summary,
            "errors": [*errors, *step_summary.get("errors", [])],
            "settled_competitions": settled_competitions,
            "advanced_competitions": advanced_competitions,
        }

    def get_health_telemetry(self) -> dict[str, Any]:
        """Return operational telemetry on clock, overdue fixtures, and worker state."""
        eval_time = self.world_clock.now_virtual()
        clock_state = self.world_clock.get_or_create_state()
        settings = self.world_clock._get_settings()
        if settings is None:
            worker_mode = "unknown"
        elif settings.kafka_brokers and settings.kafka_simulation_consumer_enabled:
            worker_mode = "kafka_consumer"
        elif getattr(settings, "autonomous_fixture_execution_enabled", False):
            worker_mode = "database_polling"
        else:
            worker_mode = "disabled"

        overdue_count = (
            self.session.scalar(
                select(func.count(CompetitionMatch.id)).where(
                    CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                    CompetitionMatch.scheduled_at <= eval_time,
                )
            )
            or 0
        )

        oldest_overdue = self.session.scalar(
            select(func.min(CompetitionMatch.scheduled_at)).where(
                CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                CompetitionMatch.scheduled_at <= eval_time,
            )
        )

        in_progress_count = (
            self.session.scalar(
                select(func.count(CompetitionMatch.id)).where(
                    CompetitionMatch.status == MatchStatus.IN_PROGRESS.value,
                )
            )
            or 0
        )

        scheduled_metadata = list(
            self.session.scalars(
                select(CompetitionMatch.metadata_json).where(
                    CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                )
            ).all()
        )
        retry_pending_count = 0
        for metadata in scheduled_metadata:
            if not isinstance(metadata, dict):
                continue
            try:
                retry_pending_count += int(metadata.get("execution_attempts") or 0) > 0
            except (TypeError, ValueError):
                # Malformed retry metadata is not evidence of a valid retry count.
                continue

        from app.models.competition_match_execution import CompetitionMatchExecution

        halted_executions = (
            self.session.scalar(
                select(func.count(CompetitionMatchExecution.id)).where(
                    CompetitionMatchExecution.execution_status == "halted"
                )
            )
            or 0
        )
        paused_executions = (
            self.session.scalar(
                select(func.count(CompetitionMatchExecution.id)).where(
                    CompetitionMatchExecution.execution_status == "paused"
                )
            )
            or 0
        )
        stalled_leases = (
            self.session.scalar(
                select(func.count(CompetitionMatchExecution.id)).where(
                    CompetitionMatchExecution.execution_status.in_(["in_progress", "paused"]),
                    CompetitionMatchExecution.lease_expires_at.is_not(None),
                    CompetitionMatchExecution.lease_expires_at <= datetime.now(timezone.utc),
                )
            )
            or 0
        )

        return {
            "clock": {
                "id": clock_state.id,
                "epoch_real_utc": clock_state.epoch_real_utc.isoformat() if clock_state.epoch_real_utc else None,
                "virtual_start_time": (
                    clock_state.virtual_start_time.isoformat() if clock_state.virtual_start_time else None
                ),
                "progression_rate": clock_state.progression_rate,
                "is_paused": clock_state.is_paused,
                "current_virtual_time": eval_time.isoformat(),
            },
            "fixtures": {
                "overdue_count": overdue_count,
                "oldest_overdue_kickoff": oldest_overdue.isoformat() if oldest_overdue else None,
                "in_progress_count": in_progress_count,
                "retry_pending_count": retry_pending_count,
                "worker_mode": worker_mode,
            },
            "executions": {
                "paused_count": paused_executions,
                "halted_count": halted_executions,
                "stalled_lease_count": stalled_leases,
            },
        }


__all__ = ["AutonomousMatchExecutionService"]
