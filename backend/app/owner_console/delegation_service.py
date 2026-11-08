from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ecosystem_events import (
    EcosystemActor,
    EcosystemDomain,
    EcosystemEvent,
    EcosystemEventPriority,
    EcosystemSubject,
    gtex_ecosystem_bus,
)
from app.models.base import utcnow
from app.owner_console.models import (
    ClubDelegatedDecision,
    ClubDelegatedDecisionAuditLog,
    ClubDelegationPolicy,
    OwnerClubState,
    OwnerInboxItem,
)


class DelegationError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "delegation_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _require_club_owner(session: Session, club_id: str, user_id: str) -> OwnerClubState:
    """Enforces authoritative club ownership. Rejects non-owners with 403 Forbidden."""
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if state is None:
        raise DelegationError("Club state not found.", 404, code="club_not_found")
    if state.owner_user_id != user_id:
        raise DelegationError("Forbidden: You do not own this club.", 403, code="not_club_owner")
    return state


# ==============================================================================
# 1. Domain Constants & Taxonomy
# ==============================================================================

ACTIVITY_DOMAINS: dict[str, str] = {
    # Sporting Operations
    "first_team_tactics": "sporting",
    "training_and_coaching": "sporting",
    "player_recruitment": "sporting",
    "player_sales": "sporting",
    "contract_renewals": "sporting",
    "youth_recruitment": "sporting",
    "academy_development": "sporting",
    "scouting_assignments": "sporting",
    # Club Operations
    "staff_recruitment_dismissal": "club_operations",
    "operational_expenditure": "club_operations",
    "facilities_infrastructure": "club_operations",
    "club_administration": "club_operations",
    "commercial_partnerships": "club_operations",
    "sponsorship_negotiations": "club_operations",
    "financial_planning": "club_operations",
    # Player and Staff Matters
    "player_complaints": "player_staff",
    "disciplinary_incidents": "player_staff",
    "contract_disputes": "player_staff",
    "development_reviews": "player_staff",
    "staff_performance": "player_staff",
    "player_staff_interactions": "player_staff",
}

MANAGEMENT_MODES = ("hands_on", "balanced", "delegating", "custom", "owner_managed", "gm_led")

ROLE_LABELS = {
    "owner": "Club Owner",
    "general_manager": "General Manager",
    "first_team_manager": "First Team Manager",
    "head_of_youth_development": "Head of Youth Development",
    "chief_scout": "Chief Scout",
    "medical_director": "Medical Director",
}

DEFAULT_FINANCIAL_THRESHOLDS: dict[str, dict[str, float]] = {
    "hands_on": {
        "recruitment_max_gtex": 0.0,
        "sales_min_gtex": 0.0,
        "operational_spend_max_gtex": 0.0,
        "contract_renewal_max_weekly_wage_gtex": 0.0,
        "facility_spend_max_gtex": 0.0,
        "max_expenditure_unapproved_gtex": 0.0,
        "max_staff_salary_unapproved_gtex": 0.0,
        "max_contract_years_unapproved": 0.0,
        "recruitment_budget_gtex": 0.0,
        "wage_budget_gtex": 0.0,
        "min_sale_value_gtex": 0.0,
        "allow_emergency_spending": 0.0,
    },
    "balanced": {
        "recruitment_max_gtex": 25000.0,
        "sales_min_gtex": 5000.0,
        "operational_spend_max_gtex": 10000.0,
        "contract_renewal_max_weekly_wage_gtex": 5000.0,
        "facility_spend_max_gtex": 15000.0,
        "max_expenditure_unapproved_gtex": 10000.0,
        "max_staff_salary_unapproved_gtex": 1500.0,
        "max_contract_years_unapproved": 2.0,
        "recruitment_budget_gtex": 35000.0,
        "wage_budget_gtex": 8000.0,
        "min_sale_value_gtex": 5000.0,
        "allow_emergency_spending": 0.0,
    },
    "delegating": {
        "recruitment_max_gtex": 100000.0,
        "sales_min_gtex": 25000.0,
        "operational_spend_max_gtex": 50000.0,
        "contract_renewal_max_weekly_wage_gtex": 20000.0,
        "facility_spend_max_gtex": 75000.0,
        "max_expenditure_unapproved_gtex": 50000.0,
        "max_staff_salary_unapproved_gtex": 3500.0,
        "max_contract_years_unapproved": 4.0,
        "recruitment_budget_gtex": 120000.0,
        "wage_budget_gtex": 25000.0,
        "min_sale_value_gtex": 25000.0,
        "allow_emergency_spending": 1.0,
    },
}

DEFAULT_FINANCIAL_THRESHOLDS["owner_managed"] = DEFAULT_FINANCIAL_THRESHOLDS["hands_on"]
DEFAULT_FINANCIAL_THRESHOLDS["gm_led"] = DEFAULT_FINANCIAL_THRESHOLDS["delegating"]

DEFAULT_RESERVED_DECISIONS = [
    "staff_recruitment_dismissal",
    "financial_planning",
]


