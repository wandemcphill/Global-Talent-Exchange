from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from threading import RLock

from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.schemas.competition import (
    CalendarConflict,
    CompetitionReference,
    CompetitionWindowAssignment,
    ExclusiveWindowReservation,
    FixtureWindowSlot,
    LeagueFixtureRequest,
    ScheduledFixture,
)

class CalendarConflictError(ValueError):
    pass


@dataclass(slots=True)
class CalendarService:
    _assignments: dict[tuple[date, FixtureWindow], CompetitionWindowAssignment] = field(default_factory=dict)
    _reservations: dict[tuple[date, FixtureWindow], ExclusiveWindowReservation] = field(default_factory=dict)
    _fixtures_by_slot: dict[tuple[date, FixtureWindow, int], list[ScheduledFixture]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _clubs_by_slot: dict[tuple[date, FixtureWindow, int], set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    _lock: RLock = field(default_factory=RLock)

    def reserve_competition_windows(
        self,
        assignment: CompetitionWindowAssignment,
    ) -> CompetitionWindowAssignment:
        with self._lock:
            for window in assignment.windows:
                key = (assignment.match_date, window)
                existing_assignment = self._assignments.get(key)
                if existing_assignment and existing_assignment.competition_id != assignment.competition_id:
                    raise CalendarConflictError(
                        "Competition window already assigned to another competition."
                    )
                existing_reservation = self._reservations.get(key)
                if existing_reservation and existing_reservation.competition_id != assignment.competition_id:
                    raise CalendarConflictError(
                        "Competition window is reserved exclusively by another competition."
                    )
            for window in assignment.windows:
                self._assignments[(assignment.match_date, window)] = assignment
        return assignment

    def release_competition_window(self, match_date: date, window: FixtureWindow) -> None:
        with self._lock:
            self._assignments.pop((match_date, window), None)

    def reserve_exclusive_windows(
        self,
        reservation: ExclusiveWindowReservation,
    ) -> ExclusiveWindowReservation:
        with self._lock:
            for window in reservation.windows:
                key = (reservation.match_date, window)
                existing_reservation = self._reservations.get(key)
                if existing_reservation and existing_reservation.competition_id != reservation.competition_id:
                    raise CalendarConflictError(
                        "Fixture window is already reserved exclusively by another competition."
                    )
                existing_assignment = self._assignments.get(key)
                if existing_assignment and existing_assignment.competition_id != reservation.competition_id:
                    raise CalendarConflictError(
                        "Fixture window is already assigned to another competition."
                    )
            for window in reservation.windows:
                self._reservations[(reservation.match_date, window)] = reservation
        return reservation

    def detect_conflicts(
        self,
        fixture: LeagueFixtureRequest,
        slot: FixtureWindowSlot,
    ) -> tuple[CalendarConflict, ...]:
        conflicts: list[CalendarConflict] = []
        reservation_key = (slot.match_date, slot.window)
        slot_key = (slot.match_date, slot.window, slot.slot_sequence)

        with self._lock:
            reservation = self._reservations.get(reservation_key)
            if reservation and reservation.competition_id != fixture.competition_id:
                conflicts.append(
                    CalendarConflict(
                        conflict_code="exclusive_window_reserved",
                        message="Fixture window is reserved exclusively by another competition.",
                        match_date=slot.match_date,
                        window=slot.window,
                        slot_sequence=slot.slot_sequence,
                        competition_id=fixture.competition_id,
                        conflicting_competition_id=reservation.competition_id,
                        fixture_id=fixture.fixture_id,
                        reservation_code=reservation.reservation_code,
                    )
                )

            assignment = self._assignments.get(reservation_key)
            if assignment and assignment.competition_id != fixture.competition_id:
                conflicts.append(
                    CalendarConflict(
                        conflict_code="competition_window_occupied",
                        message="Another competition already owns this fixture window.",
                        match_date=slot.match_date,
                        window=slot.window,
                        slot_sequence=slot.slot_sequence,
                        competition_id=fixture.competition_id,
                        conflicting_competition_id=assignment.competition_id,
                        fixture_id=fixture.fixture_id,
                    )
                )

            clubs_in_slot = self._clubs_by_slot.get(slot_key, set())
            for club_id in (fixture.home_club_id, fixture.away_club_id):
                if club_id in clubs_in_slot:
                    conflicts.append(
                        CalendarConflict(
                            conflict_code="club_double_booked",
                            message="Club is already scheduled in the same fixture window.",
                            match_date=slot.match_date,
                            window=slot.window,
                            slot_sequence=slot.slot_sequence,
                            competition_id=fixture.competition_id,
                            club_id=club_id,
                            fixture_id=fixture.fixture_id,
                        )
                    )

        return tuple(conflicts)

    def schedule_fixture(
        self,
        fixture: LeagueFixtureRequest,
        slot: FixtureWindowSlot,
        *,
        allow_penalties: bool = False,
    ) -> ScheduledFixture:
        conflicts = self.detect_conflicts(fixture, slot)
        if conflicts:
            raise CalendarConflictError(conflicts[0].message)

        scheduled_fixture = ScheduledFixture(
            fixture_id=fixture.fixture_id,
            competition_id=fixture.competition_id,
            competition_type=fixture.competition_type,
            round_number=fixture.round_number,
            home_club_id=fixture.home_club_id,
            away_club_id=fixture.away_club_id,
            match_date=slot.match_date,
            window=slot.window,
            slot_sequence=slot.slot_sequence,
            stage_name=fixture.stage_name,
            replay_visibility=fixture.replay_visibility,
            is_cup_match=fixture.is_cup_match,
            allow_penalties=allow_penalties,
        )

        key = (slot.match_date, slot.window, slot.slot_sequence)
        with self._lock:
            self._fixtures_by_slot[key].append(scheduled_fixture)
            clubs_in_slot = self._clubs_by_slot[key]
            clubs_in_slot.add(fixture.home_club_id)
            clubs_in_slot.add(fixture.away_club_id)

        return scheduled_fixture

    def schedule_league_fixtures(
        self,
        competition: CompetitionReference,
        *,
        match_date: date,
        fixtures: tuple[LeagueFixtureRequest, ...],
        available_windows: tuple[FixtureWindow, ...] | None = None,
    ) -> tuple[ScheduledFixture, ...]:
        windows = available_windows or competition.competition_type.default_fixture_windows
        scheduled: list[ScheduledFixture] = []
        next_window_index = 0

        for fixture in fixtures:
            selected_window: FixtureWindow | None = None
            for offset in range(len(windows)):
                candidate = windows[(next_window_index + offset) % len(windows)]
                slot = FixtureWindowSlot(match_date=match_date, window=candidate)
                if not self.detect_conflicts(fixture, slot):
                    selected_window = candidate
                    next_window_index = (next_window_index + offset + 1) % len(windows)
                    break
            if selected_window is None:
                raise CalendarConflictError(
                    f"Unable to place fixture {fixture.fixture_id} without a window conflict."
                )
            scheduled.append(
                self.schedule_fixture(
                    fixture,
                    FixtureWindowSlot(match_date=match_date, window=selected_window),
                )
            )

        return tuple(scheduled)

    def list_fixtures(self) -> tuple[ScheduledFixture, ...]:
        with self._lock:
            fixtures: list[ScheduledFixture] = []
            for scheduled in self._fixtures_by_slot.values():
                fixtures.extend(scheduled)
        fixtures.sort(
            key=lambda fixture: (
                fixture.match_date,
                fixture.window.value,
                fixture.slot_sequence,
                fixture.fixture_id,
            )
        )
        return tuple(fixtures)
