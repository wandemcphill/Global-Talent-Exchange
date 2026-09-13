from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PersonalManagerBand(IntEnum):
    BAND_60_70 = 1
    BAND_71_80 = 2
    BAND_81_90 = 3
    BAND_91_95 = 4
    BAND_96_99 = 5


_BOUNDS: dict[PersonalManagerBand, tuple[int, int]] = {
    PersonalManagerBand.BAND_60_70: (60, 70),
    PersonalManagerBand.BAND_71_80: (71, 80),
    PersonalManagerBand.BAND_81_90: (81, 90),
    PersonalManagerBand.BAND_91_95: (91, 95),
    PersonalManagerBand.BAND_96_99: (96, 99),
}


@dataclass(frozen=True, slots=True)
class PersonalManagerCreation:
    user_id: str
    quality_band: PersonalManagerBand
    minimum_gsi: int
    maximum_gsi: int
    fan_coin_price: int
    permanent: bool = True
    transferable: bool = False
    salary_bearing: bool = False


def quality_bounds(band: PersonalManagerBand) -> tuple[int, int]:
    return _BOUNDS[PersonalManagerBand(band)]


def validate_personal_manager_creation(
    *,
    user_id: str,
    quality_band: PersonalManagerBand,
    fan_coin_price: int,
    already_exists: bool,
) -> PersonalManagerCreation:
    if already_exists:
        raise ValueError("personal_manager_already_exists")
    if not user_id.strip():
        raise ValueError("personal_manager_user_required")
    if fan_coin_price <= 0:
        raise ValueError("personal_manager_price_must_be_positive")
    minimum_gsi, maximum_gsi = quality_bounds(quality_band)
    return PersonalManagerCreation(
        user_id=user_id,
        quality_band=PersonalManagerBand(quality_band),
        minimum_gsi=minimum_gsi,
        maximum_gsi=maximum_gsi,
        fan_coin_price=fan_coin_price,
    )


__all__ = [
    "PersonalManagerBand",
    "PersonalManagerCreation",
    "quality_bounds",
    "validate_personal_manager_creation",
]
