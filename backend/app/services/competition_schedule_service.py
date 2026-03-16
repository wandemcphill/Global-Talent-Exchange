from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.schemas.competition import CompetitionSchedulePlan, CompetitionScheduleRequest
from backend.app.competition_engine.scheduler import CompetitionScheduler
from backend.app.config.competition_constants import LEAGUE_MATCH_WINDOWS_PER_DAY
from backend.app.models.calendar_engine import CalendarEvent
from backend.app.models.competition import Competition
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.competition_schedule_job import CompetitionScheduleJob


@dataclass(slots=True)
class SchedulePreview:
    requested_dates: tuple[date, ...]
    assigned_dates: tuple[date, ...]
    plan: CompetitionSchedulePlan
    warnings: tuple[str, ...]
    alignment_week: int | None
    alignment_year: int | None


@dataclass(slots=True)
class CompetitionScheduleService:
    session: Session
    scheduler: CompetitionScheduler = field(default_factory=CompetitionScheduler)

    def preview(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participant_count: int,
        start_date: date,
        requested_dates: tuple[date, ...] | None,
        priority: int = 100,
        requires_exclusive_windows: bool = False,
        alignment_group: str | None = None,
    ) -> SchedulePreview:
        warnings: list[str] = []
        alignment_week = None
        alignment_year = None
        start_date = self._align_start_date(start_date, alignment_group, warnings)
        if alignment_group:
            alignment_week = start_date.isocalendar().week
            alignment_year = start_date.isocalendar().year

        total_rounds = self._round_count(competition, rule_set, participant_count)
        requested = requested_dates or self._build_dates(competition, rule_set, total_rounds, start_date)
        requested, warnings = self._apply_calendar_blackouts(competition, requested, warnings)

        plan = self._build_plan(
            competition=competition,
            total_rounds=total_rounds,
            requested_dates=requested,
            priority=priority,
            requires_exclusive_windows=requires_exclusive_windows,
        )
        assigned_dates = tuple(sorted({assignment.match_date for assignment in plan.assignments}))
        return SchedulePreview(
            requested_dates=requested,
            assigned_dates=assigned_dates,
            plan=plan,
            warnings=tuple(warnings),
            alignment_week=alignment_week,
            alignment_year=alignment_year,
        )

    def create_job(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participant_count: int,
        start_date: date,
        requested_dates: tuple[date, ...] | None,
        priority: int = 100,
        requires_exclusive_windows: bool = False,
        alignment_group: str | None = None,
        preview_only: bool = False,
        created_by_user_id: str | None = None,
    ) -> CompetitionScheduleJob:
        preview = self.preview(
            competition=competition,
            rule_set=rule_set,
            participant_count=participant_count,
            start_date=start_date,
            requested_dates=requested_dates,
            priority=priority,
            requires_exclusive_windows=requires_exclusive_windows,
            alignment_group=alignment_group,
        )
        job = CompetitionScheduleJob(
            competition_id=competition.id,
            status="previewed" if preview_only else "scheduled",
            requested_start_on=start_date,
            requested_dates_json=[item.isoformat() for item in preview.requested_dates],
            assigned_dates_json=[item.isoformat() for item in preview.assigned_dates],
            schedule_plan_json=preview.plan.model_dump(),
            preview_only=preview_only,
            alignment_group=alignment_group,
            alignment_week=preview.alignment_week,
            alignment_year=preview.alignment_year,
            requires_exclusive_windows=requires_exclusive_windows,
            priority=priority,
            created_by_user_id=created_by_user_id,
            metadata_json={"warnings": list(preview.warnings)},
        )
        self.session.add(job)
        self.session.flush()
        return job

    def _competition_type_for_schedule(self, competition: Competition) -> CompetitionType:
        competition_type = (competition.competition_type or competition.format or "league").lower()
        if competition_type in {"world_super_cup", "world_championship", "flagship"}:
            return CompetitionType.WORLD_SUPER_CUP
        if competition_type in {"champions_league"}:
            return CompetitionType.CHAMPIONS_LEAGUE
        if competition_type in {"academy"}:
            return CompetitionType.ACADEMY
        if competition.format == CompetitionFormat.LEAGUE.value:
            return CompetitionType.LEAGUE
        return CompetitionType.FAST_CUP

    def _round_count(
        self,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participant_count: int,
    ) -> int:
        if participant_count <= 1:
            return 0
        if rule_set.group_stage_enabled:
            group_size = rule_set.group_size or max(2, min(4, participant_count))
            group_rounds = max(1, group_size - 1)
            if rule_set.league_home_away:
                group_rounds *= 2
            advance_count = rule_set.group_advance_count or 2
            group_count = rule_set.group_count or int(math.ceil(participant_count / group_size))
            knockout_size = rule_set.knockout_bracket_size or self._next_power_of_two(group_count * advance_count)
            knockout_rounds = int(math.log2(knockout_size))
            return group_rounds + knockout_rounds

        if competition.format == CompetitionFormat.LEAGUE.value:
            rounds = participant_count - 1
            if rule_set.league_home_away:
                rounds *= 2
            return max(1, rounds)

        bracket_size = self._next_power_of_two(participant_count)
        return max(1, int(math.log2(bracket_size)))

    def _build_dates(
        self,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        total_rounds: int,
        start_date: date,
    ) -> tuple[date, ...]:
        if total_rounds <= 0:
            return ()
        spacing_days = 7 if competition.format == CompetitionFormat.LEAGUE.value else 2
        if rule_set.group_stage_enabled:
            spacing_days = 7
        return tuple(start_date + timedelta(days=spacing_days * index) for index in range(total_rounds))

    def _build_plan(
        self,
        *,
        competition: Competition,
        total_rounds: int,
        requested_dates: tuple[date, ...],
        priority: int,
        requires_exclusive_windows: bool,
    ) -> CompetitionSchedulePlan:
        if not requested_dates:
            return CompetitionSchedulePlan()
        competition_type = self._competition_type_for_schedule(competition)
        remaining_rounds = total_rounds
        requests: list[CompetitionScheduleRequest] = []
        for match_date in requested_dates:
            if remaining_rounds <= 0:
                break
            required_windows = 1
            if competition.format == CompetitionFormat.LEAGUE.value:
                required_windows = min(LEAGUE_MATCH_WINDOWS_PER_DAY, remaining_rounds)
            requests.append(
                CompetitionScheduleRequest(
                    competition_id=competition.id,
                    competition_type=competition_type,
                    requested_dates=(match_date,),
                    required_windows=required_windows,
                    priority=priority,
                    requires_exclusive_windows=requires_exclusive_windows,
                )
            )
            remaining_rounds -= required_windows
        return self.scheduler.build_schedule(tuple(requests))

    def _align_start_date(self, start_date: date, alignment_group: str | None, warnings: list[str]) -> date:
        if not alignment_group:
            return start_date
        existing = self.session.scalar(
            select(CompetitionScheduleJob)
            .where(CompetitionScheduleJob.alignment_group == alignment_group)
            .order_by(CompetitionScheduleJob.created_at.desc())
        )
        if existing is None or existing.alignment_week is None or existing.alignment_year is None:
            return start_date
        try:
            aligned = date.fromisocalendar(existing.alignment_year, existing.alignment_week, 1)
            if aligned != start_date:
                warnings.append(f"Aligned schedule to ISO week {existing.alignment_week} for {alignment_group}.")
            return aligned
        except ValueError:
            return start_date

    def _apply_calendar_blackouts(
        self,
        competition: Competition,
        requested_dates: tuple[date, ...],
        warnings: list[str],
    ) -> tuple[tuple[date, ...], list[str]]:
        if not requested_dates:
            return requested_dates, warnings
        schedule_type = self._competition_type_for_schedule(competition)
        if schedule_type is CompetitionType.WORLD_SUPER_CUP:
            return requested_dates, warnings

        start = min(requested_dates)
        end = max(requested_dates)
        events = self.session.scalars(
            select(CalendarEvent).where(
                CalendarEvent.starts_on <= end,
                CalendarEvent.ends_on >= start,
                CalendarEvent.status.in_(("scheduled", "live")),
            )
        ).all()
        blocked: set[date] = set()
        for event in events:
            if not (event.exclusive_windows or event.pause_other_gtx_competitions):
                continue
            current = event.starts_on
            while current <= event.ends_on:
                blocked.add(current)
                current += timedelta(days=1)
        if not blocked:
            return requested_dates, warnings

        filtered = [day for day in requested_dates if day not in blocked]
        if len(filtered) == len(requested_dates):
            return requested_dates, warnings

        warnings.append("Schedule avoided calendar blackout windows.")
        spacing_days = 7 if competition.format == CompetitionFormat.LEAGUE.value else 2
        cursor = max(filtered) if filtered else max(requested_dates)
        while len(filtered) < len(requested_dates):
            cursor = cursor + timedelta(days=spacing_days)
            if cursor in blocked:
                continue
            filtered.append(cursor)
        return tuple(filtered), warnings

    @staticmethod
    def _next_power_of_two(value: int) -> int:
        bracket = 1
        while bracket < value:
            bracket *= 2
        return bracket


__all__ = ["CompetitionScheduleService", "SchedulePreview"]
