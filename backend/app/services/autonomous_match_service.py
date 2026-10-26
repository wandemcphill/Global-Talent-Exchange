from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

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

        # 1. Discover due matches
        stmt = (
            select(CompetitionMatch)
            .where(
                CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                or_(
                    CompetitionMatch.scheduled_at.is_(None),
                    CompetitionMatch.scheduled_at <= eval_time,
                ),
            )
            .order_by(
                CompetitionMatch.scheduled_at.asc().nullsfirst(),
                CompetitionMatch.created_at.asc(),
            )
            .limit(max(1, limit))
        )

        if _supports_row_locks(self.session):
            stmt = stmt.with_for_update(skip_locked=True)

        due_matches = list(self.session.scalars(stmt).all())

        executed = 0
        failed = 0
        errors: list[str] = []
        settled_competitions: list[str] = []
        advanced_competitions: list[str] = []

        # Track competitions affected so we can finalize/advance them once their round completes
        competitions_to_check: dict[str, Competition] = {}

        for match in due_matches:
            comp = self.session.get(Competition, match.competition_id)
            if comp is None:
                continue

            competitions_to_check[comp.id] = comp

            # If competition is not yet active (e.g. SEEDED), launch it
            comp_status = CompetitionStatus(comp.status)
            if comp_status is CompetitionStatus.SEEDED or self.auto_runner._should_launch(comp):
                try:
                    self.auto_runner.lifecycle_service.launch_competition(comp)
                except Exception as exc:
                    logger.warning("Failed to auto-launch competition %s: %s", comp.id, exc)

            try:
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
                # Rollback match status to scheduled so it can be retried later
                match.status = MatchStatus.SCHEDULED.value
                self.session.flush()

        # 2. Check and advance / finalize competitions where all matches in round are complete
        for comp_id, comp in competitions_to_check.items():
            try:
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
            if self.auto_runner._should_launch(comp):
                try:
                    self.auto_runner.lifecycle_service.launch_competition(comp)
                    launched_competitions.append(comp.id)
                    self.session.flush()
                except Exception as exc:
                    logger.warning("Failed to auto-launch pending competition %s: %s", comp.id, exc)

        return {
            "status": "success",
            "eval_time": eval_time.isoformat(),
            "discovered_due": len(due_matches),
            "executed": executed,
            "failed": failed,
            "settled_competitions": settled_competitions,
            "advanced_competitions": advanced_competitions,
            "launched_competitions": launched_competitions,
            "errors": errors,
        }

    def get_health_telemetry(self) -> dict[str, Any]:
        """Return operational telemetry on clock, overdue fixtures, and worker state."""
        eval_time = self.world_clock.now_virtual()
        clock_state = self.world_clock.get_or_create_state()

        overdue_count = self.session.scalar(
            select(func.count(CompetitionMatch.id)).where(
                CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                or_(
                    CompetitionMatch.scheduled_at.is_(None),
                    CompetitionMatch.scheduled_at <= eval_time,
                ),
            )
        ) or 0

        oldest_overdue = self.session.scalar(
            select(func.min(CompetitionMatch.scheduled_at)).where(
                CompetitionMatch.status == MatchStatus.SCHEDULED.value,
                CompetitionMatch.scheduled_at <= eval_time,
            )
        )

        in_progress_count = self.session.scalar(
            select(func.count(CompetitionMatch.id)).where(
                CompetitionMatch.status == MatchStatus.IN_PROGRESS.value,
            )
        ) or 0

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
            },
        }


__all__ = ["AutonomousMatchExecutionService"]