def _build_default_assignments(mode: str) -> dict[str, dict[str, Any]]:
    """Builds standard responsibility, authority, and approval policies for a given mode."""
    assignments: dict[str, dict[str, Any]] = {}

    if mode in ("hands_on", "owner_managed"):
        for activity, domain in ACTIVITY_DOMAINS.items():
            assignments[activity] = {
                "activity_key": activity,
                "domain": domain,
                "responsible_role": "owner",
                "authority_level": "owner_only",
                "requires_owner_approval": True,
                "requires_joint_approval": False,
                "joint_role": None,
            }
        return assignments

    if mode in ("delegating", "gm_led"):
        roles_map = {
            # Sporting
            "first_team_tactics": ("first_team_manager", "full_autonomy", False),
            "training_and_coaching": ("first_team_manager", "full_autonomy", False),
            "player_recruitment": ("general_manager", "delegated_with_limits", False),
            "player_sales": ("general_manager", "delegated_with_limits", False),
            "contract_renewals": ("general_manager", "delegated_with_limits", False),
            "youth_recruitment": ("head_of_youth_development", "full_autonomy", False),
            "academy_development": ("head_of_youth_development", "full_autonomy", False),
            "scouting_assignments": ("chief_scout", "full_autonomy", False),
            # Operations
            "staff_recruitment_dismissal": ("owner", "owner_only", True),
            "operational_expenditure": ("general_manager", "delegated_with_limits", False),
            "facilities_infrastructure": ("general_manager", "delegated_with_limits", True),
            "club_administration": ("general_manager", "full_autonomy", False),
            "commercial_partnerships": ("general_manager", "delegated_with_limits", False),
            "sponsorship_negotiations": ("general_manager", "delegated_with_limits", False),
            "financial_planning": ("owner", "owner_only", True),
            # Matters
            "player_complaints": ("first_team_manager", "full_autonomy", False),
            "disciplinary_incidents": ("first_team_manager", "full_autonomy", False),
            "contract_disputes": ("general_manager", "delegated_with_limits", False),
            "development_reviews": ("head_of_youth_development", "full_autonomy", False),
            "staff_performance": ("general_manager", "delegated_with_limits", True),
            "player_staff_interactions": ("first_team_manager", "full_autonomy", False),
        }
    else:
        # "balanced" (default)
        roles_map = {
            # Sporting
            "first_team_tactics": ("first_team_manager", "full_autonomy", False),
            "training_and_coaching": ("first_team_manager", "full_autonomy", False),
            "player_recruitment": ("general_manager", "delegated_with_limits", False),
            "player_sales": ("general_manager", "delegated_with_limits", False),
            "contract_renewals": ("general_manager", "delegated_with_limits", False),
            "youth_recruitment": ("head_of_youth_development", "full_autonomy", False),
            "academy_development": ("head_of_youth_development", "full_autonomy", False),
            "scouting_assignments": ("chief_scout", "full_autonomy", False),
            # Operations
            "staff_recruitment_dismissal": ("owner", "owner_only", True),
            "operational_expenditure": ("general_manager", "delegated_with_limits", False),
            "facilities_infrastructure": ("owner", "owner_only", True),
            "club_administration": ("general_manager", "full_autonomy", False),
            "commercial_partnerships": ("owner", "delegated_with_limits", True),
            "sponsorship_negotiations": ("general_manager", "delegated_with_limits", True),
            "financial_planning": ("owner", "owner_only", True),
            # Matters
            "player_complaints": ("first_team_manager", "delegated_with_limits", False),
            "disciplinary_incidents": ("first_team_manager", "delegated_with_limits", False),
            "contract_disputes": ("general_manager", "delegated_with_limits", True),
            "development_reviews": ("head_of_youth_development", "full_autonomy", False),
            "staff_performance": ("owner", "owner_only", True),
            "player_staff_interactions": ("first_team_manager", "full_autonomy", False),
        }

    for activity, (role, auth, approval) in roles_map.items():
        assignments[activity] = {
            "activity_key": activity,
            "domain": ACTIVITY_DOMAINS[activity],
            "responsible_role": role,
            "authority_level": auth,
            "requires_owner_approval": approval,
            "requires_joint_approval": activity in {"player_recruitment", "contract_disputes"},
            "joint_role": "first_team_manager" if activity == "player_recruitment" else None,
        }

    return assignments


# ==============================================================================
# 2. Policy Management & State Queries
# ==============================================================================


