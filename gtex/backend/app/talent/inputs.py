"""Immutable inputs to the talent ranking and signal pipelines.

These types are deliberately free of SQLAlchemy and FastAPI so the two
pipelines are pure functions of their inputs: same input, same output, no
clock, no database, no ambient state. `app.talent.service` is responsible for
loading rows and projecting them into these structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping

from app.talent.constants import (
    ALL_ATTRIBUTE_KEYS,
    COMPETITION_LEVEL_SCORE,
    CompetitionLevel,
    DECISIVE_MATCH_STAGES,
    VerificationTier,
)


def normalise_attributes(raw: Mapping[str, object] | None) -> dict[str, float]:
    """Keep only known attribute keys with usable 0-100 values.

    Unknown keys are dropped rather than scored: an attribute vocabulary that
    silently accepts anything cannot be reasoned about, and a caller-supplied
    key would otherwise be able to move a ranking.
    """

    if not raw:
        return {}
    cleaned: dict[str, float] = {}
    for key, value in raw.items():
        normalised_key = str(key).strip().lower()
        if normalised_key not in ALL_ATTRIBUTE_KEYS:
            continue
        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if numeric != numeric:  # NaN
            continue
        cleaned[normalised_key] = max(0.0, min(100.0, numeric))
    return dict(sorted(cleaned.items()))


def normalise_competition_level(value: str | None) -> str:
    candidate = (value or "").strip().lower()
    if candidate in COMPETITION_LEVEL_SCORE:
        return candidate
    return CompetitionLevel.UNKNOWN.value


@dataclass(frozen=True, slots=True)
class TalentMatchRecord:
    """One appearance in a competition, normalised for scoring.

    `match_key` is the deduplication and tie-break key: two records with the
    same key are the same appearance and only the first (after canonical
    sorting) survives, so a double-ingested fixture cannot inflate a ranking.
    """

    match_key: str
    played_on: date
    competition_key: str
    competition_level: str = CompetitionLevel.UNKNOWN.value
    stage: str | None = None
    minutes: int = 0
    rating: float | None = None
    goals: int = 0
    assists: int = 0
    clean_sheet: bool = False
    saves: int = 0
    started: bool = False
    yellow_cards: int = 0
    red_cards: int = 0

    @property
    def is_decisive(self) -> bool:
        stage = (self.stage or "").strip().lower().replace(" ", "_")
        return stage in DECISIVE_MATCH_STAGES

    @property
    def clamped_rating(self) -> float | None:
        if self.rating is None:
            return None
        return max(0.0, min(10.0, float(self.rating)))

    @property
    def clamped_minutes(self) -> int:
        return max(0, min(120, int(self.minutes)))

    def canonical(self) -> "TalentMatchRecord":
        return TalentMatchRecord(
            match_key=str(self.match_key),
            played_on=self.played_on,
            competition_key=str(self.competition_key),
            competition_level=normalise_competition_level(self.competition_level),
            stage=(self.stage or None),
            minutes=self.clamped_minutes,
            rating=self.clamped_rating,
            goals=max(0, int(self.goals)),
            assists=max(0, int(self.assists)),
            clean_sheet=bool(self.clean_sheet),
            saves=max(0, int(self.saves)),
            started=bool(self.started),
            yellow_cards=max(0, int(self.yellow_cards)),
            red_cards=max(0, int(self.red_cards)),
        )

    def as_digest_payload(self) -> dict[str, object]:
        return {
            "match_key": self.match_key,
            "played_on": self.played_on.isoformat(),
            "competition_key": self.competition_key,
            "competition_level": self.competition_level,
            "stage": self.stage,
            "minutes": self.minutes,
            "rating": self.rating,
            "goals": self.goals,
            "assists": self.assists,
            "clean_sheet": self.clean_sheet,
            "saves": self.saves,
            "started": self.started,
            "yellow_cards": self.yellow_cards,
            "red_cards": self.red_cards,
        }


@dataclass(frozen=True, slots=True)
class AvailabilityWindow:
    """How much of the recent period the talent was actually selectable."""

    eligible_matches: int = 0
    available_matches: int = 0
    days_unavailable: int = 0
    window_days: int = 365

    @property
    def availability_ratio(self) -> float | None:
        if self.eligible_matches <= 0:
            return None
        ratio = float(self.available_matches) / float(self.eligible_matches)
        return max(0.0, min(1.0, ratio))

    def as_digest_payload(self) -> dict[str, object]:
        return {
            "eligible_matches": max(0, int(self.eligible_matches)),
            "available_matches": max(0, int(self.available_matches)),
            "days_unavailable": max(0, int(self.days_unavailable)),
            "window_days": max(1, int(self.window_days)),
        }


@dataclass(frozen=True, slots=True)
class TalentRankingInput:
    """Everything the ranking pipeline is allowed to see.

    Note what is absent: no user identity, no KYC state, no wallet, no payment
    data. Ranking cannot depend on information a scout is not permitted to act
    on, which also means a ranking response can never leak it.
    """

    player_id: str
    as_of: date
    position_code: str | None = None
    age_years: int | None = None
    experience_years: float = 0.0
    verification_tier: str = VerificationTier.UNVERIFIED.value
    technical_attributes: Mapping[str, float] = field(default_factory=dict)
    tactical_attributes: Mapping[str, float] = field(default_factory=dict)
    physical_attributes: Mapping[str, float] = field(default_factory=dict)
    match_records: tuple[TalentMatchRecord, ...] = ()
    availability: AvailabilityWindow | None = None

    def canonical(self) -> "TalentRankingInput":
        """Return an order-independent, deduplicated, clamped copy.

        Callers may hand us match records in any order and with duplicates;
        ranking must not care. Sorting on (played_on, match_key) and dropping
        repeat keys is what makes the pipeline reproducible.
        """

        seen: set[str] = set()
        canonical_records: list[TalentMatchRecord] = []
        for record in sorted(
            (item.canonical() for item in self.match_records),
            key=lambda item: (item.played_on, item.match_key),
        ):
            if record.match_key in seen:
                continue
            seen.add(record.match_key)
            canonical_records.append(record)

        tier = str(self.verification_tier or VerificationTier.UNVERIFIED.value).strip().lower()
        if tier not in {member.value for member in VerificationTier}:
            tier = VerificationTier.UNVERIFIED.value

        return TalentRankingInput(
            player_id=str(self.player_id),
            as_of=self.as_of,
            position_code=(self.position_code or "").strip().upper() or None,
            age_years=None if self.age_years is None else max(0, min(70, int(self.age_years))),
            experience_years=max(0.0, min(30.0, float(self.experience_years))),
            verification_tier=tier,
            technical_attributes=normalise_attributes(self.technical_attributes),
            tactical_attributes=normalise_attributes(self.tactical_attributes),
            physical_attributes=normalise_attributes(self.physical_attributes),
            match_records=tuple(canonical_records),
            availability=self.availability,
        )

    def as_digest_payload(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "as_of": self.as_of.isoformat(),
            "position_code": self.position_code,
            "age_years": self.age_years,
            "experience_years": round(float(self.experience_years), 4),
            "verification_tier": self.verification_tier,
            "technical_attributes": dict(sorted(self.technical_attributes.items())),
            "tactical_attributes": dict(sorted(self.tactical_attributes.items())),
            "physical_attributes": dict(sorted(self.physical_attributes.items())),
            "match_records": [record.as_digest_payload() for record in self.match_records],
            "availability": None if self.availability is None else self.availability.as_digest_payload(),
        }


__all__ = [
    "AvailabilityWindow",
    "TalentMatchRecord",
    "TalentRankingInput",
    "normalise_attributes",
    "normalise_competition_level",
]
