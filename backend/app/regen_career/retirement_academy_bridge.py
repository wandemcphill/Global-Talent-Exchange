from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_growth.schemas import AcademyGenerateProspectsRequest
from app.club_growth.service import ClubGrowthService
from app.models.club_growth import AcademyGenerationRun, AcademyProspect
from app.models.club_profile import ClubProfile
from app.models.user import User

ENABLED_ENV = "GTE_REGEN_LEGACY_INTAKE_ENABLED"


@dataclass(frozen=True, slots=True)
class RetirementAcademyBridgeResult:
    status: str
    trigger_key: str
    prospect_ids: tuple[str, ...] = ()


class RegenRetirementAcademyBridge:
    """Consumes retirement legacy plans through the existing academy generator."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def enabled() -> bool:
        return os.getenv(ENABLED_ENV, "0").strip().lower() in {"1", "true", "yes", "on"}

    def consume(self, *, state: dict[str, Any]) -> RetirementAcademyBridgeResult | None:
        plan = dict(state.get("legacy_intake_plan") or {})
        trigger_key = str(plan.get("trigger_key") or "").strip()
        if not trigger_key:
            return None
        if plan.get("generation_status") == "completed":
            return RetirementAcademyBridgeResult(status="completed", trigger_key=trigger_key)
        if not self.enabled():
            return RetirementAcademyBridgeResult(status="pending", trigger_key=trigger_key)

        existing_run = self.session.scalar(
            select(AcademyGenerationRun).where(AcademyGenerationRun.run_seed == trigger_key)
        )
        if existing_run is not None:
            prospect_ids = tuple(
                str(item)
                for item in dict(existing_run.metadata_json or {}).get("legacy_prospect_ids", [])
            )
            return RetirementAcademyBridgeResult(
                status="completed",
                trigger_key=trigger_key,
                prospect_ids=prospect_ids,
            )

        club_id = str(plan.get("club_id") or "").strip()
        count = max(1, min(6, int(plan.get("successor_count") or 1)))
        quality_floor = max(0, min(99, int(plan.get("successor_quality_floor_gsi") or 0)))
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ValueError(f"Retirement academy club {club_id} was not found")
        owner = self.session.get(User, club.owner_user_id)
        if owner is None:
            raise ValueError(f"Retirement academy club owner {club.owner_user_id} was not found")

        from app.services.academy_facility_economy_service import AcademyFacilityEconomyService

        facility_service = AcademyFacilityEconomyService(self.session)
        _capacity, facility_quality_score = facility_service.get_academy_capacity_and_quality(club_id)
        effective_quality_floor = min(99, quality_floor + (facility_quality_score // 10))

        generated = ClubGrowthService(self.session).generate_prospects(
            actor=owner,
            club_id=club_id,
            payload=AcademyGenerateProspectsRequest(count=count, seed=trigger_key),
        )
        prospect_ids = tuple(str(item.id) for item in generated)
        if len(prospect_ids) != count:
            raise RuntimeError("Academy generator did not create the requested successor count")

        for prospect in self.session.scalars(
            select(AcademyProspect).where(AcademyProspect.id.in_(prospect_ids))
        ).all():
            prospect.current_ability = max(int(prospect.current_ability), effective_quality_floor)
            prospect.potential = max(int(prospect.potential), effective_quality_floor, int(prospect.current_ability))
            prospect.metadata_json = {
                **dict(prospect.metadata_json or {}),
                "legacy_trigger_key": trigger_key,
                "retirement_regen_id": plan.get("retiring_regen_id"),
                "retirement_player_id": plan.get("retiring_player_id"),
                "successor_quality_floor_gsi": quality_floor,
                "effective_quality_floor_gsi": effective_quality_floor,
                "facility_quality_score": facility_quality_score,
                "legacy_generation": True,
            }

        for run in self.session.scalars(
            select(AcademyGenerationRun).where(
                AcademyGenerationRun.club_id == club_id,
                AcademyGenerationRun.run_seed == trigger_key,
            )
        ).all():
            run.metadata_json = {
                **dict(run.metadata_json or {}),
                "legacy_trigger_key": trigger_key,
                "retirement_regen_id": plan.get("retiring_regen_id"),
                "retirement_player_id": plan.get("retiring_player_id"),
                "successor_quality_floor_gsi": quality_floor,
                "legacy_generation": True,
                "legacy_prospect_ids": list(prospect_ids),
            }

        return RetirementAcademyBridgeResult(
            status="completed",
            trigger_key=trigger_key,
            prospect_ids=prospect_ids,
        )


__all__ = ["ENABLED_ENV", "RegenRetirementAcademyBridge", "RetirementAcademyBridgeResult"]