def get_or_create_delegation_policy(session: Session, club_id: str, owner_user_id: str) -> ClubDelegationPolicy:
    """Retrieves or initializes the authoritative delegation policy for a club."""
    _require_club_owner(session, club_id, owner_user_id)
    policy = session.scalar(select(ClubDelegationPolicy).where(ClubDelegationPolicy.club_id == club_id))
    if policy is not None:
        return policy

    # Initialize with 'balanced' baseline
    mode = "balanced"
    thresholds = dict(DEFAULT_FINANCIAL_THRESHOLDS[mode])
    assignments = _build_default_assignments(mode)

    policy = ClubDelegationPolicy(
        club_id=club_id,
        owner_user_id=owner_user_id,
        mode=mode,
        is_suspended=False,
        suspension_reason=None,
        financial_thresholds_json=thresholds,
        activity_assignments_json=assignments,
        reserved_decisions_json=list(DEFAULT_RESERVED_DECISIONS),
        temporary_overrides_json={},
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return policy


def set_management_configuration(session: Session, club_id: str, owner_user_id: str, mode: str) -> ClubDelegationPolicy:
    """Switches the management mode (hands_on, balanced, delegating, custom)."""
    if mode not in MANAGEMENT_MODES:
        raise DelegationError(f"Invalid management mode '{mode}'. Must be one of {MANAGEMENT_MODES}.", 400)

    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    policy.mode = mode

    if mode != "custom":
        policy.financial_thresholds_json = dict(
            DEFAULT_FINANCIAL_THRESHOLDS.get(mode, DEFAULT_FINANCIAL_THRESHOLDS["balanced"])
        )
        policy.activity_assignments_json = _build_default_assignments(mode)

    _publish_governance_event(
        session,
        club_id,
        owner_user_id,
        "delegation.mode_changed",
        {"new_mode": mode},
    )

    session.commit()
    session.refresh(policy)
    return policy


def update_activity_assignment(
    session: Session,
    club_id: str,
    owner_user_id: str,
    activity_key: str,
    responsible_role: str,
    authority_level: str,
    requires_owner_approval: bool = False,
    requires_joint_approval: bool = False,
    joint_role: str | None = None,
) -> ClubDelegationPolicy:
    """Updates responsibility and authority assignment for a specific club activity."""
    if activity_key not in ACTIVITY_DOMAINS:
        raise DelegationError(f"Unknown activity key '{activity_key}'.", 400)
    if responsible_role not in ROLE_LABELS:
        raise DelegationError(f"Invalid staff role '{responsible_role}'.", 400)
    if authority_level not in {"owner_only", "delegated_with_limits", "full_autonomy"}:
        raise DelegationError(f"Invalid authority level '{authority_level}'.", 400)

    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    assignments = dict(policy.activity_assignments_json or {})

    assignments[activity_key] = {
        "activity_key": activity_key,
        "domain": ACTIVITY_DOMAINS[activity_key],
        "responsible_role": responsible_role,
        "authority_level": authority_level,
        "requires_owner_approval": requires_owner_approval,
        "requires_joint_approval": requires_joint_approval,
        "joint_role": joint_role,
    }

    policy.activity_assignments_json = assignments
    policy.mode = "custom"
    _publish_governance_event(
        session,
        club_id,
        owner_user_id,
        "delegation.activity_updated",
        {
            "activity_key": activity_key,
            "responsible_role": responsible_role,
            "authority_level": authority_level,
        },
    )

    session.commit()
    session.refresh(policy)
    return policy


def update_financial_thresholds(
    session: Session, club_id: str, owner_user_id: str, thresholds: Mapping[str, Any]
) -> ClubDelegationPolicy:
    """Updates financial approval limits."""
    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    current = dict(policy.financial_thresholds_json or {})

    for key, val in thresholds.items():
        try:
            current[key] = max(0.0, float(val))
        except (ValueError, TypeError):
            continue

    policy.financial_thresholds_json = current
    _publish_governance_event(
        session,
        club_id,
        owner_user_id,
        "delegation.thresholds_updated",
        {"financial_thresholds": current},
    )

    session.commit()
    session.refresh(policy)
    return policy


def toggle_delegation_suspension(
    session: Session, club_id: str, owner_user_id: str, suspend: bool, reason: str | None = None
) -> ClubDelegationPolicy:
    """Instantly suspends or restores club delegation. When suspended, all authority reverts to owner."""
    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    policy.is_suspended = suspend
    policy.suspension_reason = reason if suspend else None

    event_name = "delegation.delegation_suspended" if suspend else "delegation.delegation_restored"
    _publish_governance_event(
        session,
        club_id,
        owner_user_id,
        event_name,
        {"is_suspended": suspend, "reason": reason},
        priority=EcosystemEventPriority.HIGH if suspend else EcosystemEventPriority.NORMAL,
    )
    session.commit()
    session.refresh(policy)
    return policy


def set_temporary_override(
    session: Session,
    club_id: str,
    owner_user_id: str,
    activity_key: str,
    override_role: str = "owner",
    reason: str = "Owner emergency intervention",
    expires_at_iso: str | None = None,
) -> ClubDelegationPolicy:
    """Applies a temporary owner override on a specific activity."""
    if activity_key not in ACTIVITY_DOMAINS:
        raise DelegationError(f"Unknown activity key '{activity_key}'.", 400)

    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    overrides = dict(policy.temporary_overrides_json or {})

    overrides[activity_key] = {
        "activity_key": activity_key,
        "override_role": override_role,
        "reason": reason,
        "created_at": utcnow().isoformat(),
        "expires_at": expires_at_iso,
    }

    policy.temporary_overrides_json = overrides
    _publish_governance_event(
        session,
        club_id,
        owner_user_id,
        "delegation.override_applied",
        {"activity_key": activity_key, "override_role": override_role, "reason": reason},
    )

    session.commit()
    session.refresh(policy)
    return policy


def remove_temporary_override(
    session: Session, club_id: str, owner_user_id: str, activity_key: str
) -> ClubDelegationPolicy:
    """Removes a temporary override, restoring normal delegation."""
    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    overrides = dict(policy.temporary_overrides_json or {})

    if activity_key in overrides:
        del overrides[activity_key]
        policy.temporary_overrides_json = overrides
        _publish_governance_event(
            session,
            club_id,
            owner_user_id,
            "delegation.override_removed",
            {"activity_key": activity_key},
        )
        session.commit()
        session.refresh(policy)

    return policy


# ==============================================================================
# 3. Authority Evaluation Engine
# ==============================================================================


class AuthorityEvaluationResult:
    def __init__(
        self,
        allowed: bool,
        requires_approval: bool,
        responsible_role: str,
        authority_level: str,
        reason: str,
        policy_status: str,
        staff_name: str | None = None,
        staff_competence_rating: int | None = None,
        staff_impact: dict[str, Any] | None = None,
    ):
        self.allowed = allowed
        self.requires_approval = requires_approval
        self.responsible_role = responsible_role
        self.authority_level = authority_level
        self.reason = reason
        self.policy_status = policy_status
        self.staff_name = staff_name
        self.staff_competence_rating = staff_competence_rating
        self.staff_impact = staff_impact or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "responsible_role": self.responsible_role,
            "authority_level": self.authority_level,
            "reason": self.reason,
            "policy_status": self.policy_status,
            "staff_name": self.staff_name,
            "staff_competence_rating": self.staff_competence_rating,
            "staff_impact": self.staff_impact,
        }


