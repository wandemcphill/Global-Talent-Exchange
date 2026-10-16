from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.schemas.competition import (
    CompetitionPauseEntry,
    CompetitionSchedulePlan,
    CompetitionScheduleRequest,
    CompetitionWindowAssignment,
    ExclusiveWindowReservation,
)
from .calendar_service import CalendarConflictError, CalendarService


@dataclass(slots=True)
class CompetitionScheduler:
    calendar_service: CalendarService = field(default_factory=CalendarService)

    def build_schedule(
        self,
        requests: tuple[CompetitionScheduleRequest, ...],
    ) -> CompetitionSchedulePlan:
        assignments: list[CompetitionWindowAssignment] = []
        reservations: list[ExclusiveWindowReservation] = []
        paused_competitions: list[CompetitionPauseEntry] = []

        world_super_cup_requests = tuple(
            request
            for request in requests
            if request.competition_type is CompetitionType.WORLD_SUPER_CUP
        )
        world_super_cup_dates = {
            scheduled_date
            for request in world_super_cup_requests
            for scheduled_date in request.requested_dates
        }

        for request in sorted(world_super_cup_requests, key=self._priority_key):
            for scheduled_date in request.requested_dates:
                windows = request.competition_type.default_fixture_windows
                reservation = ExclusiveWindowReservation(
                    reservation_code=f"{request.competition_id}:{scheduled_date.isoformat()}:exclusive",
                    competition_id=request.competition_id,
                    competition_type=request.competition_type,
                    match_date=scheduled_date,
                    windows=windows,
                    reason="World Super Cup exclusivity",
                )
                self.calendar_service.reserve_exclusive_windows(reservation)
                reservations.append(reservation)

                assignment = CompetitionWindowAssignment(
                    competition_id=request.competition_id,
                    competition_type=request.competition_type,
                    match_date=scheduled_date,
                    windows=windows,
                    exclusive=True,
                    label="world_super_cup",
                )
                self.calendar_service.reserve_competition_windows(assignment)
                assignments.append(assignment)

        remaining_requests = tuple(
            request
            for request in sorted(requests, key=self._priority_key)
            if request.competition_type is not CompetitionType.WORLD_SUPER_CUP
        )

        for request in remaining_requests:
            overlapping_world_super_cup_dates = tuple(
                scheduled_date
                for scheduled_date in request.requested_dates
                if scheduled_date in world_super_cup_dates
            )
            if overlapping_world_super_cup_dates and request.competition_type in {
                CompetitionType.LEAGUE,
                CompetitionType.CHAMPIONS_LEAGUE,
            }:
                paused_competitions.append(
                    CompetitionPauseEntry(
                        competition_id=request.competition_id,
                        competition_type=request.competition_type,
                        paused_dates=overlapping_world_super_cup_dates,
                        reason="Paused during World Super Cup exclusive senior windows.",
                    )
                )

            active_dates = tuple(
                scheduled_date
                for scheduled_date in request.requested_dates
                if not (
                    scheduled_date in world_super_cup_dates
                    and request.competition_type in {
                        CompetitionType.LEAGUE,
                        CompetitionType.CHAMPIONS_LEAGUE,
                    }
                )
            )

            if not active_dates:
                continue

            candidate_windows = self._candidate_windows(request)
            for scheduled_date in active_dates:
                assignment = self._build_assignment(
                    request=request,
                    scheduled_date=scheduled_date,
                    candidate_windows=candidate_windows,
                )
                self.calendar_service.reserve_competition_windows(assignment)
                assignments.append(assignment)

        return CompetitionSchedulePlan(
            assignments=tuple(assignments),
            reservations=tuple(reservations),
            paused_competitions=tuple(paused_competitions),
        )

    def _build_assignment(
        self,
        *,
        request: CompetitionScheduleRequest,
        scheduled_date: date,
        candidate_windows: tuple[FixtureWindow, ...],
    ) -> CompetitionWindowAssignment:
        if (
            len(candidate_windows) == 1
            and request.required_windows > 1
            and candidate_windows[0].supports_slot_sequence
        ):
            return CompetitionWindowAssignment(
                competition_id=request.competition_id,
                competition_type=request.competition_type,
                match_date=scheduled_date,
                windows=(candidate_windows[0],),
                slot_sequences=tuple(range(1, request.required_windows + 1)),
                exclusive=request.requires_exclusive_windows,
            )

        selected_windows = self._select_windows(
            request=request,
            scheduled_date=scheduled_date,
            candidate_windows=candidate_windows,
        )
        return CompetitionWindowAssignment(
            competition_id=request.competition_id,
            competition_type=request.competition_type,
            match_date=scheduled_date,
            windows=selected_windows,
            exclusive=request.requires_exclusive_windows,
        )

    def _select_windows(
        self,
        *,
        request: CompetitionScheduleRequest,
        scheduled_date: date,
        candidate_windows: tuple[FixtureWindow, ...],
    ) -> tuple[FixtureWindow, ...]:
        selected: list[FixtureWindow] = []
        for window in candidate_windows:
            tentative_assignment = CompetitionWindowAssignment(
                competition_id=request.competition_id,
                competition_type=request.competition_type,
                match_date=scheduled_date,
                windows=(window,),
                exclusive=request.requires_exclusive_windows,
            )
            try:
                self.calendar_service.reserve_competition_windows(tentative_assignment)
            except CalendarConflictError:
                continue
            self.calendar_service.release_competition_window(scheduled_date, window)
            selected.append(window)
            if len(selected) == request.required_windows:
                break
        if len(selected) != request.required_windows:
            raise CalendarConflictError(
                f"Unable to allocate {request.required_windows} non-conflicting window(s) "
                f"for competition {request.competition_id} on {scheduled_date.isoformat()}."
            )
        return tuple(selected)

    def _candidate_windows(
        self,
        request: CompetitionScheduleRequest,
    ) -> tuple[FixtureWindow, ...]:
        defaults = request.competition_type.default_fixture_windows

        if not request.preferred_windows:
            return defaults

        preferred = tuple(window for window in request.preferred_windows if window in defaults)
        return preferred or defaults

    @staticmethod
    def _priority_key(request: CompetitionScheduleRequest) -> tuple[int, int, str]:
        type_rank = {
            CompetitionType.WORLD_SUPER_CUP: 0,
            CompetitionType.CHAMPIONS_LEAGUE: 1,
            CompetitionType.LEAGUE: 2,
            CompetitionType.ACADEMY: 3,
            CompetitionType.FAST_CUP: 4,
        }[request.competition_type]
        return (type_rank, request.priority, request.competition_id)


