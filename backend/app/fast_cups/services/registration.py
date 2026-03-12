from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from backend.app.fast_cups.models.domain import (
    ClubCompetitionWindow,
    FastCup,
    FastCupEntrant,
    FastCupStateError,
    FastCupValidationError,
)


class FastCupRegistrationService:
    def join_cup(
        self,
        *,
        cup: FastCup,
        entrant: FastCupEntrant,
        existing_windows: tuple[ClubCompetitionWindow, ...] = (),
        now: datetime,
    ) -> FastCup:
        resolved_now = _normalize_timestamp(now)
        if resolved_now >= cup.slot.registration_closes_at:
            raise FastCupStateError("Registration has already closed for this fast cup.")
        if entrant.division is not cup.division:
            raise FastCupValidationError("Entrant division does not match the requested fast cup.")

        existing_ids = {registered.club_id for registered in cup.entrants}
        if entrant.club_id in existing_ids:
            return cup
        if len(cup.entrants) >= cup.size:
            raise FastCupStateError("This fast cup is already full.")

        self._ensure_no_conflicts(cup=cup, club_id=entrant.club_id, existing_windows=existing_windows)

        entrants = tuple(sorted((*cup.entrants, entrant), key=_entrant_sort_key))
        return replace(cup, entrants=entrants)

    def _ensure_no_conflicts(
        self,
        *,
        cup: FastCup,
        club_id: str,
        existing_windows: tuple[ClubCompetitionWindow, ...],
    ) -> None:
        for window in existing_windows:
            if window.club_id != club_id:
                continue
            if not window.competition_type.uses_senior_windows:
                continue
            if _windows_overlap(
                left_start=cup.slot.kickoff_at,
                left_end=cup.slot.expected_completion_at,
                right_start=_normalize_timestamp(window.starts_at),
                right_end=_normalize_timestamp(window.ends_at),
            ):
                raise FastCupStateError(
                    "Club is already committed to a league, Champions League, or World Super Cup window."
                )


def _entrant_sort_key(entrant: FastCupEntrant) -> tuple[int, str]:
    return (-entrant.rating, entrant.club_id)


def _windows_overlap(
    *,
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    return left_start < right_end and right_start < left_end


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
