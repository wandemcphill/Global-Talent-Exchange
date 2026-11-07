"""Comprehensive tests for GTEX Club Authority Engine and Owner Delegation Foundation (Phase 1D)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.ecosystem_events import EcosystemDomain, gtex_ecosystem_bus
from app.owner_console import delegation_service
from app.owner_console.models import (
    ClubDelegatedDecision,
    ClubDelegationPolicy,
    OwnerClubState,
    OwnerInboxItem,
)


def _claim_and_activate(client, headers, city: str = "Lagos") -> str:
    resp = client.post("/api/owner/clubs/claim", headers=headers, json={"city_name": city, "country_code": "NG"})
    assert resp.status_code == 200, resp.text
    club_id = resp.json()["club_id"]
    act = client.post(f"/api/owner/clubs/{club_id}/activate", headers=headers)
    assert act.status_code == 200, act.text
    return club_id


def test_delegation_policy_initialization_and_org_structure(client, bootstrap_admin_headers, app):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # 1. Fetch initial authority policy
    resp = client.get(f"/api/owner/clubs/{club_id}/authority/policy", headers=bootstrap_admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["club_id"] == club_id
    assert data["mode"] == "balanced"
    assert data["is_suspended"] is False
    assert data["financial_thresholds"]["recruitment_max_gtex"] == 25000.0
    assert data["financial_thresholds"]["operational_spend_max_gtex"] == 10000.0

    # Verify all 21 activities are present across the 3 domains
    assignments = data["activity_assignments"]
    assert len(assignments) == 21
    assert assignments["first_team_tactics"]["responsible_role"] == "first_team_manager"
    assert assignments["first_team_tactics"]["authority_level"] == "full_autonomy"
    assert assignments["player_recruitment"]["responsible_role"] == "general_manager"
    assert assignments["player_recruitment"]["authority_level"] == "delegated_with_limits"
    assert assignments["staff_recruitment_dismissal"]["responsible_role"] == "owner"
    assert assignments["staff_recruitment_dismissal"]["authority_level"] == "owner_only"

    # Reserved decisions
    assert "staff_recruitment_dismissal" in data["reserved_decisions"]
    assert "financial_planning" in data["reserved_decisions"]

    # 2. Fetch organizational structure
    org_resp = client.get(
        f"/api/owner/clubs/{club_id}/authority/org-structure",
        headers=bootstrap_admin_headers,
    )
    assert org_resp.status_code == 200, org_resp.text
    org = org_resp.json()
    assert org["club_id"] == club_id
    roles = {p["role_key"] for p in org["staff_positions"]}
    assert {
        "owner",
        "general_manager",
        "first_team_manager",
        "head_of_youth_development",
        "chief_scout",
        "medical_director",
    }.issubset(roles)


def test_switch_management_configurations(client, bootstrap_admin_headers):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # Switch to hands_on
    resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=bootstrap_admin_headers,
        json={"mode": "hands_on"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mode"] == "hands_on"
    assert data["financial_thresholds"]["recruitment_max_gtex"] == 0.0
    assert data["activity_assignments"]["first_team_tactics"]["authority_level"] == "owner_only"

    # Switch to delegating (executive owner)
    resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=bootstrap_admin_headers,
        json={"mode": "delegating"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["mode"] == "delegating"
    assert data["financial_thresholds"]["recruitment_max_gtex"] == 100000.0
    assert data["activity_assignments"]["player_recruitment"]["authority_level"] == "delegated_with_limits"

    # Invalid mode rejection
    bad_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=bootstrap_admin_headers,
        json={"mode": "anarchic_owner"},
    )
    assert bad_resp.status_code == 400


def test_authority_evaluation_and_financial_limits(client, bootstrap_admin_headers):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # Reset to balanced mode
    client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=bootstrap_admin_headers,
        json={"mode": "balanced"},
    )

    # 1. Manager First-team tactics -> allowed with full autonomy
    eval_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "first_team_tactics",
            "proposed_by_role": "first_team_manager",
        },
    )
    assert eval_resp.status_code == 200, eval_resp.text
    res = eval_resp.json()
    assert res["allowed"] is True
    assert res["requires_approval"] is False
    assert res["responsible_role"] == "first_team_manager"
    assert res["authority_level"] == "full_autonomy"

    # 2. GM recruitment under threshold (18,000 GTX vs 25,000 GTX limit)
    eval_under = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "financial_amount_gtex": 18000.0,
            "proposed_by_role": "general_manager",
        },
    )
    assert eval_under.status_code == 200
    res_under = eval_under.json()
    assert res_under["allowed"] is True
    assert res_under["requires_approval"] is False
    assert res_under["staff_impact"] is not None

    # 3. GM recruitment exceeding threshold (42,000 GTX vs 25,000 GTX limit)
    eval_over = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "financial_amount_gtex": 42000.0,
            "proposed_by_role": "general_manager",
        },
    )
    assert eval_over.status_code == 200
    res_over = eval_over.json()
    assert res_over["allowed"] is True
    assert res_over["requires_approval"] is True
    assert "exceeds delegated limit" in res_over["reason"]

    # 4. Reserved decision: Staff recruitment / dismissal requires owner approval regardless of role
    eval_reserved = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "staff_recruitment_dismissal",
            "proposed_by_role": "general_manager",
        },
    )
    assert eval_reserved.status_code == 200
    res_res = eval_reserved.json()
    assert res_res["requires_approval"] is True
    assert "reserved" in res_res["reason"].lower()


def test_propose_and_resolve_delegated_decisions(client, bootstrap_admin_headers, app):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # 1. Propose under-threshold delegated action -> Auto-approved
    prop_auto = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "scouting_assignments",
            "proposed_by_role": "chief_scout",
            "title": "Deploy Scout to West African Talent Combine",
            "summary": "Scout deployment to observe 15 prospects in Lagos.",
            "financial_amount_gtex": 1200.0,
        },
    )
    assert prop_auto.status_code == 200, prop_auto.text
    auto_data = prop_auto.json()
    assert auto_data["status"] == "auto_approved"
    assert auto_data["requires_owner_approval"] is False

    # 2. Propose over-threshold action -> Pending approval & creates Inbox Item
    prop_escalated = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "title": "Marquee Striker Bid: Victor Okoro",
            "summary": "Formal bid of 45,000 GTX for Premier League academy striker.",
            "financial_amount_gtex": 45000.0,
        },
    )
    assert prop_escalated.status_code == 200, prop_escalated.text
    esc_data = prop_escalated.json()
    decision_id = esc_data["decision_id"]
    assert esc_data["status"] == "pending_approval"
    assert esc_data["requires_owner_approval"] is True

    # Check that it appears in pending escalations
    esc_resp = client.get(
        f"/api/owner/clubs/{club_id}/authority/escalations",
        headers=bootstrap_admin_headers,
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["pending_count"] >= 1
    assert any(item["id"] == decision_id for item in esc_resp.json()["escalations"])

    # 3. Owner resolves the decision: Approves it
    resolve_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{decision_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"action": "approve", "decision_note": "Approved by Chairman."},
    )
    assert resolve_resp.status_code == 200, resolve_resp.text
    assert resolve_resp.json()["status"] == "approved"

    # Decision no longer pending
    esc_after = client.get(
        f"/api/owner/clubs/{club_id}/authority/escalations",
        headers=bootstrap_admin_headers,
    )
    assert all(item["id"] != decision_id for item in esc_after.json()["escalations"])

    # Appears in decision history log
    hist_resp = client.get(
        f"/api/owner/clubs/{club_id}/authority/decisions",
        headers=bootstrap_admin_headers,
    )
    assert hist_resp.status_code == 200
    decisions = hist_resp.json()["decisions"]
    assert any(d["id"] == decision_id and d["status"] == "approved" for d in decisions)


def test_temporary_owner_override_and_revocation(client, bootstrap_admin_headers):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # 1. Apply temporary owner override on player_recruitment
    override_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/override",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "override_role": "owner",
            "reason": "Owner taking direct control of transfer window.",
        },
    )
    assert override_resp.status_code == 200, override_resp.text
    assert "player_recruitment" in override_resp.json()["temporary_overrides"]

    # Authority evaluation now flags override
    eval_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "financial_amount_gtex": 5000.0,
        },
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["policy_status"] == "override"
    assert eval_resp.json()["requires_approval"] is True

    # 2. Remove temporary override
    del_resp = client.delete(
        f"/api/owner/clubs/{club_id}/authority/override/player_recruitment",
        headers=bootstrap_admin_headers,
    )
    assert del_resp.status_code == 200
    assert "player_recruitment" not in del_resp.json()["temporary_overrides"]

    # GM normal authority is restored
    eval_restored = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "financial_amount_gtex": 5000.0,
        },
    )
    assert eval_restored.status_code == 200
    assert eval_restored.json()["policy_status"] == "active"
    assert eval_restored.json()["requires_approval"] is False


def test_emergency_delegation_suspension(client, bootstrap_admin_headers):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # 1. Emergency suspend delegation
    susp_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/suspension",
        headers=bootstrap_admin_headers,
        json={
            "suspend": True,
            "reason": "Financial audit underway; all staff powers frozen.",
        },
    )
    assert susp_resp.status_code == 200, susp_resp.text
    assert susp_resp.json()["is_suspended"] is True
    assert susp_resp.json()["status"] == "suspended"

    # Evaluation confirms suspended status
    eval_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "training_and_coaching",
            "proposed_by_role": "first_team_manager",
        },
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["policy_status"] == "suspended"
    assert eval_resp.json()["requires_approval"] is True

    # 2. Restore delegation
    restore_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/suspension",
        headers=bootstrap_admin_headers,
        json={"suspend": False},
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_suspended"] is False

    eval_restored = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "training_and_coaching",
            "proposed_by_role": "first_team_manager",
        },
    )
    assert eval_restored.status_code == 200
    assert eval_restored.json()["policy_status"] == "active"
    assert eval_restored.json()["requires_approval"] is False


def test_unauthorized_actor_cannot_resolve_decision(client, bootstrap_admin_headers, auth_user_factory):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # Propose escalated decision
    prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "title": "Striker Signing",
            "summary": "Transfer",
            "financial_amount_gtex": 35000.0,
        },
    )
    decision_id = prop.json()["decision_id"]

    # Another user tries to resolve owner's decision
    other_user = auth_user_factory(suffix="intruder", account_type="user")
    intruder_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{decision_id}/resolve",
        headers=other_user["headers"],
        json={"action": "approve"},
    )
    assert intruder_resp.status_code in {403, 404}


def test_ecosystem_event_published_on_delegation_actions(client, bootstrap_admin_headers, app):
    club_id = _claim_and_activate(client, bootstrap_admin_headers)

    # Switch mode publishes event
    client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=bootstrap_admin_headers,
        json={"mode": "delegating"},
    )

    with app.state.session_factory() as session:
        from app.models.event_backbone import EventOutbox

        events = session.scalars(
            select(EventOutbox)
            .where(
                EventOutbox.event_type == "owner_governance.delegation.mode_changed",
            )
            .order_by(EventOutbox.created_at.desc())
        ).all()
        assert len(events) >= 1
        payload = events[0].payload_json
        assert payload["new_mode"] == "delegating"
        eco_meta = payload.get("__ecosystem__", {})
        assert eco_meta.get("domain") == EcosystemDomain.OWNER_GOVERNANCE


def test_ten_security_scenarios_and_financial_integrity(client, bootstrap_admin_headers, auth_user_factory, app):
    """
    Mandated Phase 1D Final Acceptance & Security Verification:
    Tests the 10 core security scenarios, financial ledger non-mutation,
    audit trail immutability, and staff competence advisory isolation.
    """
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Kano")
    other_user = auth_user_factory(suffix="intruder_sec", account_type="user")

    # --------------------------------------------------------------------------
    # Scenario 1: An owner managing their own club
    # --------------------------------------------------------------------------
    resp_owner = client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=bootstrap_admin_headers,
        json={"mode": "balanced"},
    )
    assert resp_owner.status_code == 200
    assert resp_owner.json()["mode"] == "balanced"

    # --------------------------------------------------------------------------
    # Scenario 2: A user attempting to manage another owner's club (403 Forbidden)
    # --------------------------------------------------------------------------
    resp_unauth_policy = client.get(
        f"/api/owner/clubs/{club_id}/authority/policy",
        headers=other_user["headers"],
    )
    assert resp_unauth_policy.status_code == 403

    resp_unauth_mode = client.post(
        f"/api/owner/clubs/{club_id}/authority/mode",
        headers=other_user["headers"],
        json={"mode": "hands_on"},
    )
    assert resp_unauth_mode.status_code == 403

    resp_unauth_susp = client.post(
        f"/api/owner/clubs/{club_id}/authority/suspension",
        headers=other_user["headers"],
        json={"suspend": True},
    )
    assert resp_unauth_susp.status_code == 403

    # --------------------------------------------------------------------------
    # Scenario 3: A general manager exercising delegated authority
    # --------------------------------------------------------------------------
    gm_prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "title": "Sign Academy Prospect",
            "summary": "Transfer within delegated threshold",
            "financial_amount_gtex": 12000.0,
        },
    )
    assert gm_prop.status_code == 200
    assert gm_prop.json()["status"] == "auto_approved"
    assert gm_prop.json()["requires_owner_approval"] is False

    # --------------------------------------------------------------------------
    # Scenario 4: A manager attempting an unauthorised financial decision
    # --------------------------------------------------------------------------
    ftm_prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "operational_expenditure",
            "proposed_by_role": "first_team_manager",
            "title": "Tactics Analytics Suite",
            "summary": "Unauthorized manager expenditure",
            "financial_amount_gtex": 35000.0,
        },
    )
    assert ftm_prop.status_code == 200
    assert ftm_prop.json()["status"] == "pending_approval"
    assert ftm_prop.json()["requires_owner_approval"] is True

    # --------------------------------------------------------------------------
    # Scenario 5: An employee whose delegation has been revoked (owner_only)
    # --------------------------------------------------------------------------
    client.put(
        f"/api/owner/clubs/{club_id}/authority/activity",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "training_and_coaching",
            "responsible_role": "first_team_manager",
            "authority_level": "owner_only",
            "requires_owner_approval": True,
        },
    )
    eval_revoked = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "training_and_coaching",
            "proposed_by_role": "first_team_manager",
        },
    )
    assert eval_revoked.status_code == 200
    assert eval_revoked.json()["allowed"] is False
    assert eval_revoked.json()["requires_approval"] is True

    # --------------------------------------------------------------------------
    # Scenario 6: A staff member attempting to exceed an approval threshold
    # --------------------------------------------------------------------------
    over_limit_prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "title": "Record Transfer Signing",
            "summary": "Exceeds 25,000 GTX threshold",
            "financial_amount_gtex": 75000.0,
        },
    )
    assert over_limit_prop.status_code == 200
    assert over_limit_prop.json()["status"] == "pending_approval"
    assert over_limit_prop.json()["requires_owner_approval"] is True
    assert "exceeds delegated limit" in over_limit_prop.json()["approval_reason"]
    over_limit_decision_id = over_limit_prop.json()["decision_id"]

    # --------------------------------------------------------------------------
    # Scenario 7: Two users attempting conflicting approvals (409 Conflict)
    # --------------------------------------------------------------------------
    first_res = client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{over_limit_decision_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"action": "approve", "decision_note": "Approved by Owner"},
    )
    assert first_res.status_code == 200
    assert first_res.json()["status"] == "approved"

    second_res = client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{over_limit_decision_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"action": "reject", "decision_note": "Late conflicting decision"},
    )
    assert second_res.status_code == 409
    assert "already resolved" in second_res.text

    # --------------------------------------------------------------------------
    # Scenario 8: An expired temporary override
    # --------------------------------------------------------------------------
    # Apply override with past expiration date
    client.post(
        f"/api/owner/clubs/{club_id}/authority/override",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "commercial_partnerships",
            "override_role": "owner",
            "reason": "Temporary commercial takeover",
            "expires_at_iso": "2020-01-01T00:00:00Z",
        },
    )
    # Authority evaluation automatically detects expiration, prunes override, returns active
    eval_exp = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "commercial_partnerships",
            "proposed_by_role": "general_manager",
        },
    )
    assert eval_exp.status_code == 200
    assert eval_exp.json()["policy_status"] == "active"

    # --------------------------------------------------------------------------
    # Scenario 9: An owner exercising a reserved decision
    # --------------------------------------------------------------------------
    eval_reserved_owner = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "staff_recruitment_dismissal",
            "proposed_by_role": "owner",
        },
    )
    assert eval_reserved_owner.status_code == 200
    assert eval_reserved_owner.json()["allowed"] is True
    assert eval_reserved_owner.json()["requires_approval"] is False

    eval_reserved_gm = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "staff_recruitment_dismissal",
            "proposed_by_role": "general_manager",
        },
    )
    assert eval_reserved_gm.status_code == 200
    assert eval_reserved_gm.json()["requires_approval"] is True

    # --------------------------------------------------------------------------
    # Scenario 10: Role spoofing prevention in request payload (403 Forbidden)
    # --------------------------------------------------------------------------
    spoof_prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=other_user["headers"],
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "owner",
            "title": "Spoofed Owner Action",
            "summary": "Attacker attempting to act as owner",
            "financial_amount_gtex": 1000.0,
        },
    )
    assert spoof_prop.status_code == 403
    assert "role spoofing" in spoof_prop.text.lower() or "forbidden" in spoof_prop.text.lower()

    # --------------------------------------------------------------------------
    # Financial Balance Non-Mutation Invariant Check
    # --------------------------------------------------------------------------
    from app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry
    from sqlalchemy import func

    with app.state.session_factory() as session:
        ledger_count_before = (
            session.scalar(
                select(func.count(ClubFinanceLedgerEntry.id)).where(ClubFinanceLedgerEntry.club_id == club_id)
            )
            or 0
        )

    # Propose and resolve an approved decision of 15,000 GTX
    prop_fin = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "facilities_infrastructure",
            "proposed_by_role": "general_manager",
            "title": "Facility Maintenance",
            "summary": "Infrastructure spend",
            "financial_amount_gtex": 15000.0,
        },
    )
    assert prop_fin.status_code == 200
    fin_dec_id = prop_fin.json()["decision_id"]

    client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{fin_dec_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"action": "approve"},
    )

    with app.state.session_factory() as session:
        ledger_count_after = (
            session.scalar(
                select(func.count(ClubFinanceLedgerEntry.id)).where(ClubFinanceLedgerEntry.club_id == club_id)
            )
            or 0
        )
        # Authoritative invariant: Authority Engine does NOT mutate financial balances or generate ledger entries
        assert ledger_count_before == ledger_count_after

    # --------------------------------------------------------------------------
    # Decision Audit Log Immutability & Competence Advisory Isolation
    # --------------------------------------------------------------------------
    hist_resp = client.get(
        f"/api/owner/clubs/{club_id}/authority/decisions",
        headers=bootstrap_admin_headers,
    )
    assert hist_resp.status_code == 200
    decs = hist_resp.json()["decisions"]
    assert len(decs) >= 3

    for d in decs:
        impact = d.get("staff_impact") or {}
        if impact:
            assert impact.get("is_informational_only") is True
            assert "advisory_notice" in impact


def test_decision_audit_trail_append_only_integrity(client, bootstrap_admin_headers, app):
    """Verifies that decision resolution creates immutable append-only audit trail logs."""
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Ibadan")

    # 1. Propose decision
    prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "player_recruitment",
            "proposed_by_role": "general_manager",
            "title": "International Winger Scout & Sign",
            "summary": "Transfer proposal requiring owner signoff.",
            "financial_amount_gtex": 35000.0,
        },
    )
    assert prop.status_code == 200
    decision_id = prop.json()["decision_id"]

    # 2. Check initial audit trail
    trail_resp1 = client.get(
        f"/api/owner/clubs/{club_id}/authority/decisions/{decision_id}/audit-trail",
        headers=bootstrap_admin_headers,
    )
    assert trail_resp1.status_code == 200
    trail1 = trail_resp1.json()["audit_trail"]
    assert len(trail1) == 1
    assert trail1[0]["action"] == "proposed"
    assert trail1[0]["previous_status"] is None
    assert trail1[0]["new_status"] == "pending_approval"
    assert trail1[0]["snapshot"]["title"] == "International Winger Scout & Sign"

    # Simulate an escalation transition before owner resolution so the audit
    # records the actual prior state rather than assuming pending_approval.
    with app.state.session_factory() as session:
        escalated = session.get(ClubDelegatedDecision, decision_id)
        escalated.status = "escalated"
        session.commit()

    # 3. Resolve decision (Approve)
    res = client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{decision_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"action": "approve", "decision_note": "Approved by Board for strategic expansion."},
    )
    assert res.status_code == 200

    # 4. Check audit trail after resolution
    trail_resp2 = client.get(
        f"/api/owner/clubs/{club_id}/authority/decisions/{decision_id}/audit-trail",
        headers=bootstrap_admin_headers,
    )
    assert trail_resp2.status_code == 200
    trail2 = trail_resp2.json()["audit_trail"]
    assert len(trail2) == 2
    # Verify original proposal entry was preserved unchanged
    assert trail2[0]["action"] == "proposed"
    assert trail2[0]["new_status"] == "pending_approval"
    # Verify resolution entry appended
    assert trail2[1]["action"] == "resolved_approve"
    assert trail2[1]["previous_status"] == "escalated"
    assert trail2[1]["new_status"] == "approved"
    assert "strategic expansion" in trail2[1]["decision_note"]


def test_approval_authorisation_distinguished_from_financial_execution(client, bootstrap_admin_headers, app):
    """
    Verifies that approval authorization does not mark financial execution,
    and execution is explicitly recorded only when the authoritative domain service executes.
    """
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Enugu")

    # Propose
    prop = client.post(
        f"/api/owner/clubs/{club_id}/authority/propose",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "operational_expenditure",
            "proposed_by_role": "general_manager",
            "title": "GPS Tracking Vests",
            "summary": "Hardware upgrade for squad monitoring",
            "financial_amount_gtex": 18000.0,
        },
    )
    assert prop.status_code == 200
    dec_id = prop.json()["decision_id"]

    # Resolve (Approve authorization)
    res = client.post(
        f"/api/owner/clubs/{club_id}/authority/decisions/{dec_id}/resolve",
        headers=bootstrap_admin_headers,
        json={"action": "approve"},
    )
    assert res.status_code == 200
    assert "Pending execution" in res.json()["outcome_text"]

    # Verify decision record in DB has execution_status="pending_execution"
    with app.state.session_factory() as session:
        dec = session.get(ClubDelegatedDecision, dec_id)
        assert dec.status == "approved"
        assert dec.execution_status == "pending_execution"

        # Authoritative domain service executes the transaction
        delegation_service.mark_decision_executed(
            session,
            club_id=club_id,
            decision_id=dec_id,
            transaction_id="tx_gps_vests_9921",
            executor_user_id=dec.owner_user_id,
        )

        dec_after = session.get(ClubDelegatedDecision, dec_id)
        assert dec_after.execution_status == "executed"
        assert "tx_gps_vests_9921" in dec_after.outcome_text


def test_staff_competence_real_appointed_staff_records(client, bootstrap_admin_headers, app):
    """Verifies competence calculations use the actual appointed staff records when available."""
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Calabar")

    # Appoint custom elite manager with specific attributes
    with app.state.session_factory() as session:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        state.manager_json = {
            "manager_id": "mgr_elite_007",
            "name": "Don Carlo Ancelotti",
            "rating": 89,
            "tactical_rating": 89,
            "tactical_flexibility": 19,
            "style": "possession",
            "is_default": False,
        }
        session.commit()

    # Authority evaluation for first team tactics
    eval_resp = client.post(
        f"/api/owner/clubs/{club_id}/authority/evaluate",
        headers=bootstrap_admin_headers,
        json={
            "activity_key": "first_team_tactics",
            "proposed_by_role": "first_team_manager",
        },
    )
    assert eval_resp.status_code == 200
    res = eval_resp.json()

    assert res["staff_name"] == "Don Carlo Ancelotti"
    assert res["staff_competence_rating"] == 89
    impact = res["staff_impact"]
    assert impact["is_appointed_staff"] is True
    assert impact["tactical_synergy_boost"] == 19
    assert impact["morale_boost"] == 2
    assert "actual appointed staff attributes" in impact["scoring_methodology"]