@dataclass(slots=True, frozen=True)
class CompetitionWindowResolver:
    assignments_by_date: dict[date, CompetitionWindowAssignment]

    @classmethod
    def from_plan(
        cls,
        plan: CompetitionSchedulePlan,
        *,
        competition_id: str,
    ) -> "CompetitionWindowResolver":
        assignments: dict[date, CompetitionWindowAssignment] = {
            assignment.match_date: assignment
            for assignment in plan.assignments
            if assignment.competition_id == competition_id
        }
        return cls(assignments_by_date=assignments)

    def windows_for_date(self, match_date: date) -> tuple[FixtureWindow, ...]:
        assignment = self.assignments_by_date.get(match_date)
        if assignment is None:
            return ()
        return assignment.windows

    def slot_sequences_for_date(self, match_date: date) -> tuple[int, ...]:
        assignment = self.assignments_by_date.get(match_date)
        if assignment is None:
            return ()
        if assignment.slot_sequences:
            return assignment.slot_sequences
        return (1,)

    def slot_for(self, match_date: date, sequence_index: int) -> tuple[FixtureWindow, int]:
        assignment = self.assignments_by_date.get(match_date)
        if assignment is None:
            raise CalendarConflictError(
                f"No scheduled window assignment exists for {match_date.isoformat()}."
            )
        if sequence_index < 0:
            raise ValueError("Window sequence index must be non-negative.")

        if assignment.slot_sequences:
            return (
                assignment.windows[0],
                assignment.slot_sequences[sequence_index % len(assignment.slot_sequences)],
            )

        return (
            assignment.windows[sequence_index % len(assignment.windows)],
            (sequence_index // len(assignment.windows)) + 1,
        )

    def window_at(self, match_date: date, sequence_index: int) -> FixtureWindow:
        window, _slot_sequence = self.slot_for(match_date, sequence_index)
        return window