def evaluate_action_authority(
    session: Session,
    club_id: str,
    actor_user_id: str,
    activity_key: str,
    financial_amount_gtex: float | Decimal | None = None,
    proposed_by_role: str | None = None,
) -> AuthorityEvaluationResult:
    """
    Evaluates whether an actor or delegated staff role is authorized to perform an activity,
    checking policy status, assigned responsibilities, financial thresholds, reserved decisions,
    and temporary overrides.
    """
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if state is None:
        raise DelegationError("Club state not found.", 404)

    is_owner = state.owner_user_id == actor_user_id
    policy = get_or_create_delegation_policy(session, club_id, state.owner_user_id)

    # Determine if evaluating owner acting directly vs evaluating delegated staff authority
    evaluating_owner_direct = is_owner and (not proposed_by_role or proposed_by_role == "owner")

    # 1. Check Suspension Status
    if policy.is_suspended:
        if evaluating_owner_direct:
            return AuthorityEvaluationResult(
                allowed=True,
                requires_approval=False,
                responsible_role="owner",
                authority_level="owner_only",
                reason="Delegation suspended; owner has direct emergency control.",
                policy_status="suspended",
            )
        return AuthorityEvaluationResult(
            allowed=False,
            requires_approval=True,
            responsible_role="owner",
            authority_level="owner_only",
            reason=f"Delegation suspended: {policy.suspension_reason or 'Direct owner oversight required.'}",
            policy_status="suspended",
        )

    # 2. Check Temporary Overrides
    overrides = dict(policy.temporary_overrides_json or {})
    if activity_key in overrides:
        override = overrides[activity_key]
        expires_at_iso = override.get("expires_at")
        is_expired = False
        if expires_at_iso:
            try:
                exp_dt = datetime.fromisoformat(str(expires_at_iso).replace("Z", "+00:00"))
                if utcnow() >= exp_dt:
                    is_expired = True
            except (ValueError, TypeError):
                is_expired = False

        if is_expired:
            # Automatic expiration: prune the expired override and fall through to standard delegation
            del overrides[activity_key]
            policy.temporary_overrides_json = overrides
            session.commit()
            session.refresh(policy)
        else:
            override_role = override.get("override_role", "owner")
            if evaluating_owner_direct or override_role == proposed_by_role:
                return AuthorityEvaluationResult(
                    allowed=True,
                    requires_approval=False,
                    responsible_role=override_role,
                    authority_level="owner_only",
                    reason=f"Temporary override active: {override.get('reason')}",
                    policy_status="override",
                )
            return AuthorityEvaluationResult(
                allowed=False,
                requires_approval=True,
                responsible_role=override_role,
                authority_level="owner_only",
                reason=f"Activity preempted by temporary owner override: {override.get('reason')}",
                policy_status="override",
            )

    # 3. Check Reserved Decisions
    reserved = policy.reserved_decisions_json or []
    if activity_key in reserved:
        if evaluating_owner_direct:
            return AuthorityEvaluationResult(
                allowed=True,
                requires_approval=False,
                responsible_role="owner",
                authority_level="owner_only",
                reason="Reserved owner decision executed directly by owner.",
                policy_status="active",
            )
        return AuthorityEvaluationResult(
            allowed=False,
            requires_approval=True,
            responsible_role="owner",
            authority_level="owner_only",
            reason="Activity is strictly reserved for club owner approval.",
            policy_status="active",
        )

    # 4. Check Activity Assignment
    assignments = policy.activity_assignments_json or {}
    rule = assignments.get(activity_key)
    if not rule:
        # Default fallback
        rule = {
            "responsible_role": "owner",
            "authority_level": "owner_only",
            "requires_owner_approval": True,
        }

    target_role = rule.get("responsible_role", "owner")
    authority_level = rule.get("authority_level", "owner_only")
    mandated_approval = rule.get("requires_owner_approval", False)

    # Evaluate appointed staff competence
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    is_appointed = False

    if target_role == "first_team_manager" and state.manager_json:
        staff_member = dict(state.manager_json)
        for k, v in (exec_staff.get("first_team_manager") or {}).items():
            staff_member.setdefault(k, v)
        is_appointed = bool(staff_member.get("name") and not staff_member.get("is_default"))
    elif target_role in exec_staff and exec_staff[target_role]:
        staff_member = dict(exec_staff[target_role])
        is_appointed = bool(staff_member.get("name"))
    else:
        staff_member = {}
        is_appointed = False

    staff_name = staff_member.get("name") or ROLE_LABELS.get(target_role, target_role)
    staff_rating = int(staff_member.get("rating") or staff_member.get("tactical_rating") or 65)

    # Calculate competence impact
    competence_impact = _calculate_staff_competence_impact(
        target_role, staff_member, activity_key, is_appointed=is_appointed
    )

    # 5. Financial Limit Verification
    requires_approval = mandated_approval
    amount = float(financial_amount_gtex or 0.0)
    thresholds = policy.financial_thresholds_json or {}

    if amount > 0:
        threshold_key_map = {
            "player_recruitment": "recruitment_max_gtex",
            "operational_expenditure": "operational_spend_max_gtex",
            "facilities_infrastructure": "facility_spend_max_gtex",
            "contract_renewals": "contract_renewal_max_weekly_wage_gtex",
        }
        th_key = threshold_key_map.get(activity_key)
        if th_key and th_key in thresholds:
            limit = float(thresholds[th_key])
            if amount > limit:
                requires_approval = True
                return AuthorityEvaluationResult(
                    allowed=True,
                    requires_approval=True,
                    responsible_role=target_role,
                    authority_level=authority_level,
                    reason=f"Transaction {amount:,.0f} GTX exceeds delegated limit {limit:,.0f} GTX for {target_role}.",
                    policy_status="active",
                    staff_name=staff_name,
                    staff_competence_rating=staff_rating,
                    staff_impact=competence_impact,
                )

    if authority_level == "owner_only" and (
        not evaluating_owner_direct or (proposed_by_role and proposed_by_role != "owner")
    ):
        return AuthorityEvaluationResult(
            allowed=False,
            requires_approval=True,
            responsible_role="owner",
            authority_level="owner_only",
            reason="Policy mandates owner-only decision authority.",
            policy_status="active",
            staff_name=staff_name,
            staff_competence_rating=staff_rating,
            staff_impact=competence_impact,
        )

    if proposed_by_role and proposed_by_role != "owner" and target_role != proposed_by_role:
        return AuthorityEvaluationResult(
            allowed=False,
            requires_approval=True,
            responsible_role=target_role,
            authority_level=authority_level,
            reason=f"Activity is assigned to {ROLE_LABELS.get(target_role, target_role)}, not {ROLE_LABELS.get(proposed_by_role, proposed_by_role)}.",
            policy_status="active",
            staff_name=staff_name,
            staff_competence_rating=staff_rating,
            staff_impact=competence_impact,
        )

    return AuthorityEvaluationResult(
        allowed=True,
        requires_approval=requires_approval,
        responsible_role=target_role,
        authority_level=authority_level,
        reason="Action permitted within delegated authority policy.",
        policy_status="active",
        staff_name=staff_name,
        staff_competence_rating=staff_rating,
        staff_impact=competence_impact,
    )


