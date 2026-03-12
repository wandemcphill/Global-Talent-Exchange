from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from backend.app.common.enums.qualification_status import QualificationStatus


class ChampionsLeagueValidationError(ValueError):
    """Raised when a Champions League request violates tournament rules."""


class AdvancementStatus(StrEnum):
    ROUND_OF_16 = "round_of_16"
    KNOCKOUT_PLAYOFF = "knockout_playoff"
    ELIMINATED = "eliminated"


class MatchStage(StrEnum):
    QUALIFICATION_PLAYOFF = "qualification_playoff"
    KNOCKOUT_PLAYOFF = "knockout_playoff"
    ROUND_OF_16 = "round_of_16"
    QUARTERFINAL = "quarterfinal"
    SEMIFINAL = "semifinal"
    FINAL = "final"


@dataclass(slots=True, frozen=True)
class ClubCandidate:
    club_id: str
    club_name: str
    region: str
    tier: str
    ranking_points: int
    domestic_rank: int


@dataclass(slots=True, frozen=True)
class ClubSeed:
    club_id: str
    club_name: str
    seed: int
    region: str | None = None
    tier: str | None = None


@dataclass(slots=True, frozen=True)
class QualifiedClub(ClubSeed):
    status: QualificationStatus = QualificationStatus.ELIMINATED
    display_color: str = "slate"


@dataclass(slots=True, frozen=True)
class TierAllocation:
    stage: str
    tier: str
    slot_count: int


@dataclass(slots=True, frozen=True)
class QualificationRegionSummary:
    region: str
    direct_count: int
    playoff_count: int
    eliminated_count: int


@dataclass(slots=True, frozen=True)
class QualificationMap:
    entries: list[QualifiedClub]
    direct_qualifiers: list[QualifiedClub]
    playoff_qualifiers: list[QualifiedClub]
    tier_allocations: list[TierAllocation]
    region_summaries: list[QualificationRegionSummary]


@dataclass(slots=True, frozen=True)
class KnockoutTie:
    tie_id: str
    stage: MatchStage
    home_club: ClubSeed
    away_club: ClubSeed
    winner: ClubSeed
    penalties_if_tied: bool
    extra_time_allowed: bool
    presentation_max_minutes: int


@dataclass(slots=True, frozen=True)
class PlayoffBracket:
    qualification: QualificationMap
    ties: list[KnockoutTie]
    advancing_clubs: list[ClubSeed]


@dataclass(slots=True, frozen=True)
class LeagueMatchResult:
    match_id: str
    home_club_id: str
    away_club_id: str
    home_goals: int
    away_goals: int


@dataclass(slots=True)
class LeagueStandingRow:
    club_id: str
    club_name: str
    seed: int
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    points: int = 0
    rank: int = 0
    advancement_status: AdvancementStatus = AdvancementStatus.ELIMINATED


@dataclass(slots=True, frozen=True)
class LeaguePhaseTable:
    rows: list[LeagueStandingRow]
    is_complete: bool


@dataclass(slots=True, frozen=True)
class KnockoutBracket:
    knockout_playoff: list[KnockoutTie]
    round_of_16: list[KnockoutTie]
    quarterfinals: list[KnockoutTie]
    semifinals: list[KnockoutTie]
    final: KnockoutTie
    champion: ClubSeed


@dataclass(slots=True, frozen=True)
class SettlementEventPlan:
    event_key: str
    event_type: str
    aggregate_id: str
    amount: Decimal
    currency: str
    payload: dict[str, str]


@dataclass(slots=True, frozen=True)
class PrizeSettlementPreview:
    season_id: str
    champion_club_id: str | None
    champion_club_name: str | None
    league_leftover_allocation: Decimal
    funded_pool: Decimal
    champion_share: Decimal
    platform_share: Decimal
    currency: str
    events: list[SettlementEventPlan] = field(default_factory=list)
