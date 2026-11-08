"""GTEX Living Football World — Stage 5
General Manager Delegation & Owner Control Engine.

Provides:
- 3 Authoritative Owner Delegation Modes:
    * `owner_managed`: Owner micromanages key operational & sporting decisions.
    * `balanced`: Premier League style hierarchy. GM operates within thresholds.
    * `gm_led`: Empowered Continental GM model with broad recruitment authority.
- 12 Canonical Delegation Matrix Activities & Financial Controls.
- GM Autonomy & Accountability:
    * Autonomous proposal generation & execution within policy.
    * Automatic escalation to owner when limits are exceeded.
    * Dynamic bilateral relationship impact (trust, tension, alignment) upon approval/rejection.
    * Financial ledger settlement integration.
"""

from __future__ import annotations

import logging
import math
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.owner_console import delegation_service, ledger, living_staff_market
from app.owner_console.delegation_service import DelegationError
from app.owner_console.models import (
    ClubDelegatedDecision,
    ClubDelegatedDecisionAuditLog,
    OwnerClubRelationship,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerInboxItem,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. Canonical Stage 5 Taxonomy & Activity Matrix Mapping
# ==============================================================================

STAGE5_DELEGATION_MODES = ("owner_managed", "balanced", "gm_led", "hands_on", "delegating", "custom")

STAGE5_MODE_ALIASES: dict[str, str] = {
    "owner_managed": "hands_on",
    "gm_led": "delegating",
    "hands_on": "hands_on",
    "delegating": "delegating",
    "balanced": "balanced",
    "custom": "custom",
}

STAGE5_REVERSE_MODE_ALIASES: dict[str, str] = {
    "hands_on": "owner_managed",
    "delegating": "gm_led",
    "balanced": "balanced",
    "custom": "custom",
}

STAGE5_ACTIVITIES: list[dict[str, Any]] = [
    {
        "activity_key": "staff_hiring",
        "label": "Staff Recruitment & Appointments",
        "domain": "club_operations",
        "description": "Scouting, negotiating contracts, and appointing departmental staff.",
        "financial_control_key": "max_staff_salary_unapproved_gtex",
    },
    {
        "activity_key": "staff_dismissal",
        "label": "Staff Contract Terminations",
        "domain": "club_operations",
        "description": "Dismissing staff to free agency and disbursing severance compensation.",
        "financial_control_key": "max_expenditure_unapproved_gtex",
    },
    {
        "activity_key": "staff_contract_renewal",
        "label": "Staff Contract Extensions",
        "domain": "club_operations",
        "description": "Extending existing technical & executive staff contracts.",
        "financial_control_key": "max_staff_salary_unapproved_gtex",
    },
    {
        "activity_key": "staff_salary_negotiation",
        "label": "Staff Salary Negotiations",
        "domain": "club_operations",
        "description": "Negotiating compensation packages and marquee wage premiums.",
        "financial_control_key": "max_staff_salary_unapproved_gtex",
    },
    {
        "activity_key": "player_scouting",
        "label": "Player Scouting Missions",
        "domain": "sporting",
        "description": "Deploying scouts across domestic & continental territories.",
        "financial_control_key": "recruitment_budget_gtex",
    },
    {
        "activity_key": "player_recruitment",
        "label": "Player Recruitment & Ingestion",
        "domain": "sporting",
        "description": "Signing new professional players to the first team squad.",
        "financial_control_key": "recruitment_budget_gtex",
    },
    {
        "activity_key": "player_transfer_negotiation",
        "label": "Transfer Fee Negotiations",
        "domain": "sporting",
        "description": "Bilateral acquisition fee negotiation with counterparty clubs.",
        "financial_control_key": "recruitment_budget_gtex",
    },
    {
        "activity_key": "player_sales",
        "label": "Player Sales & Divestments",
        "domain": "sporting",
        "description": "Evaluating outbound offers and sanctioning squad player transfers.",
        "financial_control_key": "min_sale_value_gtex",
    },
    {
        "activity_key": "contract_renewal_recommendations",
        "label": "Squad Contract Renewal Recommendations",
        "domain": "sporting",
        "description": "Auditing player contracts and advising on extension priorities.",
        "financial_control_key": "wage_budget_gtex",
    },
    {
        "activity_key": "academy_recruitment",
        "label": "Youth Academy Intake",
        "domain": "sporting",
        "description": "Recruiting trialists and signing academy scholars.",
        "financial_control_key": "max_expenditure_unapproved_gtex",
    },
    {
        "activity_key": "department_spending",
        "label": "Department Operational Expenditure",
        "domain": "club_operations",
        "description": "Disbursing operational budgets for sports science, medical, and analytics.",
        "financial_control_key": "max_expenditure_unapproved_gtex",
    },
    {
        "activity_key": "recruitment_budget_allocation",
        "label": "Recruitment Budget Allocation",
        "domain": "club_operations",
        "description": "Allocating seasonal capital reserves to scouting and acquisitions.",
        "financial_control_key": "recruitment_budget_gtex",
    },
]

STAGE5_EXECUTABLE_ACTIVITIES = frozenset({"staff_hiring", "academy_recruitment"})
STAGE5_ACTIVITY_KEYS = frozenset(item["activity_key"] for item in STAGE5_ACTIVITIES)
STAGE5_AUTHORITY_LEVELS = frozenset({"owner_only", "delegated_with_limits", "full_autonomy"})
STAGE5_RESPONSIBLE_ROLES = frozenset({"owner", "general_manager"})


DEFAULT_STAGE5_FINANCIAL_THRESHOLDS: dict[str, dict[str, float]] = {
    "owner_managed": {
        "max_expenditure_unapproved_gtex": 0.0,
        "max_staff_salary_unapproved_gtex": 0.0,
        "max_contract_years_unapproved": 0.0,
        "recruitment_budget_gtex": 0.0,
        "wage_budget_gtex": 0.0,
        "min_sale_value_gtex": 0.0,
        "allow_emergency_spending": 0.0,
        # Backward compatibility aliases
        "recruitment_max_gtex": 0.0,
        "operational_spend_max_gtex": 0.0,
        "sales_min_gtex": 0.0,
        "contract_renewal_max_weekly_wage_gtex": 0.0,
        "facility_spend_max_gtex": 0.0,
    },
    "balanced": {
        "max_expenditure_unapproved_gtex": 10000.0,
        "max_staff_salary_unapproved_gtex": 1500.0,
        "max_contract_years_unapproved": 2.0,
        "recruitment_budget_gtex": 35000.0,
        "wage_budget_gtex": 8000.0,
        "min_sale_value_gtex": 5000.0,
        "allow_emergency_spending": 0.0,
        # Backward compatibility aliases
        "recruitment_max_gtex": 25000.0,
        "operational_spend_max_gtex": 10000.0,
        "sales_min_gtex": 5000.0,
        "contract_renewal_max_weekly_wage_gtex": 5000.0,
        "facility_spend_max_gtex": 15000.0,
    },
    "gm_led": {
        "max_expenditure_unapproved_gtex": 50000.0,
        "max_staff_salary_unapproved_gtex": 3500.0,
        "max_contract_years_unapproved": 4.0,
        "recruitment_budget_gtex": 120000.0,
        "wage_budget_gtex": 25000.0,
        "min_sale_value_gtex": 25000.0,
        "allow_emergency_spending": 1.0,
        # Backward compatibility aliases
        "recruitment_max_gtex": 100000.0,
        "operational_spend_max_gtex": 50000.0,
        "sales_min_gtex": 25000.0,
        "contract_renewal_max_weekly_wage_gtex": 20000.0,
        "facility_spend_max_gtex": 75000.0,
    },
}

# Alias mapping for base delegation service
DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["hands_on"] = DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["owner_managed"]
DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["delegating"] = DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["gm_led"]


def _get_gm_relationship(session: Session, club_id: str) -> OwnerClubRelationship | None:
    """Finds or returns the bilateral relationship for the General Manager."""
    stmt = select(OwnerClubRelationship).where(
        OwnerClubRelationship.club_id == club_id,
        OwnerClubRelationship.pairing_key.like("%general_manager%"),
    )
    return session.scalars(stmt).first()


def _apply_gm_relationship_delta(
    session: Session,
    club_id: str,
    reason: str,
    delta_trust: int = 0,
    delta_tension: int = 0,
    delta_alignment: int = 0,
    delta_loyalty: int = 0,
    delta_influence: int = 0,
) -> None:
    """Modifies bilateral GM relationship metrics and appends an audit history entry."""
    rel = _get_gm_relationship(session, club_id)
    if not rel:
        return

    rel.trust = max(0, min(100, rel.trust + delta_trust))
    rel.tension = max(0, min(100, rel.tension + delta_tension))
    rel.alignment = max(0, min(100, rel.alignment + delta_alignment))
    rel.loyalty = max(0, min(100, rel.loyalty + delta_loyalty))
    rel.influence = max(0, min(100, rel.influence + delta_influence))

    hist = OwnerClubRelationshipHistory(
        relationship_id=rel.id,
        club_id=club_id,
        world_day=1,
        reason=reason,
        delta_trust=delta_trust,
        delta_tension=delta_tension,
        delta_alignment=delta_alignment,
        delta_loyalty=delta_loyalty,
        delta_influence=delta_influence,
        snapshot_json={
            "trust": rel.trust,
            "tension": rel.tension,
            "alignment": rel.alignment,
            "loyalty": rel.loyalty,
            "influence": rel.influence,
        },
    )
    session.add(hist)
    session.flush()


# ==============================================================================
# 2. GM Delegation Overview & Policy Management
# ==============================================================================


def get_gm_delegation_overview(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    """Returns the comprehensive GM Delegation state, financial limits, matrix, and proposals."""
    policy = delegation_service.get_or_create_delegation_policy(session, club_id, user_id)
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if not state:
        raise DelegationError("Club state not found", 404)

    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    gm_profile = exec_staff.get("general_manager") or {
        "name": "Dayo Adeleke",
        "role": "General Manager",
        "rating": 82,
        "temperament": "Methodical",
        "style": "Fiscal Discipline",
    }

    rel = _get_gm_relationship(session, club_id)
    rel_summary = {
        "trust": rel.trust if rel else 60,
        "tension": rel.tension if rel else 20,
        "alignment": rel.alignment if rel else 65,
        "loyalty": rel.loyalty if rel else 70,
        "influence": rel.influence if rel else 60,
        "status": rel.status if rel else "active",
    }

    # Normalize mode for Stage 5 display
    canonical_mode = STAGE5_REVERSE_MODE_ALIASES.get(policy.mode, policy.mode)

    # Activity assignments merged with Stage 5 canonical definitions
    raw_assignments = dict(policy.activity_assignments_json or {})
    activity_matrix: list[dict[str, Any]] = []

    for item in STAGE5_ACTIVITIES:
        k = item["activity_key"]
        rule = raw_assignments.get(k) or raw_assignments.get("operational_expenditure") or {}
        is_execution_supported = k in STAGE5_EXECUTABLE_ACTIVITIES
        authority_level = rule.get(
            "authority_level", "delegated_with_limits" if canonical_mode != "owner_managed" else "owner_only"
        )
        requires_approval = rule.get("requires_owner_approval", canonical_mode == "owner_managed")
        responsible_role = rule.get(
            "responsible_role", "general_manager" if canonical_mode != "owner_managed" else "owner"
        )

        # The matrix must never advertise autonomous authority for a workflow that
        # does not yet have an authoritative execution handler.
        if not is_execution_supported or canonical_mode == "owner_managed":
            authority_level = "owner_only"
            requires_approval = True
            responsible_role = "owner"

        activity_matrix.append(
            {
                "activity_key": k,
                "label": item["label"],
                "domain": item["domain"],
                "description": (
                    item["description"]
                    if is_execution_supported
                    else f"{item['description']} GM execution is not available for this activity yet."
                ),
                "responsible_role": responsible_role,
                "authority_level": authority_level,
                "requires_owner_approval": requires_approval,
                "financial_control_key": item["financial_control_key"],
                "execution_supported": is_execution_supported,
            }
        )

    # Financial thresholds merged with Stage 5 defaults
    raw_thresholds = dict(policy.financial_thresholds_json or {})
    base_defaults = DEFAULT_STAGE5_FINANCIAL_THRESHOLDS.get(
        canonical_mode, DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["balanced"]
    )
    financial_controls = {**base_defaults, **raw_thresholds}

    # Fetch pending GM proposals
    proposals_stmt = (
        select(ClubDelegatedDecision)
        .where(
            ClubDelegatedDecision.club_id == club_id,
            ClubDelegatedDecision.proposed_by_role == "general_manager",
        )
        .order_by(ClubDelegatedDecision.created_at.desc())
        .limit(30)
    )
    decision_rows = session.scalars(proposals_stmt).all()

    pending_proposals: list[dict[str, Any]] = []
    historical_decisions: list[dict[str, Any]] = []

    for d in decision_rows:
        item = {
            "id": d.id,
            "activity_key": d.activity_key,
            "domain": d.domain,
            "proposed_by_role": d.proposed_by_role,
            "proposed_by_staff_name": d.proposed_by_staff_name,
            "title": d.title,
            "summary": d.summary,
            "financial_amount_gtex": float(d.financial_amount_gtex) if d.financial_amount_gtex is not None else 0.0,
            "requires_owner_approval": d.requires_owner_approval,
            "status": d.status,
            "execution_status": d.execution_status,
            "approval_reason": d.approval_reason,
            "decision_note": d.decision_note,
            "outcome_text": d.outcome_text,
            "payload": d.payload_json,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
        }
        if d.status == "pending_approval":
            pending_proposals.append(item)
        else:
            historical_decisions.append(item)

    activities = [
        {
            "activity_key": item["activity_key"],
            "label": item["label"],
            "description": item["description"],
            "category": item["domain"],
            "department": item["domain"],
            "requires_owner_approval": item["requires_owner_approval"],
            "gm_can_execute": (
                item["execution_supported"]
                and canonical_mode != "owner_managed"
                and not item["requires_owner_approval"]
                and item["authority_level"] != "owner_only"
                and not policy.is_suspended
            ),
            "execution_supported": item["execution_supported"],
            "policy_suspended": bool(policy.is_suspended),
            "expenditure_limit_gtex": float(
                financial_controls.get(item["financial_control_key"], 0) or 0
            ),
            "delegation_level": item["authority_level"],
        }
        for item in activity_matrix
    ]

    audit_rows = session.scalars(
        select(ClubDelegatedDecisionAuditLog)
        .where(ClubDelegatedDecisionAuditLog.club_id == club_id)
        .order_by(ClubDelegatedDecisionAuditLog.created_at.desc())
        .limit(30)
    ).all()
    recent_audit_trail = [
        {
            "id": row.id,
            "decision_id": row.decision_id,
            "actor_role": (
                "general_manager" if row.action.startswith("gm_") else "owner"
            ),
            "action": (
                "approved" if row.action == "owner_approve"
                else "rejected" if row.action == "owner_reject"
                else "executed" if row.action == "gm_execute"
                else row.action
            ),
            "reason": (row.snapshot_json or {}).get("outcome") or row.new_status,
            "note": row.decision_note,
            "occurred_at": row.created_at.isoformat() if row.created_at else "",
        }
        for row in audit_rows
    ]

    executed_rows = [d for d in decision_rows if d.execution_status == "executed"]
    total_expenditure_approved = sum(
        float(d.financial_amount_gtex or 0) for d in executed_rows
    )
    gm_staff = {
        "id": str(gm_profile.get("id") or gm_profile.get("staff_id") or ""),
        "name": gm_profile.get("name", "Dayo Adeleke"),
        "role": gm_profile.get("role", "General Manager"),
        "rating": int(gm_profile.get("rating") or 0),
        "salary_gtex": float(gm_profile.get("salary_gtex") or gm_profile.get("salary") or 0),
        "trust": rel_summary["trust"],
        "tension": rel_summary["tension"],
        "alignment": rel_summary["alignment"],
        "loyalty": rel_summary["loyalty"],
        "is_appointed": bool(exec_staff.get("general_manager")),
    }

    return {
        "club_id": club_id,
        "mode": canonical_mode,
        "is_suspended": policy.is_suspended,
        "suspension_reason": policy.suspension_reason,
        "general_manager": gm_profile,
        "relationship": rel_summary,
        "financial_controls": financial_controls,
        "activity_matrix": activity_matrix,
        "pending_proposals_count": len(pending_proposals),
        "pending_proposals": pending_proposals,
        "historical_decisions": historical_decisions[:10],
        # React Stage 5 contract aliases. Keep the original keys for existing consumers.
        "gm_staff": gm_staff,
        "delegation_mode": canonical_mode,
        "canonical_mode": canonical_mode,
        "activities": activities,
        "recent_audit_trail": recent_audit_trail,
        "statistics": {
            "total_executed": len(executed_rows),
            "pending_approval_count": len(pending_proposals),
            "total_expenditure_approved_gtex": total_expenditure_approved,
        },
    }


def update_gm_delegation_mode(session: Session, user_id: str, club_id: str, mode: str) -> dict[str, Any]:
    """Updates the overarching delegation mode and triggers bilateral GM relationship impacts."""
    if mode not in STAGE5_DELEGATION_MODES:
        raise DelegationError(f"Invalid mode '{mode}'. Must be one of {STAGE5_DELEGATION_MODES}", 400)

    internal_mode = STAGE5_MODE_ALIASES.get(mode, mode)
    canonical_stage5_mode = STAGE5_REVERSE_MODE_ALIASES.get(internal_mode, internal_mode)

    policy = delegation_service.set_management_configuration(session, club_id, user_id, internal_mode)

    # Sync Stage 5 defaults into thresholds
    defaults = DEFAULT_STAGE5_FINANCIAL_THRESHOLDS.get(
        canonical_stage5_mode, DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["balanced"]
    )
    current_th = dict(policy.financial_thresholds_json or {})
    current_th.update(defaults)
    policy.financial_thresholds_json = current_th
    session.commit()

    # Bilateral relationship feedback based on owner trust
    if canonical_stage5_mode == "gm_led":
        _apply_gm_relationship_delta(
            session,
            club_id,
            reason="Delegation mode elevated to GM-Led Management",
            delta_trust=6,
            delta_tension=-5,
            delta_alignment=5,
            delta_loyalty=5,
            delta_influence=8,
        )
    elif canonical_stage5_mode == "owner_managed":
        _apply_gm_relationship_delta(
            session,
            club_id,
            reason="Owner instituted strict hands-on oversight mode",
            delta_trust=-3,
            delta_tension=6,
            delta_alignment=-3,
            delta_loyalty=-2,
            delta_influence=-8,
        )
    else:
        _apply_gm_relationship_delta(
            session,
            club_id,
            reason="Delegation mode set to Balanced standard hierarchy",
            delta_trust=2,
            delta_tension=-2,
            delta_alignment=3,
        )

    return get_gm_delegation_overview(session, user_id, club_id)


def update_gm_matrix_and_financial_controls(
    session: Session,
    user_id: str,
    club_id: str,
    financial_controls: dict[str, Any] | None = None,
    activity_assignments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Updates granular activity permissions and financial authorization limits."""
    policy = delegation_service.get_or_create_delegation_policy(session, club_id, user_id)

    current_th = dict(policy.financial_thresholds_json or {})
    current_act = dict(policy.activity_assignments_json or {})

    if financial_controls is not None:
        allowed_controls = set(DEFAULT_STAGE5_FINANCIAL_THRESHOLDS["balanced"])
        for key, value in financial_controls.items():
            if key not in allowed_controls:
                raise DelegationError(f"Unknown financial control: {key}", 400)
            if key == "allow_emergency_spending":
                if isinstance(value, bool):
                    current_th[key] = 1.0 if value else 0.0
                elif (
                    isinstance(value, (int, float))
                    and math.isfinite(float(value))
                    and float(value) in (0.0, 1.0)
                ):
                    current_th[key] = float(value)
                else:
                    raise DelegationError("allow_emergency_spending must be a boolean.", 400)
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
            ):
                raise DelegationError(f"{key} must be a finite, non-negative number.", 400)
            current_th[key] = float(value)

    if activity_assignments is not None:
        for key, value in activity_assignments.items():
            if key not in STAGE5_ACTIVITY_KEYS:
                raise DelegationError(f"Unknown Stage 5 activity: {key}", 400)
            if not isinstance(value, dict):
                raise DelegationError(f"Activity assignment for {key} must be an object.", 400)

            is_supported = key in STAGE5_EXECUTABLE_ACTIVITIES
            canonical_mode = STAGE5_REVERSE_MODE_ALIASES.get(policy.mode, policy.mode)
            current = dict(current_act.get(key) or {})
            responsible_role = value.get("responsible_role", current.get("responsible_role", "general_manager"))
            authority_level = value.get(
                "authority_level", current.get("authority_level", "delegated_with_limits")
            )
            requires_approval = value.get(
                "requires_owner_approval", current.get("requires_owner_approval", False)
            )

            if responsible_role not in STAGE5_RESPONSIBLE_ROLES:
                raise DelegationError(f"Invalid responsible role for {key}.", 400)
            if authority_level not in STAGE5_AUTHORITY_LEVELS:
                raise DelegationError(f"Invalid authority level for {key}.", 400)
            if not isinstance(requires_approval, bool):
                raise DelegationError(f"requires_owner_approval for {key} must be boolean.", 400)
            if not is_supported and (
                responsible_role != "owner" or authority_level != "owner_only" or not requires_approval
            ):
                raise DelegationError(
                    f"{key} does not yet have a GM execution handler and must remain owner-controlled.",
                    409,
                )
            if is_supported and canonical_mode == "owner_managed" and (
                responsible_role != "owner" or authority_level != "owner_only" or not requires_approval
            ):
                raise DelegationError(
                    f"{key} cannot be delegated while the club is in owner-managed mode.",
                    409,
                )

            current_act[key] = {
                "activity_key": key,
                "responsible_role": responsible_role,
                "authority_level": authority_level,
                "requires_owner_approval": requires_approval,
            }

    policy.financial_thresholds_json = current_th
    policy.activity_assignments_json = current_act
    session.commit()
    return get_gm_delegation_overview(session, user_id, club_id)


# ==============================================================================
# 3. GM Autonomous Operations & Simulation Engine
# ==============================================================================


def evaluate_gm_operational_cycle(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    """Simulates an autonomous General Manager operational cycle.

    Evaluates:
    1. Vacant technical posts & scouting free agent market.
    2. Academy recruitment intake.
    3. Operational facility and sports science improvements.

    Enforces delegation policies:
    - If action is within authorized limits: GM executes autonomously, logs to audit trail, debits ledger.
    - If action requires approval or exceeds limits: GM drafts formal proposal for owner review.
    """
    policy = delegation_service.get_or_create_delegation_policy(session, club_id, user_id)
    canonical_mode = STAGE5_REVERSE_MODE_ALIASES.get(policy.mode, policy.mode)
    financial_controls = dict(policy.financial_thresholds_json or {})
    assignments = dict(policy.activity_assignments_json or {})

    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if not state:
        raise DelegationError("Club state not found", 404)

    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    gm_name = (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke")

    max_unapproved_spend = float(financial_controls.get("max_expenditure_unapproved_gtex", 10000.0))
    max_staff_salary = float(financial_controls.get("max_staff_salary_unapproved_gtex", 1500.0))

    executed_actions: list[dict[str, Any]] = []
    escalated_proposals: list[dict[str, Any]] = []
    blocked_actions: list[dict[str, Any]] = []

    # 1. Audit Vacancies
    vacancies_data = living_staff_market.get_club_vacancies(session, user_id, club_id)
    open_vacs = vacancies_data.get("vacancies", [])

    if open_vacs:
        target_vac = open_vacs[0]
        role_key = target_vac["role_key"]

        # Check market for free agents
        market_pool = living_staff_market.list_staff_market_candidates(
            session, user_id, club_id, role=role_key, employment_status="unemployed", limit=5
        )
        candidates = market_pool.get("candidates", [])

        if candidates:
            best_candidate = candidates[0]
            cand_salary = float(best_candidate["expected_salary_gtex"])
            rule = assignments.get("staff_hiring") or {}
            requires_approval = rule.get("requires_owner_approval", canonical_mode == "owner_managed")
            authority_level = rule.get("authority_level", "delegated_with_limits")
            contract_years = 2
            max_contract_years = float(financial_controls.get("max_contract_years_unapproved", 2.0))
            can_autonomously_hire = (
                not policy.is_suspended
                and canonical_mode != "owner_managed"
                and not requires_approval
                and authority_level != "owner_only"
                and cand_salary <= max_staff_salary
                and contract_years <= max_contract_years
            )

            if can_autonomously_hire:
                hire_res = living_staff_market.hire_staff_from_market(
                    session,
                    user_id,
                    club_id,
                    profile_id=best_candidate["profile_id"],
                    role=role_key,
                    offered_salary_gtex=int(cand_salary),
                    contract_years=contract_years,
                    pitch_note=f"Appointed autonomously by General Manager {gm_name} under {canonical_mode} delegation.",
                )

                if hire_res.get("success") is True:
                    decision = ClubDelegatedDecision(
                        club_id=club_id,
                        owner_user_id=user_id,
                        activity_key="staff_hiring",
                        domain="club_operations",
                        proposed_by_role="general_manager",
                        proposed_by_staff_name=gm_name,
                        title=f"Autonomously Appointed {best_candidate['name']} as {target_vac['role_label']}",
                        summary=f"GM {gm_name} resolved the vacancy by recruiting {best_candidate['name']} (OVR {best_candidate['rating']}).",
                        financial_amount_gtex=Decimal(str(cand_salary)),
                        requires_owner_approval=False,
                        status="executed",
                        execution_status="executed",
                        decided_by_user_id=user_id,
                        decision_note="Executed autonomously under authorized GM delegation limits.",
                        outcome_text="Contract ratified, ledger settlement completed, and staff appointment recorded.",
                        payload_json={
                            "profile_id": best_candidate["profile_id"],
                            "role": role_key,
                            "salary": cand_salary,
                            "contract_years": contract_years,
                        },
                    )
                    session.add(decision)
                    session.flush()
                    session.add(
                        ClubDelegatedDecisionAuditLog(
                            decision_id=decision.id,
                            club_id=club_id,
                            actor_id=user_id,
                            action="gm_execute",
                            previous_status=None,
                            new_status="executed",
                            decision_note=decision.decision_note,
                            snapshot_json={"payload": decision.payload_json, "outcome": decision.outcome_text},
                        )
                    )
                    executed_actions.append(
                        {
                            "type": "staff_hire",
                            "title": decision.title,
                            "details": hire_res.get("message"),
                        }
                    )
                else:
                    blocked_actions.append(
                        {
                            "type": "staff_hire",
                            "title": f"Appointment not completed: {best_candidate['name']}",
                            "reason": hire_res.get("reason") or "offer_not_accepted",
                            "details": hire_res.get("message") or "The staff-market service did not accept the offer.",
                        }
                    )
            elif policy.is_suspended:
                blocked_actions.append(
                    {
                        "type": "staff_hire",
                        "title": f"Appointment suspended: {best_candidate['name']}",
                        "reason": policy.suspension_reason or "Delegation policy is suspended.",
                    }
                )
            else:
                if cand_salary > max_staff_salary:
                    reason = "Exceeds authorized staff salary ceiling"
                elif contract_years > max_contract_years:
                    reason = "Exceeds authorized contract duration"
                else:
                    reason = "Policy mandates owner ratification"
                decision = ClubDelegatedDecision(
                    club_id=club_id,
                    owner_user_id=user_id,
                    activity_key="staff_hiring",
                    domain="club_operations",
                    proposed_by_role="general_manager",
                    proposed_by_staff_name=gm_name,
                    title=f"Contract Offer Recommendation: {best_candidate['name']} for {target_vac['role_label']}",
                    summary=(
                        f"GM {gm_name} identified {best_candidate['name']} (OVR {best_candidate['rating']}, "
                        f"expected salary {cand_salary:,.0f} GTEX). Escalated for owner ratification: {reason}."
                    ),
                    financial_amount_gtex=Decimal(str(cand_salary)),
                    requires_owner_approval=True,
                    approval_reason=reason,
                    status="pending_approval",
                    execution_status="pending_execution",
                    payload_json={
                        "profile_id": best_candidate["profile_id"],
                        "role": role_key,
                        "salary": cand_salary,
                        "contract_years": contract_years,
                    },
                )
                session.add(decision)
                session.flush()
                inbox = OwnerInboxItem(
                    club_id=club_id,
                    user_id=user_id,
                    kind="delegated_proposal",
                    category="governance",
                    priority="high",
                    sender=gm_name,
                    title=f"Delegated Action: {decision.title}",
                    what=decision.title,
                    why=reason,
                    body=decision.summary,
                    is_decision=True,
                    payload_json={"decision_id": decision.id},
                    actions_json=[
                        {"action": "approve", "label": "Approve"},
                        {"action": "reject", "label": "Reject"},
                    ],
                )
                session.add(inbox)
                escalated_proposals.append(
                    {
                        "decision_id": decision.id,
                        "title": decision.title,
                        "amount_gtex": cand_salary,
                        "reason": reason,
                    }
                )

    # 2. Academy Trial & Grassroots Intake
    academy_cost = 2500
    rule_acad = assignments.get("academy_recruitment") or {}
    acad_approval = rule_acad.get("requires_owner_approval", canonical_mode == "owner_managed")
    acad_authority = rule_acad.get("authority_level", "delegated_with_limits")
    can_autonomously_fund_academy = (
        not policy.is_suspended
        and canonical_mode != "owner_managed"
        and not acad_approval
        and acad_authority != "owner_only"
        and academy_cost <= max_unapproved_spend
    )

    if policy.is_suspended:
        blocked_actions.append(
            {
                "type": "academy_recruitment",
                "title": "Academy intake suspended",
                "reason": policy.suspension_reason or "Delegation policy is suspended.",
            }
        )
    elif can_autonomously_fund_academy:
        club_acct = ledger.club_account(club_id)
        try:
            # ledger.record checks the actual available balance by default.
            ledger.record(
                session,
                event_type="academy_scouting",
                source=club_acct,
                destination=ledger.WORLD_CLUBS,
                currency=ledger.GTEX,
                gross=academy_cost,
                club_id=club_id,
                user_id=user_id,
                memo=f"Autonomous academy scouting drive authorized by GM {gm_name}",
                check_funds=True,
            )
        except ledger.LedgerError as exc:
            blocked_actions.append(
                {
                    "type": "academy_recruitment",
                    "title": "Academy intake not funded",
                    "reason": str(exc),
                }
            )
        else:
            decision_acad = ClubDelegatedDecision(
                club_id=club_id,
                owner_user_id=user_id,
                activity_key="academy_recruitment",
                domain="sporting",
                proposed_by_role="general_manager",
                proposed_by_staff_name=gm_name,
                title="Grassroots Academy Showcase Ingestion",
                summary=f"GM {gm_name} sanctioned regional trial tournament for 25 high-potential grassroots scholars.",
                financial_amount_gtex=Decimal(str(academy_cost)),
                requires_owner_approval=False,
                status="executed",
                execution_status="executed",
                decided_by_user_id=user_id,
                decision_note="Executed autonomously under authorized GM delegation limits.",
                outcome_text="Trial fee settled successfully. 4 high-upside prospects flagged for academy scholarship consideration.",
                payload_json={"cost_gtex": academy_cost},
            )
            session.add(decision_acad)
            session.flush()
            session.add(
                ClubDelegatedDecisionAuditLog(
                    decision_id=decision_acad.id,
                    club_id=club_id,
                    actor_id=user_id,
                    action="gm_execute",
                    previous_status=None,
                    new_status="executed",
                    decision_note=decision_acad.decision_note,
                    snapshot_json={"payload": decision_acad.payload_json, "outcome": decision_acad.outcome_text},
                )
            )
            executed_actions.append(
                {
                    "type": "academy_recruitment",
                    "title": decision_acad.title,
                    "cost_gtex": academy_cost,
                }
            )
    else:
        if acad_approval or acad_authority == "owner_only" or canonical_mode == "owner_managed":
            academy_reason = "Owner approval required by the delegation matrix"
        elif academy_cost > max_unapproved_spend:
            academy_reason = "Academy intake exceeds the unapproved expenditure ceiling"
        else:
            academy_reason = "Academy intake is outside the active GM delegation policy"

        decision_acad = ClubDelegatedDecision(
            club_id=club_id,
            owner_user_id=user_id,
            activity_key="academy_recruitment",
            domain="sporting",
            proposed_by_role="general_manager",
            proposed_by_staff_name=gm_name,
            title="Grassroots Academy Showcase Authorization",
            summary=f"GM {gm_name} requests owner approval to disburse {academy_cost:,} GTEX for regional youth trials.",
            financial_amount_gtex=Decimal(str(academy_cost)),
            requires_owner_approval=True,
            approval_reason=academy_reason,
            status="pending_approval",
            execution_status="pending_execution",
            payload_json={"cost_gtex": academy_cost},
        )
        session.add(decision_acad)
        session.flush()
        escalated_proposals.append(
            {
                "decision_id": decision_acad.id,
                "title": decision_acad.title,
                "amount_gtex": academy_cost,
                "reason": academy_reason,
            }
        )

    session.commit()

    return {
        "club_id": club_id,
        "mode": canonical_mode,
        "executed_actions_count": len(executed_actions),
        "executed_actions": executed_actions,
        "escalated_proposals_count": len(escalated_proposals),
        "escalated_proposals": escalated_proposals,
        "blocked_actions_count": len(blocked_actions),
        "blocked_actions": blocked_actions,
    }


# ==============================================================================
# 4. Owner Resolution of GM Proposals
# ==============================================================================


def resolve_gm_proposal(
    session: Session,
    user_id: str,
    club_id: str,
    decision_id: str,
    action: str,
    decision_note: str | None = None,
) -> dict[str, Any]:
    """Resolves an escalated GM proposal (approve / reject) with authoritative execution & relationship impact."""
    stmt = select(ClubDelegatedDecision).where(
        ClubDelegatedDecision.id == decision_id,
        ClubDelegatedDecision.club_id == club_id,
        ClubDelegatedDecision.owner_user_id == user_id,
    )
    decision = session.scalar(stmt)
    if not decision:
        raise DelegationError(f"Delegated decision '{decision_id}' not found.", 404)

    if decision.status != "pending_approval":
        raise DelegationError(f"Decision '{decision_id}' is already {decision.status}.", 400)

    clean_action = action.lower().strip()
    if clean_action not in ("approve", "reject"):
        raise DelegationError("Action must be either 'approve' or 'reject'.", 400)

    payload = dict(decision.payload_json or {})

    if clean_action == "approve":
        # Execute the real business operation first. A proposal is not approved or
        # marked executed until its appointment/ledger settlement has succeeded.
        if decision.activity_key == "staff_hiring":
            if not payload.get("profile_id"):
                raise DelegationError("Staff-hiring proposal is missing its candidate profile.", 400)
            hire_result = living_staff_market.hire_staff_from_market(
                session,
                user_id,
                club_id,
                profile_id=payload["profile_id"],
                role=payload.get("role"),
                offered_salary_gtex=payload.get("salary"),
                contract_years=payload.get("contract_years", 2),
                pitch_note=f"Sanctioned by owner following GM proposal: {decision.title}",
            )
            if hire_result.get("success") is not True:
                reason = hire_result.get("message") or hire_result.get("reason") or "Staff offer was not accepted."
                raise DelegationError(f"Approval was not executed: {reason}", 409, code="proposal_execution_failed")
            decision.outcome_text = "Contract offer approved. Staff member appointed and ledger settlement completed."
        elif decision.activity_key == "academy_recruitment":
            academy_cost = float(payload.get("cost_gtex") or decision.financial_amount_gtex or 0)
            if not math.isfinite(academy_cost) or academy_cost <= 0:
                raise DelegationError("Academy proposal has an invalid settlement amount.", 400)
            try:
                ledger.record(
                    session,
                    event_type="academy_scouting",
                    source=ledger.club_account(club_id),
                    destination=ledger.WORLD_CLUBS,
                    currency=ledger.GTEX,
                    gross=academy_cost,
                    club_id=club_id,
                    user_id=user_id,
                    memo=f"Owner-approved academy scouting drive: {decision.title}",
                    check_funds=True,
                )
            except ledger.LedgerError as exc:
                raise DelegationError(f"Approval was not executed: {exc}", 409, code="proposal_settlement_failed") from exc
            decision.outcome_text = "Academy scouting proposal approved and ledger settlement completed."
        else:
            raise DelegationError(
                f"{decision.activity_key} has no executable Stage 5 operation yet; the proposal remains pending.",
                409,
                code="proposal_execution_unsupported",
            )

        decision.status = "approved"
        decision.execution_status = "executed"
        decision.decision_note = decision_note or "Approved by club owner."
        decision.resolved_at = utcnow()
        decision.decided_by_user_id = user_id

        _apply_gm_relationship_delta(
            session,
            club_id,
            reason=f"Owner ratified proposal: {decision.title}",
            delta_trust=4,
            delta_alignment=3,
            delta_tension=-3,
            delta_loyalty=3,
        )
    else:
        decision.status = "rejected"
        decision.execution_status = "rejected"
        decision.decision_note = decision_note or "Declined by club owner."
        decision.resolved_at = utcnow()
        decision.decided_by_user_id = user_id
        decision.outcome_text = f"Proposal rejected by owner: {decision.decision_note}"

        # Bilateral relationship: GM frustration
        _apply_gm_relationship_delta(
            session,
            club_id,
            reason=f"Owner vetoed proposal: {decision.title}",
            delta_trust=-2,
            delta_alignment=-2,
            delta_tension=4,
        )

    # Append to audit log
    audit_entry = ClubDelegatedDecisionAuditLog(
        decision_id=decision.id,
        club_id=club_id,
        actor_id=user_id,
        action=f"owner_{clean_action}",
        previous_status="pending_approval",
        new_status=decision.status,
        decision_note=decision_note,
        snapshot_json={"payload": payload, "outcome": decision.outcome_text},
    )
    session.add(audit_entry)
    session.commit()
    session.refresh(decision)

    rel = _get_gm_relationship(session, club_id)
    updated_relationships = {
        "trust": rel.trust if rel else 60,
        "tension": rel.tension if rel else 20,
        "alignment": rel.alignment if rel else 65,
    }
    return {
        "success": True,
        "decision_id": decision.id,
        "proposal_id": decision.id,
        "status": decision.status,
        "execution_status": decision.execution_status,
        "outcome_text": decision.outcome_text,
        "action_taken": decision.outcome_text or decision.decision_note or clean_action,
        "audit_logged": True,
        "updated_relationships": updated_relationships,
        "resolved_at": decision.resolved_at.isoformat() if decision.resolved_at else None,
    }
