from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from backend.app.config.competition_constants import (
    ACADEMY_BUY_IN_MULTIPLIER,
    FAST_CUP_REGISTRATION_INTERVAL_MINUTES,
    FINAL_PRESENTATION_MAX_MINUTES,
    LEAGUE_BUY_IN_TIERS,
    MATCH_PRESENTATION_MAX_MINUTES,
)
from backend.app.fast_cups.models.domain import FastCup, FastCupDivision, FastCupSlot
from backend.app.fast_cups.repositories.base import FastCupRepository

SUPPORTED_FAST_CUP_SIZES = (32, 64, 128, 256)
DEFAULT_HORIZON_INTERVALS = 4


class RecurringFastCupCreationService:
    def __init__(self, repository: FastCupRepository) -> None:
        self.repository = repository

    def ensure_upcoming_cups(
        self,
        *,
        now: datetime,
        horizon_intervals: int = DEFAULT_HORIZON_INTERVALS,
        sizes: tuple[int, ...] = SUPPORTED_FAST_CUP_SIZES,
    ) -> tuple[FastCup, ...]:
        normalized_now = _normalize_timestamp(now)
        created: list[FastCup] = []
        next_boundary = _next_registration_boundary(normalized_now)

        for interval_index in range(horizon_intervals):
            kickoff_at = next_boundary + timedelta(minutes=FAST_CUP_REGISTRATION_INTERVAL_MINUTES * interval_index)
            for division in (FastCupDivision.SENIOR, FastCupDivision.ACADEMY):
                for size in sizes:
                    cup_id = _cup_id(division=division, size=size, kickoff_at=kickoff_at)
                    if self.repository.exists(cup_id):
                        created.append(self.repository.get(cup_id))
                        continue
                    created.append(self.repository.save(self._build_cup(division=division, size=size, kickoff_at=kickoff_at)))
        return tuple(created)

    def _build_cup(self, *, division: FastCupDivision, size: int, kickoff_at: datetime) -> FastCup:
        registration_delta = timedelta(minutes=FAST_CUP_REGISTRATION_INTERVAL_MINUTES)
        expected_duration = _expected_duration_minutes(size)
        slot = FastCupSlot(
            registration_opens_at=kickoff_at - registration_delta,
            registration_closes_at=kickoff_at,
            kickoff_at=kickoff_at,
            expected_completion_at=kickoff_at + timedelta(minutes=expected_duration),
        )
        return FastCup(
            cup_id=_cup_id(division=division, size=size, kickoff_at=kickoff_at),
            title=_cup_title(division=division, size=size),
            division=division,
            size=size,
            buy_in=_buy_in_for(division=division, size=size),
            currency="credit",
            slot=slot,
        )


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _next_registration_boundary(now: datetime) -> datetime:
    clipped = now.replace(second=0, microsecond=0)
    remainder = clipped.minute % FAST_CUP_REGISTRATION_INTERVAL_MINUTES
    if remainder == 0 and now.second == 0 and now.microsecond == 0:
        return clipped + timedelta(minutes=FAST_CUP_REGISTRATION_INTERVAL_MINUTES)
    return clipped + timedelta(minutes=FAST_CUP_REGISTRATION_INTERVAL_MINUTES - remainder)


def _cup_id(*, division: FastCupDivision, size: int, kickoff_at: datetime) -> str:
    return f"fast-cup:{division.value}:{size}:{kickoff_at.strftime('%Y%m%dT%H%MZ')}"


def _cup_title(*, division: FastCupDivision, size: int) -> str:
    if division is FastCupDivision.ACADEMY:
        return f"GTEX Fast Academy Cup {size}"
    return f"GTEX Fast Cup {size}"


def _buy_in_for(*, division: FastCupDivision, size: int) -> Decimal:
    buy_in_slots = tuple(sorted(LEAGUE_BUY_IN_TIERS))[1:5]
    size_to_buy_in = {
        32: Decimal(str(buy_in_slots[0])),
        64: Decimal(str(buy_in_slots[1])),
        128: Decimal(str(buy_in_slots[2])),
        256: Decimal(str(buy_in_slots[3])),
    }
    base_amount = size_to_buy_in[size]
    if division is FastCupDivision.ACADEMY:
        return (base_amount * Decimal(str(ACADEMY_BUY_IN_MULTIPLIER))).quantize(Decimal("0.0001"))
    return base_amount.quantize(Decimal("0.0001"))


def _expected_duration_minutes(size: int) -> int:
    round_count = size.bit_length() - 1
    return ((round_count - 1) * MATCH_PRESENTATION_MAX_MINUTES) + FINAL_PRESENTATION_MAX_MINUTES
