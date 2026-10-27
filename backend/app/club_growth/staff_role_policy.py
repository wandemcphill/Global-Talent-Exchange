from __future__ import annotations

from dataclasses import dataclass


ROLE_FIRST_TEAM_MANAGER = "first_team_manager"
ROLE_GENERAL_MANAGER = "general_manager"
ROLE_HEAD_OF_YOUTH_DEVELOPMENT = "head_of_youth_development"
ROLE_YOUTH_COACH = "youth_coach"
ROLE_FIRST_TEAM_COACH = "first_team_coach"
ROLE_SCOUT = "scout"
ROLE_AGENT = "agent"
ROLE_MEDICAL = "medical"
ROLE_PERFORMANCE_ANALYST = "performance_analyst"

GENERAL_MANAGER_CAPABILITIES = frozenset({
    "operations",
    "financial_acumen",
    "negotiation",
    "talent_evaluation",
    "recruitment_strategy",
    "budget_management",
    "transfer_planning",
})
HEAD_OF_YOUTH_DEVELOPMENT_CAPABILITIES = frozenset({
    "talent_identification",
    "potential_assessment",
    "recruitment_network",
    "academy_growth",
    "regen_development",
    "youth_development",
    "academy_recruitment",
})
COACH_SPECIALISATIONS = frozenset({
    "coach",
    "youth_coach",
    "goalkeeping_coach",
    "fitness_coach",
    "technical_coach",
    "tactical_coach",
})
MEDICAL_SPECIALISATIONS = frozenset({
    "medical",
    "physio",
    "doctor",
    "sports_scientist",
})


@dataclass(frozen=True, slots=True)
class StaffRoleDecision:
    role_key: str
    allowed: bool
    reason: str
    consumes_salary: bool = True


def normalise_staff_role(role_key: str | None) -> str:
    raw = "_".join(str(role_key or "").strip().lower().replace("-", " ").split())
    aliases = {
        "manager": ROLE_FIRST_TEAM_MANAGER,
        "head_coach": ROLE_FIRST_TEAM_MANAGER,
        "first_team_manager": ROLE_FIRST_TEAM_MANAGER,
        "gm": ROLE_GENERAL_MANAGER,
        "general_manager": ROLE_GENERAL_MANAGER,
        "director_of_football": ROLE_GENERAL_MANAGER,
        "hoyd": ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        "head_of_youth_development": ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        "youth_development_manager": ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        "academy_director": ROLE_HEAD_OF_YOUTH_DEVELOPMENT,
        "youth_coach": ROLE_YOUTH_COACH,
        "academy_coach": ROLE_YOUTH_COACH,
        "coach": ROLE_FIRST_TEAM_COACH,
        "first_team_coach": ROLE_FIRST_TEAM_COACH,
        "medical_staff": ROLE_MEDICAL,
        "doctor": ROLE_MEDICAL,
        "physio": ROLE_MEDICAL,
        "sports_scientist": ROLE_MEDICAL,
        "performance_analyst": ROLE_PERFORMANCE_ANALYST,
        "analyst": ROLE_PERFORMANCE_ANALYST,
        "scout": ROLE_SCOUT,
        "agent": ROLE_AGENT,
    }
    return aliases.get(raw, raw)


