from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.base import utcnow
from app.models.club_growth import AcademyProfile, ClubStaffAssignment, ClubStaffContract
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.wallets.service import WalletService


class FacilityEconomyError(ValueError):
    """Base error for facility economic operations."""


FACILITY_FIELD_MAP: dict[str, str] = {
    "training": "training_level",
    "academy": "academy_level",
    "medical": "medical_level",
    "branding": "branding_level",
    "youth_recruitment": "youth_recruitment_level",
}

BASE_FACILITY_UPGRADE_FANCOIN = Decimal("500.0000")
BASE_UPKEEP_PER_LEVEL = Decimal("100.0000")


def calculate_upgrade_cost(facility_key: str, target_level: int) -> Decimal:
    """Calculate the escalating Fan Coin investment cost for upgrading a facility."""
    normalized_key = facility_key.strip().lower()
    if normalized_key not in FACILITY_FIELD_MAP:
        raise FacilityEconomyError(
            f"Invalid facility key '{facility_key}'. Must be one of {tuple(FACILITY_FIELD_MAP)}."
        )
    if target_level <= 1 or target_level > 10:
        raise FacilityEconomyError("Target level must be between 2 and 10.")
    multiplier = Decimal(str(round(target_level**1.6, 4)))
    return (BASE_FACILITY_UPGRADE_FANCOIN * multiplier).quantize(Decimal("0.0001"))


