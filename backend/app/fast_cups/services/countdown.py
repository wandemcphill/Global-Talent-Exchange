from __future__ import annotations

from datetime import UTC, datetime

from backend.app.fast_cups.models.domain import FastCup, FastCupStatus, RegistrationCountdown


class RegistrationCountdownService:
    def build(self, *, cup: FastCup, now: datetime) -> RegistrationCountdown:
        resolved_now = _normalize_timestamp(now)
        if cup.result_summary is not None:
            status = FastCupStatus.COMPLETED
        elif resolved_now < cup.slot.kickoff_at:
            status = FastCupStatus.READY if len(cup.entrants) == cup.size else FastCupStatus.REGISTRATION_OPEN
        elif resolved_now < cup.slot.expected_completion_at:
            status = FastCupStatus.IN_PROGRESS
        else:
            status = FastCupStatus.COMPLETED

        return RegistrationCountdown(
            cup_id=cup.cup_id,
            status=status,
            seconds_until_registration_close=_seconds_remaining(cup.slot.registration_closes_at, resolved_now),
            seconds_until_kickoff=_seconds_remaining(cup.slot.kickoff_at, resolved_now),
            seconds_until_completion=_seconds_remaining(cup.slot.expected_completion_at, resolved_now),
            entrants_registered=len(cup.entrants),
            slots_remaining=max(0, cup.size - len(cup.entrants)),
        )


def _seconds_remaining(target: datetime, now: datetime) -> int:
    return max(0, int((target - now).total_seconds()))


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