def evaluate_staff_role(
    *,
    role_key: str | None,
    staff_type: str | None,
    specialisations: set[str] | frozenset[str] | None = None,
    retired_regen: bool = False,
    medical_qualified: bool = False,
    personal_manager: bool = False,
) -> StaffRoleDecision:
    role = normalise_staff_role(role_key)
    staff = str(staff_type or "").strip().lower()
    skills = {str(item).strip().lower() for item in (specialisations or set())}

    if personal_manager:
        if role != ROLE_FIRST_TEAM_MANAGER:
            return StaffRoleDecision(role, False, "personal_manager_only_supports_first_team_manager")
        return StaffRoleDecision(role, True, "personal_manager_is_profile_bound", consumes_salary=False)

    if role == ROLE_GENERAL_MANAGER:
        if (
            staff in {"general_manager", "director_of_football"}
            or skills & GENERAL_MANAGER_CAPABILITIES
        ):
            return StaffRoleDecision(role, True, "qualified_general_management_role")
        return StaffRoleDecision(role, False, "general_manager_requires_operations_or_transfer_capability")

    if role == ROLE_HEAD_OF_YOUTH_DEVELOPMENT:
        if (
            staff in {"head_of_youth_development", "youth_development_manager", "academy_director"}
            or skills & HEAD_OF_YOUTH_DEVELOPMENT_CAPABILITIES
        ):
            return StaffRoleDecision(role, True, "qualified_youth_development_leadership")
        return StaffRoleDecision(role, False, "head_of_youth_development_requires_academy_capability")

    if role == ROLE_FIRST_TEAM_MANAGER:
        if retired_regen or staff in COACH_SPECIALISATIONS or staff == "manager" or skills & COACH_SPECIALISATIONS:
            return StaffRoleDecision(role, True, "manager_is_a_club_appointment")
        return StaffRoleDecision(role, False, "manager_requires_coaching_or_manager_qualification")

    if role == ROLE_YOUTH_COACH:
        if staff in COACH_SPECIALISATIONS or skills & COACH_SPECIALISATIONS:
            return StaffRoleDecision(role, True, "qualified_coaching_role")
        return StaffRoleDecision(role, False, "youth_coach_requires_coaching_qualification")

    if role == ROLE_FIRST_TEAM_COACH:
        if staff in COACH_SPECIALISATIONS or skills & COACH_SPECIALISATIONS:
            return StaffRoleDecision(role, True, "qualified_coaching_role")
        return StaffRoleDecision(role, False, "first_team_coach_requires_coaching_qualification")

    if role == ROLE_MEDICAL:
        if medical_qualified or staff in MEDICAL_SPECIALISATIONS or skills & MEDICAL_SPECIALISATIONS:
            return StaffRoleDecision(role, True, "medical_qualification_present")
        return StaffRoleDecision(role, False, "medical_role_requires_explicit_qualification")

    if role == ROLE_SCOUT:
        if staff == "scout" or "scouting" in skills:
            return StaffRoleDecision(role, True, "qualified_scouting_role")
        return StaffRoleDecision(role, False, "scout_role_requires_scouting_capability")

    if role == ROLE_AGENT:
        if staff == "agent" or "negotiation" in skills or "market_insight" in skills:
            return StaffRoleDecision(role, True, "qualified_agent_role")
        return StaffRoleDecision(role, False, "agent_role_requires_negotiation_or_market_capability")

    if role == ROLE_PERFORMANCE_ANALYST:
        if staff in {"analyst", "performance_analyst"} or "analysis" in skills:
            return StaffRoleDecision(role, True, "qualified_analysis_role")
        return StaffRoleDecision(role, False, "performance_analysis_requires_analysis_capability")

    return StaffRoleDecision(role, False, "unknown_staff_role")


__all__ = [
    "COACH_SPECIALISATIONS",
    "GENERAL_MANAGER_CAPABILITIES",
    "HEAD_OF_YOUTH_DEVELOPMENT_CAPABILITIES",
    "MEDICAL_SPECIALISATIONS",
    "ROLE_AGENT",
    "ROLE_FIRST_TEAM_COACH",
    "ROLE_FIRST_TEAM_MANAGER",
    "ROLE_GENERAL_MANAGER",
    "ROLE_HEAD_OF_YOUTH_DEVELOPMENT",
    "ROLE_MEDICAL",
    "ROLE_PERFORMANCE_ANALYST",
    "ROLE_SCOUT",
    "ROLE_YOUTH_COACH",
    "StaffRoleDecision",
    "evaluate_staff_role",
    "normalise_staff_role",
]
