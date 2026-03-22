from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.schemas.real_player_ingestion import RealPlayerSeedInput


NORMALIZATION_PROFILE_VERSION = "real_player_v1"

_COMPETITION_STRENGTH_SCORES = {
    "elite": 94.0,
    "major": 92.0,
    "continental": 88.0,
    "top_flight": 82.0,
    "first_division": 78.0,
    "second_tier": 64.0,
    "developmental": 48.0,
    "youth": 38.0,
    "unknown": 55.0,
}


@dataclass(frozen=True, slots=True)
class RealPlayerNormalizedProfile:
    source_name: str
    source_player_key: str
    canonical_name: str
    known_aliases: tuple[str, ...]
    nationality: str | None
    nationality_code: str | None
    date_of_birth: date | None
    birth_year: int | None
    age_years: int | None
    dominant_foot: str | None
    primary_position: str
    secondary_positions: tuple[str, ...]
    normalized_position: str
    current_real_world_club: str | None
    current_real_world_league: str | None
    competition_level: str
    competition_strength_score: float
    competition_strength_multiplier: float
    club_strength_score: float
    real_life_performance_score: float
    age_trajectory_score: float
    market_prestige_signal: float
    popularity_signal: float
    liquidity_seed_signal: float
    form_signal: float
    role_tier_signal: float
    profile_completeness_score: float
    current_market_reference_value: float | None
    market_reference_currency: str | None
    reference_market_value_eur: float | None
    normalization_profile_version: str
    real_player_tier: str
    appearances: int
    minutes_played: int
    goals: int
    assists: int
    clean_sheets: int
    injury_status: str | None

    def normalized_signals(self) -> dict[str, float]:
        return {
            "real_life_performance_score": self.real_life_performance_score,
            "competition_strength_score": self.competition_strength_score,
            "club_strength_score": self.club_strength_score,
            "age_trajectory_score": self.age_trajectory_score,
            "market_prestige_signal": self.market_prestige_signal,
            "popularity_signal": self.popularity_signal,
            "liquidity_seed_signal": self.liquidity_seed_signal,
            "form_signal": self.form_signal,
            "role_tier_signal": self.role_tier_signal,
        }


