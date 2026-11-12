"""Keep scarce staff desks hireable.

Named catalog people stay one club at a time. The general-manager catalog is
only a few dozen people because ingestion kept each staff member's single
highest rating, and a coach or scout rating almost always beat the general
manager rating. Once those named directors are appointed, the desk would be
empty.

The bench below is original sporting directors, spread across foundation,
established, and elite wage bands. Whenever free general managers fall under
the floor, the next market open brings the free pool back up to that floor.
Elite directors stay the small top band.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_growth.staff_role_policy import ROLE_GENERAL_MANAGER
from app.models.club_growth import ClubStaffProfile

GENERAL_MANAGER_FREE_AGENT_FLOOR = 160
BENCH_ORIGIN = "staff_bench"
_BENCH_KEY_PREFIX = "staff:bench-gm-"

_GIVEN_NAMES = (
    "Adaeze", "Chinedu", "Ifeoma", "Kunle", "Ngozi", "Tunde", "Yewande", "Zubair",
    "Amara", "Kofi", "Abena", "Kwame", "Lerato", "Thabo", "Amina", "Jelani",
    "Mateo", "Lucia", "Andres", "Camila", "Soren", "Ines", "Pavel", "Anika",
    "Hiro", "Mei", "Arun", "Priya", "Leila", "Omar", "Noor", "Farid",
    "Elena", "Marcus", "Helena", "Jonas", "Clara", "Nikolai", "Sofia", "Idris",
)
_FAMILY_NAMES = (
    "Adeyemi", "Balogun", "Okeke", "Lawal", "Mensah", "Boateng", "Diallo", "Ndlovu",
    "Okoro", "Adebayo", "Mensima", "Traore", "Dlamini", "Abebe", "Kamara", "Mwangi",
    "Navarro", "Almeida", "Costa", "Bergstrom", "Novak", "Horvat", "Petrov", "Kowalska",
    "Sato", "Nakamura", "Iyer", "Rahman", "Haddad", "Farouk", "Elsayed", "Qureshi",
    "Moretti", "Keller", "Lindholm", "Rossi", "Duarte", "Silva", "Pereira", "Okafor",
)
_NATIONS = (
    "Nigeria", "Ghana", "Senegal", "South Africa", "Kenya", "Morocco", "Egypt",
    "Brazil", "Argentina", "Portugal", "Spain", "France", "Netherlands", "Germany",
    "Sweden", "Poland", "Japan", "South Korea", "India", "Turkey",
)
_STYLES = (
    "Grassroots Operator",
    "Sell and Rebuild",
    "Academy First",
    "Wage Discipline",
    "Data Recruitment",
    "Commercial Growth",
    "Squad Rebuilding",
    "Global Network",
)
_TEMPERAMENTS = ("pragmatic", "calm", "demanding", "diplomatic", "fiery")
_BANDS = (
    {"weight_slots": 6, "rating": (64, 72), "salary": (450, 1100), "prestige": (12, 28), "rarity": "standard"},
    {"weight_slots": 3, "rating": (73, 80), "salary": (1400, 3200), "prestige": (32, 55), "rarity": "established"},
    {"weight_slots": 1, "rating": (81, 88), "salary": (4500, 9000), "prestige": (62, 82), "rarity": "elite"},
)


def _mix(index: int, low: int, high: int) -> int:
    span = high - low + 1
    return low + ((index * 17 + 3) % span)


def _band_for(index: int) -> dict[str, object]:
    slot = index % 10
    cursor = 0
    for band in _BANDS:
        cursor += int(band["weight_slots"])
        if slot < cursor:
            return band
    return _BANDS[0]


def _unemployed(profile: ClubStaffProfile) -> bool:
    meta = profile.metadata_json or {}
    return str(meta.get("employment_status") or "unemployed") == "unemployed"


def _next_bench_index(profiles: list[ClubStaffProfile]) -> int:
    highest = 0
    for profile in profiles:
        key = profile.market_key or ""
        if not key.startswith(_BENCH_KEY_PREFIX):
            continue
        suffix = key.removeprefix(_BENCH_KEY_PREFIX)
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return highest + 1


def _build_general_manager(index: int) -> ClubStaffProfile:
    band = _band_for(index)
    rating_low, rating_high = band["rating"]  # type: ignore[misc]
    salary_low, salary_high = band["salary"]  # type: ignore[misc]
    prestige_low, prestige_high = band["prestige"]  # type: ignore[misc]
    rating = _mix(index, int(rating_low), int(rating_high))
    salary = _mix(index, int(salary_low), int(salary_high))
    min_prestige = _mix(index + 5, int(prestige_low), int(prestige_high))
    given = _GIVEN_NAMES[index % len(_GIVEN_NAMES)]
    family = _FAMILY_NAMES[(index // len(_GIVEN_NAMES)) % len(_FAMILY_NAMES)]
    nation = _NATIONS[index % len(_NATIONS)]
    style = _STYLES[index % len(_STYLES)]
    temperament = _TEMPERAMENTS[index % len(_TEMPERAMENTS)]
    name = f"{given} {family}"
    staff_id = f"bench-gm-{index:04d}"
    meta = {
        "staff_id": staff_id,
        "employment_status": "unemployed",
        "current_club_id": None,
        "origin": BENCH_ORIGIN,
        "min_prestige": min_prestige,
        "temperament": temperament,
        "style": style,
        "ambition": _mix(index, 8, 18),
        "loyalty": _mix(index + 2, 8, 18),
        "experience_years": max(4, rating // 6),
        "career_history": [],
        "previous_relationships": {},
        "preferred_roles": [ROLE_GENERAL_MANAGER],
        "reputation": min(92, max(40, rating - 4)),
        "nation": nation,
        "negotiation": _mix(index + 1, 10, 19),
        "commercial_acumen": _mix(index + 4, 9, 18),
    }
    return ClubStaffProfile(
        market_key=f"{_BENCH_KEY_PREFIX}{index:04d}",
        display_name=name,
        staff_type=ROLE_GENERAL_MANAGER,
        rarity=str(band["rarity"]),
        rating=rating,
        salary_minor=salary * 100,
        skills_json=[ROLE_GENERAL_MANAGER, style, "negotiation", "budget_management"],
        active=True,
        metadata_json=meta,
    )


def general_manager_supply(session: Session) -> dict[str, int]:
    profiles = list(
        session.scalars(
            select(ClubStaffProfile).where(
                ClubStaffProfile.active.is_(True),
                ClubStaffProfile.staff_type == ROLE_GENERAL_MANAGER,
            )
        ).all()
    )
    available = sum(1 for profile in profiles if _unemployed(profile))
    return {
        "general_manager_available": available,
        "general_manager_floor": GENERAL_MANAGER_FREE_AGENT_FLOOR,
        "general_manager_total": len(profiles),
    }


def replenish_scarce_staff(session: Session) -> dict[str, int]:
    """Top the free general-manager bench back up to the floor."""
    profiles = list(
        session.scalars(
            select(ClubStaffProfile).where(
                ClubStaffProfile.active.is_(True),
                ClubStaffProfile.staff_type == ROLE_GENERAL_MANAGER,
            )
        ).all()
    )
    available = sum(1 for profile in profiles if _unemployed(profile))
    shortfall = GENERAL_MANAGER_FREE_AGENT_FLOOR - available
    created = 0
    if shortfall > 0:
        index = _next_bench_index(profiles)
        for _ in range(shortfall):
            session.add(_build_general_manager(index))
            created += 1
            index += 1
        session.flush()
        available += created
    return {
        "general_manager_available": available,
        "general_manager_floor": GENERAL_MANAGER_FREE_AGENT_FLOOR,
        "general_manager_added": created,
        "general_manager_total": len(profiles) + created,
    }
