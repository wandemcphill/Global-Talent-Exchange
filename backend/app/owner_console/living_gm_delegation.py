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
        authority_level = rule.get(
            "authority_level", "delegated_with_limits" if canonical_mode != "owner_managed" else "owner_only"
        )
        requires_approval = rule.get("requires_owner_approval", canonical_mode == "owner_managed")
        responsible_role = rule.get(
            "responsible_role", "general_manager" if canonical_mode != "owner_managed" else "owner"
        )

        activity_matrix.append(
            {
                "activity_key": k,
                "label": item["label"],
                "domain": item["domain"],
                "description": item["description"],
                "responsible_role": responsible_role,
                "authority_level": authority_level,
                "requires_owner_approval": requires_approval,
                "financial_control_key": item["financial_control_key"],
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

    if financial_controls:
        current_th = dict(policy.financial_thresholds_json or {})
        for k, v in financial_controls.items():
            current_th[k] = float(v) if isinstance(v, (int, float)) else v
        policy.financial_thresholds_json = current_th

    if activity_assignments:
        current_act = dict(policy.activity_assignments_json or {})
        for k, v in activity_assignments.items():
            if isinstance(v, dict):
                current_act[k] = {
                    "activity_key": k,
                    "responsible_role": v.get("responsible_role", "general_manager"),
                    "authority_level": v.get("authority_level", "delegated_with_limits"),
                    "requires_owner_approval": bool(v.get("requires_owner_approval", False)),
                }
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
            cand_salary = best_candidate["expected_salary_gtex"]
            rule = assignments.get("staff_hiring") or {}
            requires_approval = rule.get("requires_owner_approval", canonical_mode == "owner_managed")
            is_owner_only = rule.get("authority_level") == "owner_only" or canonical_mode == "owner_managed"

            # Check if GM can autonomously hire
            can_autonomously_hire = (
                not is_owner_only
                and not requires_approval
                and cand_salary <= max_staff_salary
                and not policy.is_suspended
            )

            if can_autonomously_hire:
                # GM hires autonomously
                hire_res = living_staff_market.hire_staff_from_market(
                    session,
                    user_id,
                    club_id,
                    profile_id=best_candidate["profile_id"],
                    role=role_key,
                    offered_salary_gtex=cand_salary,
                    contract_years=2,
                    pitch_note=f"Appointed autonomously by General Manager {gm_name} under {canonical_mode} delegation.",
                )

                # Log decision
                decision = ClubDelegatedDecision(
                    club_id=club_id,
                    owner_user_id=user_id,
                    activity_key="staff_hiring",
                    domain="club_operations",
                    proposed_by_role="general_manager",
                    proposed_by_staff_name=gm_name,
                    title=f"Autonomously Appointed {best_candidate['name']} as {target_vac['role_label']}",
                    summary=f"GM {gm_name} successfully resolved department vacancy by recruiting {best_candidate['name']} (OVR {best_candidate['rating']}).",
                    financial_amount_gtex=Decimal(str(cand_salary)),
                    requires_owner_approval=False,
                    status="executed",
                    execution_status="executed",
                    decided_by_user_id=user_id,
                    decision_note="Executed autonomously under authorized GM delegation limits.",
                    outcome_text="Contract ratified and signed. Department operational efficiency restored.",
                    payload_json={"profile_id": best_candidate["profile_id"], "role": role_key, "salary": cand_salary},
                )
                session.add(decision)
                session.flush()

                executed_actions.append(
                    {
                        "type": "staff_hire",
                        "title": decision.title,
                        "details": hire_res.get("message"),
                    }
                )
            else:
                # Escalate proposal to owner
                reason = (
                    "Exceeds authorized staff salary ceiling"
                    if cand_salary > max_staff_salary
                    else "Policy mandates owner ratification"
                )
                decision = ClubDelegatedDecision(
                    club_id=club_id,
                    owner_user_id=user_id,
                    activity_key="staff_hiring",
                    domain="club_operations",
                    proposed_by_role="general_manager",
                    proposed_by_staff_name=gm_name,
                    title=f"Contract Offer Recommendation: {best_candidate['name']} for {target_vac['role_label']}",
                    summary=(
                        f"GM {gm_name} identified top candidate {best_candidate['name']} (OVR {best_candidate['rating']}, Expected Salary: ₦{cand_salary:,} GTEX). "
                        f"Escalated for owner ratification: {reason}."
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
                        "contract_years": 2,
                    },
                )
                session.add(decision)
                session.flush()

                # Add inbox alert
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

    # 2. Academy Trial & Grassroots Intake Proposal
    academy_cost = 2500
    rule_acad = assignments.get("academy_recruitment") or {}
    acad_approval = rule_acad.get("requires_owner_approval", canonical_mode == "owner_managed")

    if not acad_approval and academy_cost <= max_unapproved_spend and canonical_mode == "gm_led":
        # Disburse trial fee via ledger
        club_acct = ledger.club_account(club_id)
        try:
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
                check_funds=False,
            )
        except Exception:
            pass

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
            outcome_text="Trial concluded. 4 high-upside prospects flagged for academy scholarship consideration.",
            payload_json={"cost_gtex": academy_cost},
        )
        session.add(decision_acad)
        session.flush()

        executed_actions.append(
            {
                "type": "academy_recruitment",
                "title": decision_acad.title,
                "cost_gtex": academy_cost,
            }
        )
    elif canonical_mode == "owner_managed":
        # Escalate as proposal
        decision_acad = ClubDelegatedDecision(
            club_id=club_id,
            owner_user_id=user_id,
            activity_key="academy_recruitment",
            domain="sporting",
            proposed_by_role="general_manager",
            proposed_by_staff_name=gm_name,
            title="Grassroots Academy Showcase Authorization",
            summary=f"GM {gm_name} requests owner approval to disburse ₦{academy_cost:,} GTEX for regional youth trials.",
            financial_amount_gtex=Decimal(str(academy_cost)),
            requires_owner_approval=True,
            approval_reason="Owner-managed policy requires explicit sanction for scouting drives",
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
                "reason": "Owner approval required",
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
        decision.status = "approved"
        decision.execution_status = "executed"
        decision.decision_note = decision_note or "Approved by club owner."
        decision.resolved_at = utcnow()
        decision.decided_by_user_id = user_id

        # Execute payload action if staff hiring
        if decision.activity_key == "staff_hiring" and payload.get("profile_id"):
            living_staff_market.hire_staff_from_market(
                session,
                user_id,
                club_id,
                profile_id=payload["profile_id"],
                role=payload.get("role"),
                offered_salary_gtex=payload.get("salary"),
                contract_years=payload.get("contract_years", 2),
                pitch_note=f"Sanctioned by owner following GM proposal: {decision.title}",
            )
            decision.outcome_text = "Contract offer approved. Staff member appointed and settled."

        # Bilateral relationship: GM feels validated
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

    return {
        "success": True,
        "decision_id": decision.id,
        "status": decision.status,
        "execution_status": decision.execution_status,
        "outcome_text": decision.outcome_text,
        "resolved_at": decision.resolved_at.isoformat() if decision.resolved_at else None,
    }
