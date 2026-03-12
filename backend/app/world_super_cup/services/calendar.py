from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.schemas.competition import CompetitionSchedulePlan, CompetitionScheduleRequest
from backend.app.competition_engine.scheduler import CompetitionScheduler
from backend.app.world_super_cup.models import PausePolicy, TournamentCountdown


@dataclass(slots=True)
class WorldSuperCupCalendarService:
    tournament_name: str = "GTEX World Super Cup"
    competition_id: str = "world_super_cup"

    def pause_policy(self) -> PausePolicy:
        return PausePolicy(
            paused_competitions=("senior_regional_leagues", "senior_continental_cups"),
            active_competitions=("gtex_fast_cup", "academy_competitions"),
            cadence_description="Runs every 2 weeks and every 2 seasons.",
        )

    def build_schedule_plan(
        self,
        reference_at: datetime | None = None,
        *,
        duration_days: int = 3,
    ) -> CompetitionSchedulePlan:
        start_date = self._tournament_start_date(reference_at)
        scheduler = CompetitionScheduler()
        request = CompetitionScheduleRequest(
            competition_id=self.competition_id,
            competition_type=CompetitionType.WORLD_SUPER_CUP,
            requested_dates=tuple(start_date + timedelta(days=offset) for offset in range(duration_days)),
            required_windows=len(CompetitionType.WORLD_SUPER_CUP.default_fixture_windows),
            priority=0,
            requires_exclusive_windows=True,
        )
        return scheduler.build_schedule((request,))

    def tournament_start(self, reference_at: datetime | None = None) -> datetime:
        schedule_plan = self.build_schedule_plan(reference_at)
        opening_assignment = min(schedule_plan.assignments, key=lambda assignment: assignment.match_date)
        opening_window = opening_assignment.windows[0]
        return opening_window.kickoff_at(opening_assignment.match_date, tzinfo=timezone.utc)

    def build_countdown(
        self,
        starts_at: datetime,
        reference_at: datetime | None = None,
    ) -> TournamentCountdown:
        if reference_at is None:
            reference_at = datetime.now(timezone.utc)
        reference_at = reference_at.astimezone(timezone.utc).replace(microsecond=0)
        delta = starts_at - reference_at
        minutes_until_start = max(int(delta.total_seconds() // 60), 0)
        return TournamentCountdown(
            tournament_name=self.tournament_name,
            starts_at=starts_at,
            reference_at=reference_at,
            minutes_until_start=minutes_until_start,
            pause_policy=self.pause_policy(),
        )

    def _tournament_start_date(self, reference_at: datetime | None = None) -> date:
        if reference_at is None:
            reference_at = datetime.now(timezone.utc)
        base_time = reference_at.astimezone(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
        return (base_time + timedelta(days=2)).date()