def _calculate_staff_competence_impact(
    role: str, staff_member: dict[str, Any], activity_key: str, is_appointed: bool = False
) -> dict[str, Any]:
    """Calculates quantitative performance adjustments based on staff competence attributes.

    Scoring Methodology:
    - GM (Commercial/Finance): Rating + negotiation skills give 3% to 15% efficiency discount on fees.
    - First Team Manager (Tactics/Training): Tactical flexibility (1-20) adds synergy boost; morale boost if >=14.
    - Head of Youth Dev (Youth/Academy): Youth development rating yields 50% to 100% potential reveal accuracy.
    - Chief Scout (Scouting): Scouting accuracy yields 1-20 confidence rating on talent profiles.
    - Medical Director (Player Health): Medical expertise yields 2% to 40% accelerated recovery rate.

    Advisory Notice:
    Competence calculations are strictly informational decision-support metrics and do not modify core
    game invariants or bypass financial ledger authorization.
    """
    rating = int(staff_member.get("rating") or staff_member.get("tactical_rating") or 65)
    impact: dict[str, Any] = {
        "rating": rating,
        "is_appointed_staff": is_appointed,
        "is_informational_only": True,
        "advisory_notice": "Staff competence metrics provide informational advisory guidance for executive decision-making and do not override platform rules or mutate ledger balances.",
        "scoring_methodology": f"Calculated using {'actual appointed staff attributes' if is_appointed else 'baseline catalog attributes'} for {role} (rating={rating}).",
    }

    if role == "general_manager":
        nego = int(staff_member.get("negotiation") or staff_member.get("ambition") or (rating // 5))
        discount_pct = min(15, max(3, round((nego / 20) * 15, 1)))
        impact["negotiation_discount_pct"] = discount_pct
        impact["summary"] = (
            f"GM {staff_member.get('name', 'Appointee')} achieved a {discount_pct}% cost efficiency on negotiation."
        )
    elif role == "first_team_manager":
        tactics = int(staff_member.get("tactical_flexibility") or (rating // 5))
        morale_boost = 2 if tactics >= 18 else (1 if tactics >= 14 else 0)
        impact["tactical_synergy_boost"] = tactics
        impact["morale_boost"] = morale_boost
        impact["summary"] = f"Manager tactical flexibility ({tactics}/20) applied to selection."
    elif role == "head_of_youth_development":
        youth = int(staff_member.get("youth_development") or (rating // 5))
        potential_reveal_pct = min(100, 50 + youth * 2.5)
        impact["potential_reveal_accuracy"] = potential_reveal_pct
        impact["summary"] = f"HoYD youth scouting accuracy at {potential_reveal_pct}%."
    elif role == "chief_scout":
        scouting = int(staff_member.get("scouting_accuracy") or (rating // 5))
        impact["scouting_accuracy_score"] = scouting
        impact["summary"] = f"Scout accuracy rating {scouting}/20."
    elif role == "medical_director":
        medical = int(staff_member.get("medical_expertise") or (rating // 5))
        recovery_pct = min(40, medical * 2)
        impact["medical_recovery_pct"] = recovery_pct
        impact["summary"] = (
            f"Medical Director expertise ({medical}/20) provides {recovery_pct}% accelerated rehabilitation."
        )
    else:
        impact["summary"] = f"Staff competence rating {rating}/100 evaluated."

    return impact


# ==============================================================================
# 4. Delegated Decisions Lifecycle & Approval Workflow
# ==============================================================================


def propose_delegated_decision(
    session: Session,
    club_id: str,
    activity_key: str,
    proposed_by_role: str,
    title: str,
    summary: str,
    financial_amount_gtex: float | Decimal | None = None,
    payload: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> ClubDelegatedDecision:
    """
    Submits a club decision for delegated execution.
    If within delegated limits, auto-executes/auto-approves.
    If outside limits or policy mandates signoff, escalates to owner inbox for approval.

    Security & Invariants:
    - Verifies authoritative ownership; role spoofing or cross-owner submission rejected with 403.
    - Financial decisions recorded here do NOT mutate financial balances directly.
    - Decisions are append-only.
    """
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if state is None:
        raise DelegationError("Club state not found.", 404, code="club_not_found")

    if user_id is not None and user_id != state.owner_user_id:
        if proposed_by_role == "owner":
            raise DelegationError(
                "Role spoofing detected: Non-owner cannot propose decisions with owner role.",
                403,
                code="role_spoofing_forbidden",
            )
        raise DelegationError(
            "Forbidden: You do not own this club and cannot submit delegated decisions.",
            403,
            code="not_club_owner",
        )

    eval_result = evaluate_action_authority(
        session,
        club_id,
        user_id or state.owner_user_id,
        activity_key,
        financial_amount_gtex=financial_amount_gtex,
        proposed_by_role=proposed_by_role,
    )

    domain = ACTIVITY_DOMAINS.get(activity_key, "sporting")
    staff_name = eval_result.staff_name or ROLE_LABELS.get(proposed_by_role, proposed_by_role)
    amount_dec = Decimal(str(financial_amount_gtex)) if financial_amount_gtex is not None else None

    # Determine status
    if not eval_result.requires_approval and eval_result.allowed:
        status = "auto_approved"
        outcome_text = f"Authorized autonomously by {staff_name} under delegated {eval_result.authority_level} authority. Pending execution by authoritative domain service."
    else:
        status = "pending_approval"
        outcome_text = None

    decision = ClubDelegatedDecision(
        club_id=club_id,
        owner_user_id=state.owner_user_id,
        activity_key=activity_key,
        domain=domain,
        proposed_by_role=proposed_by_role,
        proposed_by_staff_name=staff_name,
        title=title,
        summary=summary,
        financial_amount_gtex=amount_dec,
        requires_owner_approval=eval_result.requires_approval,
        approval_reason=eval_result.reason if eval_result.requires_approval else None,
        status=status,
        execution_status="pending_execution",
        decided_by_user_id=state.owner_user_id if status == "auto_approved" else None,
        outcome_text=outcome_text,
        payload_json=payload or {},
        staff_competence_rating=eval_result.staff_competence_rating,
        staff_impact_json=eval_result.staff_impact,
    )
    session.add(decision)
    session.flush()

    # Append immutable audit log record for proposal
    audit_entry = ClubDelegatedDecisionAuditLog(
        decision_id=decision.id,
        club_id=club_id,
        actor_id=user_id or state.owner_user_id,
        action="proposed" if status == "pending_approval" else "auto_authorized",
        previous_status=None,
        new_status=status,
        decision_note=None,
        snapshot_json={
            "activity_key": activity_key,
            "domain": domain,
            "proposed_by_role": proposed_by_role,
            "proposed_by_staff_name": staff_name,
            "title": title,
            "financial_amount_gtex": float(financial_amount_gtex or 0),
            "requires_owner_approval": eval_result.requires_approval,
            "execution_status": "pending_execution",
            "staff_competence_rating": eval_result.staff_competence_rating,
            "staff_impact": eval_result.staff_impact,
        },
    )
    session.add(audit_entry)

    # If pending approval, push an actionable notification into the Owner's Inbox
    if status == "pending_approval":
        inbox_item = OwnerInboxItem(
            user_id=state.owner_user_id,
            club_id=club_id,
            kind="delegated_decision_request",
            priority="urgent" if (financial_amount_gtex or 0) > 25000 else "normal",
            sender=staff_name,
            title=f"Approval Required: {title}",
            what=summary,
            why=eval_result.reason,
            body=f"{staff_name} ({ROLE_LABELS.get(proposed_by_role, proposed_by_role)}) has prepared an action requiring your executive authorization.",
            category="requests",
            is_decision=True,
            actions_json=[
                {"id": "approve", "label": "Approve Decision", "variant": "primary"},
                {"id": "reject", "label": "Reject Decision", "variant": "danger"},
                {"id": "override", "label": "Owner Override", "variant": "secondary"},
            ],
            payload_json={
                "delegated_decision_id": decision.id,
                "activity_key": activity_key,
                "financial_amount_gtex": float(financial_amount_gtex or 0),
                "proposed_by_role": proposed_by_role,
            },
        )
        session.add(inbox_item)

    # Publish Ecosystem Event
    event_name = "delegation.decision_auto_approved" if status == "auto_approved" else "delegation.decision_proposed"
    _publish_governance_event(
        session,
        club_id,
        state.owner_user_id,
        event_name,
        {
            "decision_id": decision.id,
            "activity_key": activity_key,
            "title": title,
            "status": status,
            "amount_gtex": float(financial_amount_gtex or 0),
        },
    )

    session.commit()
    session.refresh(decision)
    return decision


def resolve_delegated_decision(
    session: Session,
    club_id: str,
    owner_user_id: str,
    decision_id: str,
    action: str,  # "approve" | "reject" | "override"
    decision_note: str | None = None,
) -> ClubDelegatedDecision:
    """Owner authorizes, rejects, or overrides a pending delegated decision."""
    _require_club_owner(session, club_id, owner_user_id)

    stmt = select(ClubDelegatedDecision).where(ClubDelegatedDecision.id == decision_id)
    if session.bind and session.bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    decision = session.scalar(stmt)

    if decision is None or decision.club_id != club_id:
        raise DelegationError("Delegated decision not found.", 404, code="decision_not_found")
    if decision.owner_user_id != owner_user_id:
        raise DelegationError(
            "Unauthorized: Only the club owner may resolve delegated decisions.", 403, code="not_club_owner"
        )
    if decision.status not in {"pending_approval", "escalated"}:
        raise DelegationError(
            f"Conflict: Decision is already resolved with status '{decision.status}'.",
            409,
            code="decision_already_resolved",
        )
    previous_status = decision.status

    action = action.lower().strip()
    if action not in {"approve", "reject", "override"}:
        raise DelegationError("Action must be 'approve', 'reject', or 'override'.", 400)

    now = utcnow()
    if action == "approve":
        decision.status = "approved"
        decision.outcome_text = f"Authorized by club owner on {now.strftime('%Y-%m-%d %H:%M UTC')}. Pending execution by authoritative domain service."
    elif action == "reject":
        decision.status = "rejected"
        decision.outcome_text = f"Proposal rejected by club owner: {decision_note or 'Owner declined authorization.'}"
    else:
        decision.status = "overridden"
        decision.outcome_text = (
            f"Proposal overridden by club owner: {decision_note or 'Owner substituted executive direction.'}"
        )

    decision.decided_by_user_id = owner_user_id
    decision.decision_note = decision_note
    decision.resolved_at = now

    # Append immutable audit log record for resolution
    audit_entry = ClubDelegatedDecisionAuditLog(
        decision_id=decision.id,
        club_id=club_id,
        actor_id=owner_user_id,
        action=f"resolved_{action}",
        previous_status=previous_status,
        new_status=decision.status,
        decision_note=decision_note,
        snapshot_json={
            "resolution_action": action,
            "decision_note": decision_note,
            "outcome_text": decision.outcome_text,
            "resolved_at": now.isoformat(),
            "execution_status": decision.execution_status,
        },
    )
    session.add(audit_entry)

    # Also resolve any matching OwnerInboxItem
    inbox_items = session.scalars(
        select(OwnerInboxItem).where(
            OwnerInboxItem.club_id == club_id,
            OwnerInboxItem.is_decision.is_(True),
            OwnerInboxItem.status == "open",
        )
    ).all()
    for item in inbox_items:
        payload = item.payload_json or {}
        if payload.get("delegated_decision_id") == decision_id:
            item.status = "resolved"
            item.resolution = action
            item.outcome_text = decision.outcome_text
            item.resolved_at = now

    _publish_governance_event(
        session,
        club_id,
        owner_user_id,
        f"delegation.decision_{decision.status}",
        {
            "decision_id": decision.id,
            "activity_key": decision.activity_key,
            "status": decision.status,
            "decision_note": decision_note,
        },
    )

    session.commit()
    session.refresh(decision)
    return decision


def get_club_decision_history(
    session: Session,
    club_id: str,
    owner_user_id: str,
    status_filter: str | None = None,
    domain_filter: str | None = None,
    limit: int = 50,
) -> list[ClubDelegatedDecision]:
    """Returns the decision audit log for the club."""
    _require_club_owner(session, club_id, owner_user_id)
    stmt = (
        select(ClubDelegatedDecision)
        .where(
            ClubDelegatedDecision.club_id == club_id,
            ClubDelegatedDecision.owner_user_id == owner_user_id,
        )
        .order_by(ClubDelegatedDecision.created_at.desc())
        .limit(min(100, max(1, limit)))
    )
    if status_filter:
        stmt = stmt.where(ClubDelegatedDecision.status == status_filter)
    if domain_filter:
        stmt = stmt.where(ClubDelegatedDecision.domain == domain_filter)

    return list(session.scalars(stmt).all())


def get_pending_escalations(session: Session, club_id: str, owner_user_id: str) -> list[ClubDelegatedDecision]:
    """Returns all decisions currently awaiting owner signoff."""
    _require_club_owner(session, club_id, owner_user_id)
    return list(
        session.scalars(
            select(ClubDelegatedDecision)
            .where(
                ClubDelegatedDecision.club_id == club_id,
                ClubDelegatedDecision.owner_user_id == owner_user_id,
                ClubDelegatedDecision.status == "pending_approval",
            )
            .order_by(ClubDelegatedDecision.created_at.desc())
        ).all()
    )


def get_decision_audit_trail(
    session: Session,
    club_id: str,
    owner_user_id: str,
    decision_id: str,
) -> list[ClubDelegatedDecisionAuditLog]:
    """Returns the immutable append-only audit trail for a specific decision."""
    _require_club_owner(session, club_id, owner_user_id)
    return list(
        session.scalars(
            select(ClubDelegatedDecisionAuditLog)
            .where(
                ClubDelegatedDecisionAuditLog.club_id == club_id,
                ClubDelegatedDecisionAuditLog.decision_id == decision_id,
            )
            .order_by(ClubDelegatedDecisionAuditLog.created_at.asc())
        ).all()
    )


def mark_decision_executed(
    session: Session,
    club_id: str,
    decision_id: str,
    transaction_id: str,
    executor_user_id: str,
) -> ClubDelegatedDecision:
    """Authoritative domain service records that an authorized decision has been financially executed."""
    decision = session.get(ClubDelegatedDecision, decision_id)
    if decision is None or decision.club_id != club_id:
        raise DelegationError("Delegated decision not found.", 404, code="decision_not_found")
    if decision.status not in {"approved", "auto_approved"}:
        raise DelegationError(
            f"Cannot execute decision with authorization status '{decision.status}'. Must be approved or auto_approved.",
            400,
            code="decision_not_authorized",
        )
    if decision.execution_status == "executed":
        raise DelegationError("Decision has already been executed.", 409, code="decision_already_executed")

    decision.execution_status = "executed"
    decision.outcome_text = f"Executed by authoritative domain service (Transaction: {transaction_id})."

    audit_entry = ClubDelegatedDecisionAuditLog(
        decision_id=decision.id,
        club_id=club_id,
        actor_id=executor_user_id,
        action="executed",
        previous_status=decision.status,
        new_status=decision.status,
        decision_note=f"Authoritative execution confirmed (tx: {transaction_id}).",
        snapshot_json={
            "transaction_id": transaction_id,
            "execution_status": "executed",
            "executed_at": utcnow().isoformat(),
        },
    )
    session.add(audit_entry)

    _publish_governance_event(
        session,
        club_id,
        decision.owner_user_id,
        "delegation.decision_executed",
        {
            "decision_id": decision.id,
            "activity_key": decision.activity_key,
            "transaction_id": transaction_id,
            "status": decision.status,
            "execution_status": "executed",
        },
    )
    session.commit()
    session.refresh(decision)
    return decision


def get_club_org_structure(session: Session, club_id: str, owner_user_id: str) -> dict[str, Any]:
    """Constructs the comprehensive organizational structure, appointed staff, and authority roles."""
    state = _require_club_owner(session, club_id, owner_user_id)
    policy = get_or_create_delegation_policy(session, club_id, owner_user_id)
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})

    # Organization roles
    staff_positions = []
    for role_key, role_title in ROLE_LABELS.items():
        if role_key == "owner":
            staff_positions.append(
                {
                    "role_key": "owner",
                    "title": "Club Owner & Chairman",
                    "appointee_name": state.club_name + " Executive Ownership",
                    "rating": 100,
                    "is_appointed": True,
                    "can_fire": False,
                }
            )
            continue

        staff_data = exec_staff.get(role_key)
        if staff_data:
            staff_positions.append(
                {
                    "role_key": role_key,
                    "title": role_title,
                    "appointee_name": staff_data.get("name"),
                    "staff_id": staff_data.get("id") or staff_data.get("staff_id"),
                    "rating": int(staff_data.get("rating") or 65),
                    "temperament": staff_data.get("temperament"),
                    "specialty": staff_data.get("specialty"),
                    "salary_gtex": float(staff_data.get("salary_gtex") or 0.0),
                    "is_appointed": True,
                    "can_fire": True,
                }
            )
        else:
            staff_positions.append(
                {
                    "role_key": role_key,
                    "title": role_title,
                    "appointee_name": f"Vacant ({role_title})",
                    "rating": 50,
                    "is_appointed": False,
                    "can_fire": False,
                }
            )

    return {
        "club_id": club_id,
        "club_name": state.club_name,
        "mode": policy.mode,
        "is_suspended": policy.is_suspended,
        "staff_positions": staff_positions,
        "financial_thresholds": policy.financial_thresholds_json,
        "activity_assignments": policy.activity_assignments_json,
        "reserved_decisions": policy.reserved_decisions_json,
        "temporary_overrides": policy.temporary_overrides_json,
    }


# ==============================================================================
# 5. Ecosystem Event Bus Helper
# ==============================================================================


def _publish_governance_event(
    session: Session,
    club_id: str,
    owner_user_id: str,
    event_name: str,
    payload: dict[str, Any],
    priority: EcosystemEventPriority = EcosystemEventPriority.NORMAL,
) -> None:
    """Emits canonical ecosystem events on the GTEX transactional event backbone."""
    gtex_ecosystem_bus.publish(
        session,
        EcosystemEvent(
            domain=EcosystemDomain.OWNER_GOVERNANCE,
            name=event_name,
            payload=payload,
            actor=EcosystemActor(actor_id=owner_user_id, roles=("owner",)),
            subject=EcosystemSubject(subject_id=club_id, subject_type="club_delegation"),
            priority=priority,
        ),
    )
