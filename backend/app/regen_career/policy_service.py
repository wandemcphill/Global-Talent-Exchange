from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.player_contract import PlayerContract
from app.models.player_injury_case import PlayerInjuryCase
from app.models.regen import (
    RegenGenerationEvent,
    RegenPersonalityProfile,
    RegenProfile,
)
from app.regen_career.clock import (
    RegenCareerAssessment,
    RegenCareerClock,
    RegenRetirementInputs,
)
from app.regen_universe.models import RegenSeason

_SEASON_NUMBER_RE = re.compile(r"(?:season|s)[ _-]?(\d+)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RegenCareerPolicyContext:
    player_id: str
    regen_id: str
    generation_season_number: int
    current_season_number: int
    position: str
    personality: dict[str, float]
    current_contract_id: str | None
    active_injury_count: int
    assessment: RegenCareerAssessment


class RegenCareerPolicyService:
    """Repository adapter for the tested Phase 6C retirement policy.

    This service is read-only. It converts existing GTEX records into the
    policy input and returns an auditable assessment. It intentionally does
    not retire players or mutate lifecycle state yet.
    """

    def __init__(self, session: Session, *, clock: RegenCareerClock | None = None) -> None:
        self.session = session
        self.clock = clock or RegenCareerClock()

    def assess(
        self,
        player_id: str,
        *,
        current_season_number: int | None = None,
        season_virtual_month_index: Mapping[int, int] | None = None,
        injury_burden: float = 0.0,
        playing_time: float = 0.5,
        performance_trajectory: float = 0.5,
        contract_security: float = 0.5,
        market_demand: float = 0.5,
        salary_burden: float = 0.5,
        willingness_to_continue: float | None = None,
        retirement_threshold: float = 0.85,
        reference_on: date | None = None,
    ) -> RegenCareerPolicyContext:
        player = self.session.get(Player, player_id)
        if player is None:
            raise ValueError(f"Player {player_id} was not found")
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        if regen is None:
            raise ValueError(f"Player {player_id} is not a regen")

        generation_season_number = self._generation_season_number(regen.id)
        current = current_season_number or self._current_season_number(reference_on=reference_on)
        mapping = dict(season_virtual_month_index or self._season_virtual_month_index())
        virtual_age_months = self.clock.virtual_age_months_from_seasons(
            generation_season_number=generation_season_number,
            current_season_number=current,
            season_virtual_month_index=mapping,
        )

        personality = self._personality(regen.id)
        willingness = (
            willingness_to_continue
            if willingness_to_continue is not None
            else self._willingness_from_personality(personality)
        )
        effective_date = reference_on or date.today()
        active_contract = self._active_contract(player_id=player_id, reference_on=effective_date)
        active_injuries = self._active_injury_count(player_id=player_id, reference_on=effective_date)
        computed_injury_burden = self._injury_burden_from_cases(player_id=player_id, reference_on=effective_date)

        effective_playing_time = 0.0 if computed_injury_burden >= 0.8 else playing_time
        effective_willingness = 0.0 if computed_injury_burden >= 0.8 else willingness
        effective_market_demand = 0.0 if computed_injury_burden >= 0.8 else market_demand
        effective_trajectory = 0.0 if computed_injury_burden >= 0.8 else performance_trajectory
        effective_contract_security = 0.0 if computed_injury_burden >= 0.8 else (contract_security if active_contract is not None else 0.0)

        assessment = self.clock.assess(
            RegenRetirementInputs(
                virtual_age_months=virtual_age_months,
                position=player.normalized_position or player.position or "midfielder",
                injury_burden=max(float(injury_burden), computed_injury_burden, min(1.0, active_injuries / 3.0)),
                playing_time=effective_playing_time,
                performance_trajectory=effective_trajectory,
                contract_security=effective_contract_security,
                market_demand=effective_market_demand,
                salary_burden=salary_burden,
                willingness_to_continue=effective_willingness,
                ambition=personality.get("ambition", 0.5),
                resilience=personality.get("resilience", 0.5),
                loyalty=personality.get("loyalty", 0.5),
                achievements=0.0,
                club_opportunity=playing_time,
                retirement_threshold=retirement_threshold,
            )
        )
        return RegenCareerPolicyContext(
            player_id=player_id,
            regen_id=regen.regen_id,
            generation_season_number=generation_season_number,
            current_season_number=current,
            position=player.normalized_position or player.position or "midfielder",
            personality=personality,
            current_contract_id=active_contract.id if active_contract is not None else None,
            active_injury_count=active_injuries,
            assessment=assessment,
        )

    def _generation_season_number(self, regen_profile_id: str) -> int:
        events = list(
            self.session.scalars(
                select(RegenGenerationEvent)
                .where(RegenGenerationEvent.regen_profile_id == regen_profile_id)
                .order_by(RegenGenerationEvent.created_at.asc(), RegenGenerationEvent.id.asc())
            )
        )
        for event in events:
            raw_values = (
                event.season_label,
                str((event.metadata_json or {}).get("season_number", "")),
            )
            for raw in raw_values:
                match = _SEASON_NUMBER_RE.search(raw.strip())
                if match:
                    return int(match.group(1))
        raise ValueError("Regen generation season is unavailable; retirement age must remain unknown")

    def _current_season_number(self, *, reference_on: date | None) -> int:
        seasons = list(
            self.session.scalars(select(RegenSeason).order_by(RegenSeason.season_number.desc())).all()
        )
        if not seasons:
            raise ValueError("No GTEX seasons are configured")
        if reference_on is None:
            active = next((season for season in seasons if season.is_active), None)
            return active.season_number if active is not None else seasons[0].season_number
        eligible = [
            season
            for season in seasons
            if season.start_date <= reference_on <= season.end_date
        ]
        if eligible:
            return max(season.season_number for season in eligible)
        past = [season for season in seasons if season.start_date <= reference_on]
        if past:
            return max(season.season_number for season in past)
        raise ValueError("Reference date occurs before the configured GTEX season timeline")

    def _season_virtual_month_index(self) -> dict[int, int]:
        seasons = list(
            self.session.scalars(select(RegenSeason).order_by(RegenSeason.season_number.asc())).all()
        )
        mapping: dict[int, int] = {}
        for season in seasons:
            raw = (season.metadata_json or {}).get("virtual_age_month_index")
            if raw is None:
                raise ValueError("GTEX season virtual-age mapping is incomplete")
            mapping[season.season_number] = int(raw)
        return mapping

    def _personality(self, regen_profile_id: str) -> dict[str, float]:
        row = self.session.scalar(
            select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen_profile_id)
        )
        if row is None:
            return {}
        return {
            "ambition": float(row.ambition) / 100.0,
            "loyalty": float(row.loyalty) / 100.0,
            "resilience": float(row.resilience) / 100.0,
        }

    def _active_contract(self, *, player_id: str, reference_on: date) -> PlayerContract | None:
        contracts = list(
            self.session.scalars(
                select(PlayerContract)
                .where(PlayerContract.player_id == player_id)
                .order_by(PlayerContract.starts_on.desc(), PlayerContract.created_at.desc())
            ).all()
        )
        return next(
            (contract for contract in contracts if contract.starts_on <= reference_on <= contract.ends_on),
            None,
        )

    def _active_injury_count(self, *, player_id: str, reference_on: date) -> int:
        injuries = list(
            self.session.scalars(select(PlayerInjuryCase).where(PlayerInjuryCase.player_id == player_id)).all()
        )
        return sum(
            1
            for injury in injuries
            if injury.occurred_on <= reference_on
            and injury.expected_return_on is not None
            and injury.expected_return_on >= reference_on
        )

    def _injury_burden_from_cases(self, *, player_id: str, reference_on: date) -> float:
        injuries = list(
            self.session.scalars(select(PlayerInjuryCase).where(PlayerInjuryCase.player_id == player_id)).all()
        )
        active = [
            injury
            for injury in injuries
            if injury.occurred_on <= reference_on
            and (injury.expected_return_on is None or injury.expected_return_on >= reference_on)
        ]
        if not active:
            return 0.0
        burden_weights = {
            "season_ending": 1.0,
            "major": 0.67,
            "moderate": 0.33,
            "minor": 0.15,
        }
        return min(1.0, max((burden_weights.get(str(inj.severity).lower(), 0.33) for inj in active), default=0.0))

    @staticmethod
    def _willingness_from_personality(personality: Mapping[str, float]) -> float:
        ambition = float(personality.get("ambition", 0.5))
        resilience = float(personality.get("resilience", 0.5))
        loyalty = float(personality.get("loyalty", 0.5))
        return max(0.0, min(1.0, (ambition * 0.35) + (resilience * 0.35) + (loyalty * 0.30)))


__all__ = ["RegenCareerPolicyContext", "RegenCareerPolicyService"]
