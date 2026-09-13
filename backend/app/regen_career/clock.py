from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class RetirementPressureBand(str, Enum):
    LOW = "low"
    WATCH = "watch"
    HIGH = "high"
    DECISION = "decision"


@dataclass(frozen=True, slots=True)
class RegenRetirementInputs:
    """Inputs for the dynamic regen retirement policy.

    All scalar factors are normalized to 0..1 unless noted. The policy is
    intentionally independent of wall-clock months. GTEX seasons provide the
    career clock, while the season system supplies the approved virtual-age
    mapping.
    """

    virtual_age_months: int | None
    position: str
    injury_burden: float = 0.0
    playing_time: float = 0.5
    performance_trajectory: float = 0.5
    contract_security: float = 0.5
    market_demand: float = 0.5
    salary_burden: float = 0.5
    willingness_to_continue: float = 0.7
    ambition: float = 0.5
    resilience: float = 0.5
    loyalty: float = 0.5
    achievements: float = 0.0
    club_opportunity: float = 0.5
    retirement_threshold: float = 0.85


@dataclass(frozen=True, slots=True)
class RegenCareerAssessment:
    virtual_age_months: int | None
    career_stage: str
    retirement_pressure: float
    pressure_band: RetirementPressureBand
    expected_longevity_months: int | None
    should_enter_retirement_watch: bool
    eligible_for_retirement_decision: bool
    drivers: tuple[str, ...]


