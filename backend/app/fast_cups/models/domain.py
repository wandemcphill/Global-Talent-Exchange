from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow


class FastCupValidationError(ValueError):
    """Raised when fast cup input is malformed."""


class FastCupStateError(ValueError):
    """Raised when a fast cup action is not valid in the cup's current state."""


class FastCupNotFoundError(KeyError):
    """Raised when a fast cup cannot be found."""


class FastCupDivision(StrEnum):
    SENIOR = "senior"
    ACADEMY = "academy"


class FastCupStatus(StrEnum):
    REGISTRATION_OPEN = "registration_open"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class FastCupStage(StrEnum):
    ROUND_OF_256 = "round_of_256"
    ROUND_OF_128 = "round_of_128"
    ROUND_OF_64 = "round_of_64"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTERFINAL = "quarterfinal"
    SEMIFINAL = "semifinal"
    FINAL = "final"


@dataclass(slots=True, frozen=True)
class ClubCompetitionWindow:
    club_id: str
    competition_id: str
    competition_type: CompetitionType
    starts_at: datetime
    ends_at: datetime
    window: FixtureWindow | None = None


@dataclass(slots=True, frozen=True)
class FastCupEntrant:
    club_id: str
    club_name: str
    division: FastCupDivision
    rating: int
    registered_at: datetime


@dataclass(slots=True, frozen=True)
class FastCupSlot:
    registration_opens_at: datetime
    registration_closes_at: datetime
    kickoff_at: datetime
    expected_completion_at: datetime
    window: FixtureWindow = FixtureWindow.FAST_CUP_OPEN


@dataclass(slots=True, frozen=True)
class FastCupMatch:
    tie_id: str
    stage: FastCupStage
    round_number: int
    slot_number: int
    scheduled_at: datetime
    presentation_min_minutes: int
    presentation_max_minutes: int
    home: FastCupEntrant | None = None
    away: FastCupEntrant | None = None
    winner: FastCupEntrant | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    home_penalties: int | None = None
    away_penalties: int | None = None
    decided_by_penalties: bool = False
    penalties_if_tied: bool = True
    extra_time_allowed: bool = False
    key_moments: tuple[str, ...] = ()
    home_source_tie_id: str | None = None
    away_source_tie_id: str | None = None


@dataclass(slots=True, frozen=True)
class FastCupRound:
    stage: FastCupStage
    round_number: int
    scheduled_at: datetime
    presentation_max_minutes: int
    matches: tuple[FastCupMatch, ...]


@dataclass(slots=True, frozen=True)
class FastCupBracket:
    rounds: tuple[FastCupRound, ...]
    total_rounds: int
    total_matches: int
    expected_duration_minutes: int
    simulated: bool = False
    champion: FastCupEntrant | None = None
    runner_up: FastCupEntrant | None = None
    semifinalists: tuple[FastCupEntrant, ...] = ()


@dataclass(slots=True, frozen=True)
class CupReward:
    club_id: str
    club_name: str
    finish: str
    amount: Decimal
    currency: str


@dataclass(slots=True, frozen=True)
class PayoutLedgerEvent:
    event_key: str
    event_type: str
    aggregate_id: str
    amount: Decimal
    currency: str
    payload: dict[str, str]


@dataclass(slots=True, frozen=True)
class FastCupResultSummary:
    cup_id: str
    division: FastCupDivision
    size: int
    champion: FastCupEntrant
    runner_up: FastCupEntrant
    semifinalists: tuple[FastCupEntrant, ...]
    total_rounds: int
    total_matches: int
    expected_duration_minutes: int
    concluded_at: datetime
    prize_pool: Decimal
    reward_pool: Decimal
    platform_fee: Decimal
    currency: str
    penalty_shootouts: int
    rewards: tuple[CupReward, ...] = ()
    events: tuple[PayoutLedgerEvent, ...] = ()


@dataclass(slots=True, frozen=True)
class RegistrationCountdown:
    cup_id: str
    status: FastCupStatus
    seconds_until_registration_close: int
    seconds_until_kickoff: int
    seconds_until_completion: int
    entrants_registered: int
    slots_remaining: int


@dataclass(slots=True, frozen=True)
class FastCup:
    cup_id: str
    title: str
    division: FastCupDivision
    size: int
    buy_in: Decimal
    currency: str
    slot: FastCupSlot
    status: FastCupStatus = FastCupStatus.REGISTRATION_OPEN
    entrants: tuple[FastCupEntrant, ...] = field(default_factory=tuple)
    bracket: FastCupBracket | None = None
    result_summary: FastCupResultSummary | None = None