def calculate_completion_seasons(facility_key: str, target_level: int) -> int:
    """Calculate the GTEX season build duration for completing a facility upgrade."""
    normalized_key = facility_key.strip().lower()
    if normalized_key not in FACILITY_FIELD_MAP:
        raise FacilityEconomyError(
            f"Invalid facility key '{facility_key}'. Must be one of {tuple(FACILITY_FIELD_MAP)}."
        )
    return 1 + (target_level // 3)


@dataclass(slots=True)
class AcademyFacilityEconomyService:
    session: Session

    def ensure_facility(self, club_id: str) -> ClubFacility:
        facility = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club_id))
        if facility is None:
            club = self.session.get(ClubProfile, club_id)
            if club is None:
                raise FacilityEconomyError(f"Club {club_id} was not found.")
            facility = ClubFacility(
                club_id=club_id,
                training_level=1,
                academy_level=1,
                medical_level=1,
                branding_level=1,
                youth_recruitment_level=1,
                upkeep_cost_fancoin=Decimal("500.0000"),
                in_progress_upgrades_json={},
                facility_effects_json={},
            )
            self.session.add(facility)
            self.session.flush()
        return facility

    def ensure_academy_profile(self, club_id: str) -> AcademyProfile:
        profile = self.session.scalar(select(AcademyProfile).where(AcademyProfile.club_id == club_id))
        if profile is None:
            club = self.session.get(ClubProfile, club_id)
            if club is None:
                raise FacilityEconomyError(f"Club {club_id} was not found.")
            profile = AcademyProfile(
                club_id=club_id,
                level=1,
                investment_minor=0,
                capacity_limit=18,
                metadata_json={},
            )
            self.session.add(profile)
            self.session.flush()
        return profile

    def start_facility_upgrade(
        self,
        *,
        actor: User,
        club_id: str,
        facility_key: str,
        current_season_number: int = 1,
    ) -> dict[str, Any]:
        normalized_key = facility_key.strip().lower()
        attr_name = FACILITY_FIELD_MAP.get(normalized_key)
        if attr_name is None:
            raise FacilityEconomyError(
                f"Invalid facility key '{facility_key}'. Must be one of {tuple(FACILITY_FIELD_MAP)}."
            )

        facility = self.ensure_facility(club_id)
        current_level = int(getattr(facility, attr_name, 1))
        if current_level >= 10:
            raise FacilityEconomyError(f"Facility '{facility_key}' is already at maximum level 10.")

        target_level = current_level + 1
        in_progress = dict(facility.in_progress_upgrades_json or {})
        if normalized_key in in_progress:
            raise FacilityEconomyError(f"An upgrade for facility '{facility_key}' is already in progress.")

        cost_fancoin = calculate_upgrade_cost(normalized_key, target_level)
        build_duration_seasons = calculate_completion_seasons(normalized_key, target_level)
        target_season = current_season_number + build_duration_seasons

        wallet_service = WalletService()
        fancoin_summary = wallet_service.get_wallet_summary(self.session, actor, currency=LedgerUnit.CREDIT)
        if fancoin_summary.available_balance < cost_fancoin:
            raise FacilityEconomyError(
                f"Insufficient Fan Coin balance. Required: {cost_fancoin} FanCoin, Available: {fancoin_summary.available_balance} FanCoin."
            )

        wallet_service.settle_available_funds(
            self.session,
            user=actor,
            amount=cost_fancoin,
            reference=f"facility_upgrade:{club_id}:{normalized_key}:{target_level}",
            description=f"Fan Coin investment for {normalized_key} level {target_level} facility upgrade",
            external_reference=f"ext:facility_upgrade:{club_id}:{normalized_key}:{target_level}",
            unit=LedgerUnit.CREDIT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        )

        build_job = {
            "facility_key": normalized_key,
            "current_level": current_level,
            "target_level": target_level,
            "cost_fancoin": str(cost_fancoin),
            "start_season": current_season_number,
            "target_season": target_season,
            "build_duration_seasons": build_duration_seasons,
            "started_at": utcnow().isoformat(),
        }
        in_progress[normalized_key] = build_job
        facility.in_progress_upgrades_json = in_progress
        flag_modified(facility, "in_progress_upgrades_json")

        if build_duration_seasons <= 0 or current_season_number >= target_season:
            self.advance_season_facility_upgrades(club_id=club_id, current_season_number=target_season)

        self.session.flush()
        return {
            "club_id": club_id,
            "facility_key": normalized_key,
            "current_level": getattr(facility, attr_name),
            "target_level": target_level,
            "cost_fancoin": cost_fancoin,
            "build_duration_seasons": build_duration_seasons,
            "target_season": target_season,
            "in_progress": normalized_key in (facility.in_progress_upgrades_json or {}),
        }

    def advance_season_facility_upgrades(
        self,
        *,
        club_id: str,
        current_season_number: int,
    ) -> list[str]:
        facility = self.ensure_facility(club_id)
        in_progress = dict(facility.in_progress_upgrades_json or {})
        if not in_progress:
            return []

        completed_keys: list[str] = []
        for key, job in list(in_progress.items()):
            target_season = int(job.get("target_season", 0))
            if current_season_number >= target_season:
                attr_name = FACILITY_FIELD_MAP.get(key)
                if attr_name is not None:
                    target_level = int(job.get("target_level", getattr(facility, attr_name) + 1))
                    setattr(facility, attr_name, target_level)
                    if key == "academy":
                        academy = self.ensure_academy_profile(club_id)
                        academy.level = target_level
                        academy.capacity_limit = 10 + (target_level * 5) + (facility.youth_recruitment_level * 3)
                completed_keys.append(key)
                del in_progress[key]

        if completed_keys:
            facility.in_progress_upgrades_json = in_progress
            flag_modified(facility, "in_progress_upgrades_json")
            self._recalculate_facility_effects_and_upkeep(facility)
            self.session.flush()

        return completed_keys

    def get_academy_capacity_and_quality(self, club_id: str) -> tuple[int, int]:
        facility = self.ensure_facility(club_id)
        academy = self.ensure_academy_profile(club_id)

        staff_bonus = self._get_coaching_and_scouting_staff_bonus(club_id)
        capacity = 10 + (facility.academy_level * 5) + (facility.youth_recruitment_level * 3)
        quality_score = min(
            100,
            int(
                (facility.academy_level * 15)
                + (facility.training_level * 12)
                + (facility.youth_recruitment_level * 10)
                + (facility.medical_level * 8)
                + staff_bonus
            ),
        )

        academy.capacity_limit = capacity
        self.session.flush()
        return capacity, quality_score

    def _get_coaching_and_scouting_staff_bonus(self, club_id: str) -> int:
        statement = (
            select(ClubStaffContract)
            .join(ClubStaffAssignment, ClubStaffAssignment.staff_contract_id == ClubStaffContract.id)
            .where(
                ClubStaffContract.club_id == club_id,
                ClubStaffContract.status == "active",
                ClubStaffAssignment.active.is_(True),
            )
        )
        active_contracts = list(self.session.scalars(statement).all())
        total_rating = sum(
            contract.staff_profile.rating
            for contract in active_contracts
            if contract.staff_profile is not None
            and contract.staff_profile.staff_type in {"coach", "scout", "manager", "academy_director"}
        )
        return min(35, total_rating // 4)

    def _recalculate_facility_effects_and_upkeep(self, facility: ClubFacility) -> None:
        total_levels = (
            facility.training_level
            + facility.academy_level
            + facility.medical_level
            + facility.branding_level
            + facility.youth_recruitment_level
        )
        facility.upkeep_cost_fancoin = (Decimal("100.0000") * Decimal(total_levels)).quantize(Decimal("0.0001"))
        facility.facility_effects_json = {
            "training_development_bonus_pct": facility.training_level * 5,
            "medical_recovery_speed_bonus_pct": facility.medical_level * 6,
            "youth_recruitment_quality_floor": 30 + facility.youth_recruitment_level * 4,
            "branding_revenue_multiplier_bps": 10000 + facility.branding_level * 300,
        }
        flag_modified(facility, "facility_effects_json")


__all__ = [
    "BASE_FACILITY_UPGRADE_FANCOIN",
    "BASE_UPKEEP_PER_LEVEL",
    "FACILITY_FIELD_MAP",
    "AcademyFacilityEconomyService",
    "FacilityEconomyError",
    "calculate_completion_seasons",
    "calculate_upgrade_cost",
]