class RegenCareerClock:
    """GTEX-season-native career clock and dynamic retirement policy.

    This class deliberately does not choose a global ``N seasons = 1 age year``
    ratio. The active RegenSeason records can publish an explicit
    ``virtual_age_month_index`` in metadata, allowing GTEX to compress or
    stretch virtual age without rewriting player history.
    """

    DEFAULT_POSITION_LONGEVITY: Mapping[str, float] = {
        "goalkeeper": 0.15,
        "defender": 0.10,
        "defensive_midfielder": 0.05,
        "midfielder": 0.00,
        "winger": -0.05,
        "forward": -0.08,
        "striker": -0.10,
        "attacker": -0.10,
    }

    def virtual_age_months_from_seasons(
        self,
        *,
        generation_season_number: int,
        current_season_number: int,
        season_virtual_month_index: Mapping[int, int],
    ) -> int:
        """Return virtual age from the approved GTEX season timeline.

        The timeline itself is authoritative. Missing season mappings are an
        error rather than a guessed wall-clock conversion.
        """
        if generation_season_number < 1 or current_season_number < generation_season_number:
            raise ValueError("Invalid GTEX season range")
        try:
            birth_index = int(season_virtual_month_index[generation_season_number])
            current_index = int(season_virtual_month_index[current_season_number])
        except KeyError as exc:
            raise ValueError("GTEX virtual-age mapping is incomplete for the requested seasons") from exc
        age = current_index - birth_index
        if age < 0:
            raise ValueError("GTEX virtual-age mapping moved backwards")
        return age

    def assess(self, inputs: RegenRetirementInputs) -> RegenCareerAssessment:
        age = inputs.virtual_age_months
        stage = self._stage(age)
        position_key = self._normalize_position(inputs.position)
        longevity = self.DEFAULT_POSITION_LONGEVITY.get(position_key, 0.0)

        age_pressure = self._age_pressure(age)
        injury = self._clamp(inputs.injury_burden)
        low_minutes = 1.0 - self._clamp(inputs.playing_time)
        poor_trajectory = 1.0 - self._clamp(inputs.performance_trajectory)
        contract = 1.0 - self._clamp(inputs.contract_security)
        demand = 1.0 - self._clamp(inputs.market_demand)
        salary = self._clamp(inputs.salary_burden)
        unwilling = 1.0 - self._clamp(inputs.willingness_to_continue)
        low_ambition = 1.0 - self._clamp(inputs.ambition)
        low_resilience = 1.0 - self._clamp(inputs.resilience)
        low_loyalty = 1.0 - self._clamp(inputs.loyalty)
        achievement = self._clamp(inputs.achievements)
        opportunity = self._clamp(inputs.club_opportunity)

        pressure = (
            0.34 * age_pressure
            + 0.15 * injury
            + 0.10 * low_minutes
            + 0.10 * poor_trajectory
            + 0.07 * contract
            + 0.06 * demand
            + 0.05 * salary
            + 0.05 * unwilling
            + 0.03 * low_ambition
            + 0.03 * low_resilience
            + 0.02 * low_loyalty
            - 0.07 * achievement
            - 0.08 * opportunity
            - 0.08 * longevity
        )
        pressure = round(self._clamp(pressure), 4)

        band = self._pressure_band(pressure)
        watch = pressure >= 0.55 or (age is not None and age >= 300)
        decision = pressure >= inputs.retirement_threshold and age is not None

        drivers = self._drivers(
            age=age,
            position_key=position_key,
            age_pressure=age_pressure,
            injury=injury,
            low_minutes=low_minutes,
            poor_trajectory=poor_trajectory,
            contract=contract,
            demand=demand,
            salary=salary,
            unwilling=unwilling,
            achievement=achievement,
            opportunity=opportunity,
        )

        expected = self._expected_longevity(age=age, pressure=pressure, longevity=longevity)
        return RegenCareerAssessment(
            virtual_age_months=age,
            career_stage=stage,
            retirement_pressure=pressure,
            pressure_band=band,
            expected_longevity_months=expected,
            should_enter_retirement_watch=watch,
            eligible_for_retirement_decision=decision,
            drivers=drivers,
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _normalize_position(position: str) -> str:
        raw = " ".join(str(position or "").strip().lower().split())
        if "goal" in raw or "keeper" in raw:
            return "goalkeeper"
        if raw in {"cb", "lb", "rb", "lwb", "rwb"} or "def" in raw:
            return "defender"
        if "defensive mid" in raw or raw == "dm":
            return "defensive_midfielder"
        if "wing" in raw:
            return "winger"
        if "striker" in raw:
            return "striker"
        if "forward" in raw:
            return "forward"
        if "attack" in raw:
            return "attacker"
        return "midfielder"

    @staticmethod
    def _age_pressure(age: int | None) -> float:
        if age is None:
            return 0.0
        if age >= 420:
            return 1.0 + ((age - 420) / 60.0)
        return RegenCareerClock._clamp((age - 300) / 120.0)

    @staticmethod
    def _stage(age: int | None) -> str:
        if age is None:
            return "age_unknown"
        if age < 120:
            return "emerging"
        if age < 240:
            return "development"
        if age < 330:
            return "prime"
        if age < 420:
            return "veteran"
        return "late_career"

    @staticmethod
    def _pressure_band(pressure: float) -> RetirementPressureBand:
        if pressure >= 0.85:
            return RetirementPressureBand.DECISION
        if pressure >= 0.70:
            return RetirementPressureBand.HIGH
        if pressure >= 0.40:
            return RetirementPressureBand.WATCH
        return RetirementPressureBand.LOW

    @staticmethod
    def _expected_longevity(*, age: int | None, pressure: float, longevity: float) -> int | None:
        if age is None:
            return None
        remaining = 72.0 * (1.0 - pressure) + 24.0 * max(0.0, longevity)
        return max(0, int(round(age + remaining)))

    @staticmethod
    def _drivers(
        *,
        age: int | None,
        position_key: str,
        age_pressure: float,
        injury: float,
        low_minutes: float,
        poor_trajectory: float,
        contract: float,
        demand: float,
        salary: float,
        unwilling: float,
        achievement: float,
        opportunity: float,
    ) -> tuple[str, ...]:
        candidates: list[tuple[float, str]] = [
            (age_pressure, "virtual_age"),
            (injury, "injury_burden"),
            (low_minutes, "playing_time"),
            (poor_trajectory, "performance_trajectory"),
            (contract, "contract_security"),
            (demand, "market_demand"),
            (salary, "salary_burden"),
            (unwilling, "willingness_to_continue"),
        ]
        if position_key in {"goalkeeper", "defender"}:
            candidates.append((-0.15, "position_longevity"))
        if achievement >= 0.7:
            candidates.append((-achievement, "career_achievements"))
        if opportunity >= 0.7:
            candidates.append((-opportunity, "club_opportunity"))
        candidates.sort(key=lambda item: abs(item[0]), reverse=True)
        return tuple(name for _, name in candidates[:5])


__all__ = [
    "RegenCareerAssessment",
    "RegenCareerClock",
    "RegenRetirementInputs",
    "RetirementPressureBand",
]
