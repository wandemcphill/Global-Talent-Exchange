"""GTEX Living Football World - Stage 5
Test Suite: General Manager Delegation & Owner Control Engine
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.club_growth import (
    ClubStaffProfile,
    ClubStaffContract,
    ClubStaffAssignment,
)
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
)
from app.models.user import User
from app.owner_console import (
    delegation_service,
    ledger,
    living_gm_delegation,
    living_staff_market,
    router as owner_router,
)
from app.owner_console.delegation_service import DelegationError
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubState,
    OwnerClubRelationship,
    ClubDelegatedDecision,
    ClubDelegatedDecisionAuditLog,
)

WORLD_NOW = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)


def _session() -> Session:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        eng,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            AuditLog.__table__,
            EventOutbox.__table__,
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            LedgerAccount.__table__,
            LedgerBalanceProjection.__table__,
            LedgerEntry.__table__,
            LedgerTransaction.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    return sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)()


def _bootstrap_club(
    session: Session, user_id: str, club_id: str, prestige: int = 65
) -> tuple[User, ClubProfile, OwnerClubState]:
    u = User(
        id=user_id,
        email=f"{user_id}@gtex.test",
        username=f"owner_{user_id}",
        password_hash="synthetic_hash",  # pragma: allowlist secret
        role="authenticated",
        is_active=True,
    )
    cp = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name=f"Club {club_id}",
        slug=f"club-{club_id}",
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
    )
    session.add_all([u, cp])
    session.flush()

    state = OwnerClubState(
        id=club_id,
        club_id=club_id,
        owner_user_id=user_id,
        club_name=cp.club_name,
        prestige=prestige,
        facilities_json={
            "_executive_staff": {
                "general_manager": {
                    "id": "staff_gm_1",
                    "name": "Dayo Adeleke",
                    "role": "General Manager",
                    "rating": 84,
                    "salary_gtex": 1800,
                    "mood": 80,
                },
                "chief_scout": None,
                "head_of_youth_development": None,
            },
        },
        manager_json={
            "id": "staff_mgr_1",
            "name": "Emmanuel Amuneke",
            "role": "First-Team Manager",
            "rating": 86,
            "salary": 3000,
            "mood": 85,
        },
    )
    session.add(state)
    session.flush()

    # Establish initial bilateral GM relationship
    rel = OwnerClubRelationship(
        club_id=club_id,
        pairing_key=f"owner:{user_id}:staff:general_manager:staff_gm_1",
        participant_a_type="owner",
        participant_a_id=user_id,
        participant_a_name=u.username,
        participant_b_type="staff",
        participant_b_id="staff:general_manager:staff_gm_1",
        participant_b_name="Dayo Adeleke",
        trust=60,
        respect=65,
        affinity=55,
        tension=20,
        alignment=65,
        influence=60,
        loyalty=70,
        status="active",
    )
    session.add(rel)
    session.flush()

    # Seed candidates and a funded club treasury for authoritative settlement tests.
    living_staff_market.ensure_staff_market_profiles(session)
    ledger.record(
        session,
        event_type="test_club_funding",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=2_000_000,
        club_id=club_id,
        user_id=user_id,
        memo="Deterministic test-club treasury funding",
    )

    return u, cp, state


# ==============================================================================
# Unit & Integration Tests
# ==============================================================================


def test_gm_delegation_overview_initialization():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_1", "c_gm_1", prestige=70)

    overview = living_gm_delegation.get_gm_delegation_overview(session, u.id, cp.id)

    assert overview["club_id"] == cp.id
    assert overview["mode"] == "balanced"
    assert overview["is_suspended"] is False
    assert overview["general_manager"]["name"] == "Dayo Adeleke"
    assert overview["relationship"]["trust"] == 60
    assert overview["relationship"]["tension"] == 20

    # 12 activities in matrix
    assert len(overview["activity_matrix"]) == 12
    act_keys = {a["activity_key"] for a in overview["activity_matrix"]}
    assert "staff_hiring" in act_keys
    assert "player_scouting" in act_keys
    assert "academy_recruitment" in act_keys

    # Financial controls present
    th = overview["financial_controls"]
    assert th["max_expenditure_unapproved_gtex"] == 10000.0
    assert th["max_staff_salary_unapproved_gtex"] == 1500.0


def test_update_gm_delegation_mode_transitions():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_2", "c_gm_2", prestige=70)

    # 1. Switch to gm_led (empowered GM)
    res_gm = living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "gm_led")
    assert res_gm["mode"] == "gm_led"
    assert res_gm["relationship"]["trust"] == 66  # +6
    assert res_gm["relationship"]["tension"] == 15  # -5
    assert res_gm["financial_controls"]["max_staff_salary_unapproved_gtex"] == 3500.0

    # 2. Switch to owner_managed (micromanagement)
    res_own = living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "owner_managed")
    assert res_own["mode"] == "owner_managed"
    assert res_own["relationship"]["tension"] == 21  # +6
    assert res_own["relationship"]["trust"] == 63  # -3
    assert res_own["financial_controls"]["max_staff_salary_unapproved_gtex"] == 0.0


def test_update_gm_matrix_and_financial_controls():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_3", "c_gm_3", prestige=70)

    updated = living_gm_delegation.update_gm_matrix_and_financial_controls(
        session,
        u.id,
        cp.id,
        financial_controls={"max_staff_salary_unapproved_gtex": 2200.0, "allow_emergency_spending": 1.0},
        activity_assignments={"staff_hiring": {"authority_level": "full_autonomy", "requires_owner_approval": False}},
    )

    assert updated["financial_controls"]["max_staff_salary_unapproved_gtex"] == 2200.0
    assert updated["financial_controls"]["allow_emergency_spending"] == 1.0

    hiring_rule = next(a for a in updated["activity_matrix"] if a["activity_key"] == "staff_hiring")
    assert hiring_rule["authority_level"] == "full_autonomy"
    assert hiring_rule["requires_owner_approval"] is False


def test_gm_operational_cycle_autonomous_hiring_in_gm_led():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_4", "c_gm_4", prestige=75)

    # Set mode to gm_led (max_staff_salary = 3500)
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "gm_led")

    # Run operational cycle
    cycle_res = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)

    assert cycle_res["executed_actions_count"] > 0
    executed_types = [a["type"] for a in cycle_res["executed_actions"]]
    assert "staff_hire" in executed_types or "academy_recruitment" in executed_types

    # Verify decision logged in database
    decisions = session.scalars(select(ClubDelegatedDecision).where(ClubDelegatedDecision.club_id == cp.id)).all()
    assert len(decisions) >= 1
    executed = [d for d in decisions if d.status == "executed"]
    assert executed
    for decision in executed:
        audit = session.scalar(
            select(ClubDelegatedDecisionAuditLog).where(
                ClubDelegatedDecisionAuditLog.decision_id == decision.id,
                ClubDelegatedDecisionAuditLog.action == "gm_execute",
            )
        )
        assert audit is not None


def test_gm_operational_cycle_does_not_log_rejected_staff_offer_as_executed(monkeypatch):
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_failed_cycle_hire", "c_gm_failed_cycle_hire", prestige=75)
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "gm_led")

    monkeypatch.setattr(
        living_staff_market,
        "get_club_vacancies",
        lambda *args, **kwargs: {"vacancies": [{"role_key": "general_manager", "role_label": "General Manager"}]},
    )
    monkeypatch.setattr(
        living_staff_market,
        "list_staff_market_candidates",
        lambda *args, **kwargs: {
            "candidates": [
                {
                    "profile_id": "profile_candidate_rejected",
                    "name": "Candidate Rejected",
                    "rating": 80,
                    "expected_salary_gtex": 1000,
                }
            ]
        },
    )
    monkeypatch.setattr(
        living_staff_market,
        "hire_staff_from_market",
        lambda *args, **kwargs: {
            "success": False,
            "status": "rejected",
            "reason": "insufficient_prestige",
            "message": "Candidate declined the appointment.",
        },
    )

    cycle = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)

    assert "staff_hire" in [action["type"] for action in cycle["blocked_actions"]]
    assert "staff_hire" not in [action["type"] for action in cycle["executed_actions"]]
    assert (
        session.scalar(
            select(ClubDelegatedDecision).where(
                ClubDelegatedDecision.club_id == cp.id,
                ClubDelegatedDecision.activity_key == "staff_hiring",
                ClubDelegatedDecision.execution_status == "executed",
            )
        )
        is None
    )


def test_gm_operational_cycle_escalates_when_limit_exceeded():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_5", "c_gm_5", prestige=75)

    # Balanced mode has max_staff_salary = 1500; top candidates often demand 1600+
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "balanced")
    # Restrict staff salary to 500 to guarantee escalation
    living_gm_delegation.update_gm_matrix_and_financial_controls(
        session, u.id, cp.id, financial_controls={"max_staff_salary_unapproved_gtex": 500.0}
    )

    cycle_res = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)

    assert cycle_res["escalated_proposals_count"] >= 1
    esc = cycle_res["escalated_proposals"][0]
    assert "Exceeds authorized" in esc["reason"] or "ratification" in esc["reason"]

    # Verify pending decision exists
    pending = session.scalar(
        select(ClubDelegatedDecision).where(
            ClubDelegatedDecision.club_id == cp.id,
            ClubDelegatedDecision.status == "pending_approval",
        )
    )
    assert pending is not None
    assert pending.requires_owner_approval is True


def test_resolve_gm_proposal_approve():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_6", "c_gm_6", prestige=70)

    # Seed a pending proposal
    decision = ClubDelegatedDecision(
        club_id=cp.id,
        owner_user_id=u.id,
        activity_key="academy_recruitment",
        domain="sporting",
        proposed_by_role="general_manager",
        proposed_by_staff_name="Dayo Adeleke",
        title="Academy Scouting Trial",
        summary="Proposal to fund an academy scouting trial.",
        financial_amount_gtex=Decimal("12000.00"),
        requires_owner_approval=True,
        status="pending_approval",
        execution_status="pending_execution",
        payload_json={"cost_gtex": 12000},
    )
    session.add(decision)
    session.flush()

    res = living_gm_delegation.resolve_gm_proposal(
        session, u.id, cp.id, decision.id, action="approve", decision_note="Approved. Proceed with installation."
    )

    assert res["success"] is True
    assert res["status"] == "approved"
    assert res["execution_status"] == "executed"

    # GM relationship improved
    rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.club_id == cp.id))
    assert rel.trust == 64  # +4
    assert rel.tension == 17  # -3

    # Audit log entry exists
    audit = session.scalar(
        select(ClubDelegatedDecisionAuditLog).where(ClubDelegatedDecisionAuditLog.decision_id == decision.id)
    )
    assert audit is not None
    assert audit.action == "owner_approve"


def test_resolve_gm_proposal_reject():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_7", "c_gm_7", prestige=70)

    decision = ClubDelegatedDecision(
        club_id=cp.id,
        owner_user_id=u.id,
        activity_key="department_spending",
        domain="club_operations",
        proposed_by_role="general_manager",
        proposed_by_staff_name="Dayo Adeleke",
        title="Unscheduled Corporate Jet Charter",
        summary="Charter flight for scouting expedition.",
        financial_amount_gtex=Decimal("25000.00"),
        requires_owner_approval=True,
        status="pending_approval",
        execution_status="pending_execution",
        payload_json={"cost_gtex": 25000},
    )
    session.add(decision)
    session.flush()

    res = living_gm_delegation.resolve_gm_proposal(
        session, u.id, cp.id, decision.id, action="reject", decision_note="Rejected. Budget reserves too tight."
    )

    assert res["success"] is True
    assert res["status"] == "rejected"
    assert res["execution_status"] == "rejected"

    rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.club_id == cp.id))
    assert rel.trust == 58  # -2
    assert rel.tension == 24  # +4


def test_router_gm_delegation_endpoints():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_router_gm", "c_router_gm", prestige=70)

    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_current_user] = lambda: u
    app.dependency_overrides[get_session] = lambda: session

    client = TestClient(app)

    # 1. GET overview
    res_get = client.get(f"/owner/clubs/{cp.id}/living-world/gm-delegation")
    assert res_get.status_code == 200, res_get.text
    data = res_get.json()
    assert data["club_id"] == cp.id
    assert data["mode"] == "balanced"
    assert len(data["activity_matrix"]) == 12

    # 2. POST mode switch
    res_mode = client.post(
        f"/owner/clubs/{cp.id}/living-world/gm-delegation/mode",
        json={"mode": "gm_led"},
    )
    assert res_mode.status_code == 200, res_mode.text
    assert res_mode.json()["mode"] == "gm_led"

    # 3. PUT matrix update
    res_matrix = client.put(
        f"/owner/clubs/{cp.id}/living-world/gm-delegation/matrix",
        json={
            "financial_controls": {"max_expenditure_unapproved_gtex": 65000},
            "activity_assignments": {
                "staff_hiring": {"authority_level": "full_autonomy", "requires_owner_approval": False}
            },
        },
    )
    assert res_matrix.status_code == 200, res_matrix.text
    assert res_matrix.json()["financial_controls"]["max_expenditure_unapproved_gtex"] == 65000

    # 4. POST evaluate operations
    res_eval = client.post(f"/owner/clubs/{cp.id}/living-world/gm-delegation/evaluate-operations")
    assert res_eval.status_code == 200, res_eval.text
    assert "executed_actions_count" in res_eval.json()


def test_gm_matrix_rejects_invalid_and_unsupported_authority():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_matrix_validation", "c_gm_matrix_validation")

    with pytest.raises(DelegationError):
        living_gm_delegation.update_gm_matrix_and_financial_controls(
            session, u.id, cp.id, financial_controls={"max_expenditure_unapproved_gtex": -1}
        )

    with pytest.raises(DelegationError):
        living_gm_delegation.update_gm_matrix_and_financial_controls(
            session,
            u.id,
            cp.id,
            activity_assignments={
                "player_scouting": {
                    "authority_level": "full_autonomy",
                    "responsible_role": "general_manager",
                    "requires_owner_approval": False,
                }
            },
        )

    overview = living_gm_delegation.get_gm_delegation_overview(session, u.id, cp.id)
    unsupported = next(a for a in overview["activities"] if a["activity_key"] == "player_scouting")
    assert unsupported["execution_supported"] is False
    assert unsupported["requires_owner_approval"] is True
    assert unsupported["gm_can_execute"] is False


def test_owner_approval_does_not_mark_rejected_staff_offer_as_executed(monkeypatch):
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_failed_hire", "c_gm_failed_hire")

    decision = ClubDelegatedDecision(
        club_id=cp.id,
        owner_user_id=u.id,
        activity_key="staff_hiring",
        domain="club_operations",
        proposed_by_role="general_manager",
        proposed_by_staff_name="Dayo Adeleke",
        title="Appoint Chief Scout",
        summary="Owner approval requested for a staff appointment.",
        financial_amount_gtex=Decimal("1800.00"),
        requires_owner_approval=True,
        status="pending_approval",
        execution_status="pending_execution",
        payload_json={"profile_id": "candidate-not-accepted", "role": "chief_scout", "salary": 1800},
    )
    session.add(decision)
    session.flush()

    monkeypatch.setattr(
        living_staff_market,
        "hire_staff_from_market",
        lambda *args, **kwargs: {
            "success": False,
            "status": "counter_offer",
            "reason": "salary_below_market",
            "message": "Candidate requested a higher salary.",
        },
    )

    with pytest.raises(DelegationError, match="Approval was not executed"):
        living_gm_delegation.resolve_gm_proposal(session, u.id, cp.id, decision.id, action="approve")

    session.refresh(decision)
    assert decision.status == "pending_approval"
    assert decision.execution_status == "pending_execution"
    assert (
        session.scalar(
            select(ClubDelegatedDecisionAuditLog).where(ClubDelegatedDecisionAuditLog.decision_id == decision.id)
        )
        is None
    )
    rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.club_id == cp.id))
    assert rel.trust == 60


def test_staff_market_does_not_create_contract_when_treasury_cannot_fund_it(monkeypatch):
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_unfunded_hire", "c_gm_unfunded_hire", prestige=100)
    profile = session.scalar(select(ClubStaffProfile))
    assert profile is not None

    monkeypatch.setattr(
        living_staff_market,
        "evaluate_staff_contract_offer",
        lambda **kwargs: {"accepted": True, "outcome": "accepted", "message": "Offer accepted."},
    )
    monkeypatch.setattr(living_staff_market.ledger, "balance", lambda *args, **kwargs: Decimal("0.00"))

    result = living_staff_market.hire_staff_from_market(
        session,
        u.id,
        cp.id,
        profile_id=profile.id,
        role=profile.staff_type,
        offered_salary_gtex=1000,
        contract_years=2,
    )

    assert result["success"] is False
    assert result["reason"] == "insufficient_funds"
    assert session.scalar(select(ClubStaffContract).where(ClubStaffContract.club_id == cp.id)) is None


def test_gm_cycle_blocks_academy_settlement_when_suspended_or_unfunded(monkeypatch):
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_blocked_academy", "c_gm_blocked_academy", prestige=80)
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "gm_led")
    monkeypatch.setattr(
        living_staff_market,
        "get_club_vacancies",
        lambda *args, **kwargs: {"vacancies": []},
    )
    monkeypatch.setattr(living_gm_delegation.ledger, "balance", lambda *args, **kwargs: Decimal("0.00"))

    cycle = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)

    assert "academy_recruitment" in [action["type"] for action in cycle["blocked_actions"]]
    assert "academy_recruitment" not in [action["type"] for action in cycle["executed_actions"]]
    assert (
        session.scalar(
            select(ClubDelegatedDecision).where(
                ClubDelegatedDecision.club_id == cp.id,
                ClubDelegatedDecision.activity_key == "academy_recruitment",
                ClubDelegatedDecision.execution_status == "executed",
            )
        )
        is None
    )

    # Suspension must block the same path even after funds are restored.
    monkeypatch.setattr(living_gm_delegation.ledger, "balance", lambda *args, **kwargs: Decimal("2000000"))
    policy = delegation_service.get_or_create_delegation_policy(session, cp.id, u.id)
    policy.is_suspended = True
    policy.suspension_reason = "Owner freeze"
    session.commit()
    cycle_suspended = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)
    assert "academy_recruitment" in [action["type"] for action in cycle_suspended["blocked_actions"]]
    assert not cycle_suspended["executed_actions"]


def test_owner_managed_mode_cannot_be_overridden_by_matrix_toggle():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_gm_owner_only", "c_gm_owner_only")
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "owner_managed")

    overview = living_gm_delegation.get_gm_delegation_overview(session, u.id, cp.id)
    hiring = next(a for a in overview["activities"] if a["activity_key"] == "staff_hiring")
    assert hiring["requires_owner_approval"] is True
    assert hiring["gm_can_execute"] is False

    with pytest.raises(DelegationError, match="cannot be delegated"):
        living_gm_delegation.update_gm_matrix_and_financial_controls(
            session,
            u.id,
            cp.id,
            activity_assignments={
                "staff_hiring": {
                    "responsible_role": "general_manager",
                    "authority_level": "full_autonomy",
                    "requires_owner_approval": False,
                }
            },
        )