@dataclass(slots=True)
class RealPlayerNormalizationService:
    normalization_profile_version: str = NORMALIZATION_PROFILE_VERSION

    def normalize(self, payload: RealPlayerSeedInput, *, as_of: datetime) -> RealPlayerNormalizedProfile:
        competition_level = self._competition_level(payload.competition_level)
        primary_position = self._primary_position(payload.primary_position)
        secondary_positions = tuple(self._primary_position(position) for position in payload.secondary_positions)
        normalized_position = self._position_family(primary_position)
        age_years = self._age_years(payload.date_of_birth, payload.birth_year, as_of.date())
        competition_strength_score = _COMPETITION_STRENGTH_SCORES[competition_level]
        market_reference_currency = payload.market_reference_currency
        reference_market_value_eur = (
            round(float(payload.current_market_reference_value), 2)
            if payload.current_market_reference_value is not None and market_reference_currency == "EUR"
            else None
        )
        real_life_performance_score = self._performance_score(
            primary_position=primary_position,
            appearances=int(payload.appearances or 0),
            minutes_played=int(payload.minutes_played or 0),
            goals=int(payload.goals or 0),
            assists=int(payload.assists or 0),
            clean_sheets=int(payload.clean_sheets or 0),
            injury_status=payload.injury_status,
        )
        age_trajectory_score = self._age_trajectory_score(primary_position=primary_position, age_years=age_years)
        market_prestige_signal = self._market_prestige_signal(
            reference_market_value_eur=reference_market_value_eur,
            competition_strength_score=competition_strength_score,
        )
        role_tier_signal = self._role_tier_signal(
            competition_strength_score=competition_strength_score,
            performance_score=real_life_performance_score,
            minutes_played=int(payload.minutes_played or 0),
        )
        club_strength_score = self._club_strength_score(
            competition_strength_score=competition_strength_score,
            market_prestige_signal=market_prestige_signal,
            role_tier_signal=role_tier_signal,
        )
        form_signal = self._form_signal(
            performance_score=real_life_performance_score,
            role_tier_signal=role_tier_signal,
            injury_status=payload.injury_status,
        )
        popularity_signal = self._popularity_signal(
            market_prestige_signal=market_prestige_signal,
            club_strength_score=club_strength_score,
            competition_strength_score=competition_strength_score,
            form_signal=form_signal,
        )
        liquidity_seed_signal = self._liquidity_seed_signal(
            market_prestige_signal=market_prestige_signal,
            popularity_signal=popularity_signal,
            role_tier_signal=role_tier_signal,
            form_signal=form_signal,
        )
        profile_completeness_score = self._profile_completeness_score(payload)
        real_player_tier = self._real_player_tier(
            explicit_tier=payload.real_player_tier,
            market_prestige_signal=market_prestige_signal,
            role_tier_signal=role_tier_signal,
            performance_score=real_life_performance_score,
        )

        return RealPlayerNormalizedProfile(
            source_name=payload.source_name,
            source_player_key=payload.source_player_key,
            canonical_name=payload.canonical_name,
            known_aliases=tuple(payload.known_aliases),
            nationality=payload.nationality,
            nationality_code=payload.nationality_code,
            date_of_birth=payload.date_of_birth,
            birth_year=payload.birth_year,
            age_years=age_years,
            dominant_foot=payload.dominant_foot,
            primary_position=primary_position,
            secondary_positions=secondary_positions,
            normalized_position=normalized_position,
            current_real_world_club=payload.current_real_world_club,
            current_real_world_league=payload.current_real_world_league,
            competition_level=competition_level,
            competition_strength_score=competition_strength_score,
            competition_strength_multiplier=round(0.75 + (competition_strength_score / 200.0), 3),
            club_strength_score=club_strength_score,
            real_life_performance_score=real_life_performance_score,
            age_trajectory_score=age_trajectory_score,
            market_prestige_signal=market_prestige_signal,
            popularity_signal=popularity_signal,
            liquidity_seed_signal=liquidity_seed_signal,
            form_signal=form_signal,
            role_tier_signal=role_tier_signal,
            profile_completeness_score=profile_completeness_score,
            current_market_reference_value=payload.current_market_reference_value,
            market_reference_currency=market_reference_currency,
            reference_market_value_eur=reference_market_value_eur,
            normalization_profile_version=self.normalization_profile_version,
            real_player_tier=real_player_tier,
            appearances=int(payload.appearances or 0),
            minutes_played=int(payload.minutes_played or 0),
            goals=int(payload.goals or 0),
            assists=int(payload.assists or 0),
            clean_sheets=int(payload.clean_sheets or 0),
            injury_status=payload.injury_status,
        )

    def _competition_level(self, value: str | None) -> str:
        normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"elite", "major", "continental", "top_flight", "first_division", "second_tier", "developmental", "youth"}:
            return normalized
        if normalized in {"champions_league", "major_european", "major_league"}:
            return "elite"
        if normalized in {"top", "tier_1", "premier"}:
            return "top_flight"
        if normalized in {"tier_2", "division_2"}:
            return "second_tier"
        if normalized in {"dev", "development"}:
            return "developmental"
        return "unknown"

    def _primary_position(self, value: str | None) -> str:
        normalized = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"gk", "goalkeeper"}:
            return "Goalkeeper"
        if normalized in {"cb", "centre_back", "center_back"}:
            return "Centre-Back"
        if normalized in {"lb", "rb", "full_back", "left_back", "right_back", "wing_back"}:
            return "Full-Back"
        if normalized in {"dm", "cdm", "defensive_midfielder"}:
            return "Defensive Midfielder"
        if normalized in {"am", "cam", "attacking_midfielder"}:
            return "Attacking Midfielder"
        if normalized in {"lw", "rw", "winger", "wide_forward"}:
            return "Winger"
        if normalized in {"st", "cf", "striker", "forward", "centre_forward", "center_forward"}:
            return "Striker"
        return "Central Midfielder"

    def _position_family(self, primary_position: str) -> str:
        if primary_position == "Goalkeeper":
            return "goalkeeper"
        if primary_position in {"Centre-Back", "Full-Back"}:
            return "defender"
        if primary_position in {"Winger", "Striker"}:
            return "forward"
        return "midfielder"

    def _age_years(self, date_of_birth: date | None, birth_year: int | None, reference_date: date) -> int | None:
        if date_of_birth is not None:
            age_years = reference_date.year - date_of_birth.year
            if (reference_date.month, reference_date.day) < (date_of_birth.month, date_of_birth.day):
                age_years -= 1
            return max(age_years, 15)
        if birth_year is not None:
            return max(reference_date.year - birth_year, 15)
        return None

    def _performance_score(
        self,
        *,
        primary_position: str,
        appearances: int,
        minutes_played: int,
        goals: int,
        assists: int,
        clean_sheets: int,
        injury_status: str | None,
    ) -> float:
        minute_score = min((minutes_played / 2700.0) * 45.0, 45.0)
        appearance_score = min((appearances / 38.0) * 25.0, 25.0)
        if primary_position == "Striker":
            contribution_score = min((goals * 2.8) + (assists * 1.4), 30.0)
        elif primary_position == "Winger":
            contribution_score = min((goals * 2.0) + (assists * 1.8), 30.0)
        elif primary_position in {"Attacking Midfielder", "Central Midfielder", "Defensive Midfielder"}:
            contribution_score = min((goals * 1.5) + (assists * 2.0), 26.0)
        elif primary_position in {"Centre-Back", "Full-Back"}:
            contribution_score = min((clean_sheets * 1.5) + (goals * 1.1) + (assists * 1.1), 24.0)
        else:
            contribution_score = min(clean_sheets * 1.8, 22.0)
        injury_penalty = 12.0 if (injury_status or "").strip().lower() not in {"", "fit", "available", "none"} else 0.0
        return round(min(max(minute_score + appearance_score + contribution_score - injury_penalty, 28.0), 96.0), 2)

    def _age_trajectory_score(self, *, primary_position: str, age_years: int | None) -> float:
        if age_years is None:
            return 60.0
        target_age = {
            "Goalkeeper": 29,
            "Centre-Back": 27,
            "Full-Back": 25,
            "Defensive Midfielder": 27,
            "Central Midfielder": 26,
            "Attacking Midfielder": 25,
            "Winger": 24,
            "Striker": 25,
        }[primary_position]
        delta = abs(age_years - target_age)
        return round(min(max(92.0 - (delta * 4.5), 34.0), 92.0), 2)

    def _market_prestige_signal(self, *, reference_market_value_eur: float | None, competition_strength_score: float) -> float:
        if reference_market_value_eur is None:
            return round(min(max((competition_strength_score * 0.72), 36.0), 78.0), 2)
        if reference_market_value_eur >= 80_000_000:
            return 96.0
        if reference_market_value_eur >= 50_000_000:
            return 87.0
        if reference_market_value_eur >= 25_000_000:
            return 74.0
        if reference_market_value_eur >= 10_000_000:
            return 61.0
        if reference_market_value_eur >= 5_000_000:
            return 48.0
        return 38.0

    def _role_tier_signal(self, *, competition_strength_score: float, performance_score: float, minutes_played: int) -> float:
        minutes_factor = min(minutes_played / 3000.0, 1.0) * 100.0
        return round(min(max((competition_strength_score * 0.32) + (performance_score * 0.43) + (minutes_factor * 0.25), 34.0), 95.0), 2)

    def _club_strength_score(
        self,
        *,
        competition_strength_score: float,
        market_prestige_signal: float,
        role_tier_signal: float,
    ) -> float:
        return round(min(max((competition_strength_score * 0.55) + (market_prestige_signal * 0.25) + (role_tier_signal * 0.20), 38.0), 94.0), 2)

    def _form_signal(self, *, performance_score: float, role_tier_signal: float, injury_status: str | None) -> float:
        penalty = 10.0 if (injury_status or "").strip().lower() not in {"", "fit", "available", "none"} else 0.0
        return round(min(max((performance_score * 0.65) + (role_tier_signal * 0.35) - penalty, 24.0), 95.0), 2)

    def _popularity_signal(
        self,
        *,
        market_prestige_signal: float,
        club_strength_score: float,
        competition_strength_score: float,
        form_signal: float,
    ) -> float:
        return round(
            min(
                max(
                    (market_prestige_signal * 0.45)
                    + (club_strength_score * 0.22)
                    + (competition_strength_score * 0.18)
                    + (form_signal * 0.15),
                    30.0,
                ),
                96.0,
            ),
            2,
        )

    def _liquidity_seed_signal(
        self,
        *,
        market_prestige_signal: float,
        popularity_signal: float,
        role_tier_signal: float,
        form_signal: float,
    ) -> float:
        return round(
            min(
                max(
                    (market_prestige_signal * 0.38)
                    + (popularity_signal * 0.27)
                    + (role_tier_signal * 0.20)
                    + (form_signal * 0.15),
                    24.0,
                ),
                95.0,
            ),
            2,
        )

    def _profile_completeness_score(self, payload: RealPlayerSeedInput) -> float:
        checks = (
            bool(payload.nationality or payload.nationality_code),
            bool(payload.date_of_birth or payload.birth_year),
            bool(payload.primary_position),
            bool(payload.current_real_world_club),
            bool(payload.current_real_world_league),
            payload.height_cm is not None,
            payload.weight_kg is not None,
            bool(payload.dominant_foot),
            payload.current_market_reference_value is not None,
            payload.appearances is not None,
            payload.minutes_played is not None,
        )
        filled = sum(1 for item in checks if item)
        return round(min(max(0.55 + ((filled / len(checks)) * 0.35), 0.55), 0.90), 4)

    def _real_player_tier(
        self,
        *,
        explicit_tier: str | None,
        market_prestige_signal: float,
        role_tier_signal: float,
        performance_score: float,
    ) -> str:
        if explicit_tier:
            return explicit_tier
        if market_prestige_signal >= 90.0 or performance_score >= 90.0:
            return "elite"
        if market_prestige_signal >= 74.0 or role_tier_signal >= 74.0:
            return "featured"
        if role_tier_signal >= 58.0:
            return "core"
        return "watchlist"


__all__ = [
    "NORMALIZATION_PROFILE_VERSION",
    "RealPlayerNormalizationService",
    "RealPlayerNormalizedProfile",
]
