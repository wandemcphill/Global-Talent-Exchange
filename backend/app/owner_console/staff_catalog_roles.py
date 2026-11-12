"""Map an FM23 staff row onto one GTEX executive role.

FM23's English export has no job named Director of Football. That seat is
stored as General Manager or Technical Director. Either job qualifies the
person as a GTEX general manager when the desk rating clears the same floor
used for every other executive. Board titles (Director, Managing Director)
stay on the normal highest-rating rule, so a club president is not hired as
the sporting director.
"""

from __future__ import annotations

EXECUTIVE_RATING_FLOOR = 65

# Jobs that are the director-of-football seat in the FM23 staff export.
FOOTBALL_DIRECTOR_JOBS = frozenset(
    {
        "director of football",
        "sporting director",
        "general manager",
        "technical director",
    }
)


def _job_key(job: str | None) -> str:
    return " ".join(str(job or "").strip().lower().replace("_", " ").replace("-", " ").split())


def assign_executive_staff_role(
    *,
    job: str | None,
    head_coach: int,
    general_manager: int,
    technical_director: int = 0,
    youth: int,
    scout: int,
    physio: int,
) -> tuple[str, int] | None:
    """Return the single GTEX role and the rating that earned it."""
    key = _job_key(job)
    if key in FOOTBALL_DIRECTOR_JOBS:
        desk = general_manager if key == "general manager" else max(general_manager, technical_director)
        if desk >= EXECUTIVE_RATING_FLOOR:
            return "general_manager", desk

    best_role = "first_team_manager"
    best_rating = head_coach
    if general_manager > best_rating:
        best_role = "general_manager"
        best_rating = general_manager
    if youth > best_rating:
        best_role = "head_of_youth_development"
        best_rating = youth
    if scout > best_rating:
        best_role = "chief_scout"
        best_rating = scout
    if physio > best_rating:
        best_role = "medical_director"
        best_rating = physio
    if best_rating < EXECUTIVE_RATING_FLOOR:
        return None
    return best_role, best_rating
