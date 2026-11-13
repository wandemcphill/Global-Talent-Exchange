"""GTEX Living Football World - Stage 8
End-to-End Integration, Quality & Acceptance Suite (Scenarios A through I).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.models.base import Base
from app.models.club_growth import (
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
)
from app.models.club_profile import ClubProfile
from app.models.event_backbone import EventOutbox
from app.models.risk_ops import AuditLog
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
)
from app.models.world_clock import WorldClockState
from app.owner_console import (
    ledger,
    living_cinema_showroom,
    living_club_world,
    living_gm_delegation,
    living_politics_engine,
    living_staff_market,
    money,
    router as owner_router,
    service,
    storytelling,
)
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    ClubDelegatedDecision,
    OwnerClubEvent,
    OwnerClubState,
    OwnerShowroomAsset,
    OwnerSquadPlayer,
)

WORLD_NOW = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
DEFAULT_CLOCK_ID = "00000000-0000-0000-0000-000000000001"


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
            LedgerAccount.__table__,
            LedgerBalanceProjection.__table__,
            LedgerEntry.__table__,
            LedgerTransaction.__table__,
            WorldClockState.__table__,
            ClubStaffProfile.__table__,
            ClubStaffContract.__table__,
            ClubStaffAssignment.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    session = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)()
    session.add(
        WorldClockState(
            id=DEFAULT_CLOCK_ID,
            epoch_real_utc=WORLD_NOW,
            virtual_start_time=WORLD_NOW,
            progression_rate=1.0,
            is_paused=False,
            paused_at_virtual_time=None,
            virtual_months_per_season=12,
            metadata_json={"canonical": True},
        )
    )
    session.commit()
    return session


def _bootstrap_club(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    prestige: int = 72,
    cash_gtex: int = 250000,
    with_user: User | None = None,
) -> tuple[User, ClubProfile, OwnerClubState]:
    if with_user is None:
        u = User(
            id=user_id,
            email=f"{user_id}@gtex.test",
            username=f"owner_{user_id}",
            password_hash="synthetic_hash",  # pragma: allowlist secret
            role="authenticated",
            is_active=True,
        )
        session.add(u)
    else:
        u = with_user

    cp = ClubProfile(
        id=club_id,
        owner_user_id=u.id,
        club_name=f"Atlantic FC ({club_id})",
        slug=f"atlantic-fc-{club_id}",
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
    )
    session.add(cp)
    session.flush()

    state = OwnerClubState(
        id=club_id,
        club_id=club_id,
        owner_user_id=u.id,
        club_name=cp.club_name,
        stage="active",
        prestige=prestige,
        mentality="balanced",
        world_day=18,
        facilities_json={
            "training": 3,
            "academy": 3,
            "medical": 3,
            "stadium": 3,
            "commercial": 2,
            "_executive_staff": {
                "general_manager": {
                    "id": f"gm_{club_id}",
                    "staff_id": f"gm_{club_id}",
                    "name": "Dayo Adeleke",
                    "role": "general_manager",
                    "role_label": "General Manager",
                    "rating": 84,
                    "salary_gtex": 1800,
                    "mood": 82,
                    "is_appointed": True,
                },
                "medical_director": {
                    "id": f"med_{club_id}",
                    "staff_id": f"med_{club_id}",
                    "name": "Dr. Chidi Obi",
                    "role": "medical_director",
                    "role_label": "Medical Director",
                    "rating": 83,
                    "salary_gtex": 1200,
                    "mood": 80,
                    "is_appointed": True,
                },
                "head_of_youth_development": {
                    "id": f"hoyd_{club_id}",
                    "staff_id": f"hoyd_{club_id}",
                    "name": "Kunle Adeyemi",
                    "role": "head_of_youth_development",
                    "role_label": "Head of Youth Development",
                    "rating": 81,
                    "salary_gtex": 1100,
                    "mood": 79,
                    "is_appointed": True,
                },
            },
        },
        manager_json={
            "id": f"mgr_{club_id}",
            "staff_id": f"mgr_{club_id}",
            "name": "Emmanuel Amuneke",
            "display_name": "Emmanuel Amuneke",
            "role": "first_team_manager",
            "rating": 85,
            "salary": 2400,
            "salary_gtex": 2400,
            "formation": "4-3-3",
            "style": "High-Press Possession",
            "loyalty": 14,
            "is_default": False,
            "is_vacant": False,
        },
    )
    session.add(state)
    session.flush()

    living_staff_market.ensure_staff_market_profiles(session)
    ledger.record(
        session,
        event_type="capital_injection",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=Decimal(str(cash_gtex)),
        user_id=u.id,
        club_id=club_id,
        memo="Stage 8 E2E seed treasury",
    )
    ledger.record(
        session,
        event_type="test_club_fan_funding",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.FAN,
        gross=Decimal(str(cash_gtex)),
        user_id=u.id,
        club_id=club_id,
        memo="Stage 8 E2E Fan Coin salary purse",
        check_funds=False,
    )
    session.commit()
    return u, cp, state


# ==============================================================================
# Scenario A — Owner and Manager Tactical Disagreement & Counter-Proposal
# ==============================================================================
def test_scenario_a_owner_manager_tactical_disagreement_and_counter_proposal():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_a", "c_scen_a")

    # 1. Owner proposes a radical tactical shift (3-4-3 attacking) under full_autonomy
    first_res = living_club_world.propose_tactical_adjustment(
        session,
        u.id,
        cp.id,
        proposed_formation="3-4-3",
        proposed_mentality="attacking",
        autonomy_mode="full_autonomy",
        rationale="Switch to ultra-attacking 3-4-3 immediately",
    )
    session.commit()

    assert first_res["status"] == "rejected"
    assert first_res["implemented"] is False
    assert first_res["effective_tactics"]["formation"] == "4-3-3"
    assert first_res["effective_tactics"]["mentality"] == "balanced"
    assert first_res["counter_proposal"] is not None
    counter_form = first_res["counter_proposal"]["formation"]
    counter_ment = first_res["counter_proposal"]["mentality"]

    # Verify relationship changed (tension rose, trust dropped)
    rel_after_reject = first_res["relationship"]
    assert rel_after_reject is not None
    assert rel_after_reject["tension"] > 15

    # 2. Owner accepts the manager's counter-proposal
    second_res = living_club_world.propose_tactical_adjustment(
        session,
        u.id,
        cp.id,
        proposed_formation=counter_form,
        proposed_mentality=counter_ment,
        autonomy_mode="consultative",
        accept_counter_proposal=True,
        rationale="Agreed on manager counter-proposal",
    )
    session.commit()

    assert second_res["status"] == "accepted"
    assert second_res["implemented"] is True
    assert second_res["effective_tactics"]["formation"] == counter_form
    assert second_res["effective_tactics"]["mentality"] == counter_ment

    # Re-read authoritative database state and verify tactical update + event history
    refreshed = session.get(OwnerClubState, cp.id)
    assert refreshed is not None
    assert (refreshed.manager_json or {}).get("formation") == counter_form
    assert refreshed.mentality == counter_ment

    tactical_events = list(
        session.scalars(
            select(OwnerClubEvent).where(
                OwnerClubEvent.club_id == cp.id,
                OwnerClubEvent.category == "tactical",
            )
        ).all()
    )
    event_types = {e.event_type for e in tactical_events}
    assert "tactical_proposal_rejected" in event_types
    assert "tactical_proposal_implemented" in event_types


# ==============================================================================
# Scenario B — Dismissed Manager Finds a New Club & Triggers Arrival Cinematic
# ==============================================================================
def test_scenario_b_dismissed_manager_finds_new_club_and_triggers_arrival_cinematic():
    session = _session()
    u_a, cp_a, _ = _bootstrap_club(session, "u_scen_b1", "c_scen_b_club_a", prestige=75, cash_gtex=300000)
    u_b, cp_b, state_b = _bootstrap_club(session, "u_scen_b2", "c_scen_b_club_b", prestige=85, cash_gtex=300000)

    # First hire a canonical market manager into Club A so they have an active tenure
    initial_cands = living_staff_market.list_staff_market_candidates(
        session, u_a.id, cp_a.id, role="first_team_manager", employment_status="unemployed"
    )["candidates"]
    target_mgr = initial_cands[0]
    living_staff_market.hire_staff_from_market(
        session=session,
        user_id=u_a.id,
        club_id=cp_a.id,
        profile_id=target_mgr["profile_id"],
        role="first_team_manager",
        offered_salary_gtex=target_mgr["expected_salary_gtex"] + 500,
        contract_years=2,
        marquee_wage_premium=True,
    )
    session.commit()

    # Make First-Team Manager vacant at Club B
    state_b.manager_json = {"is_vacant": True, "is_default": True}
    session.commit()

    # 1. Dismiss manager from Club A
    dismiss_res = living_staff_market.dismiss_staff_with_free_agency(
        session,
        u_a.id,
        cp_a.id,
        role="first_team_manager",
        reason="Tactical direction change",
    )
    session.commit()

    assert dismiss_res["status"] == "dismissed"
    assert dismiss_res["entered_free_agency"] is True
    assert dismiss_res["severance_paid"] > 0
    dismissed_profile_id = dismiss_res["profile_id"]

    # 2. Club B checks vacancies and candidate pool
    vacancies_b = living_staff_market.get_club_vacancies(session, u_b.id, cp_b.id)
    assert any(v["role_key"] == "first_team_manager" for v in vacancies_b["vacancies"])

    pool_b = living_staff_market.list_staff_market_candidates(
        session,
        u_b.id,
        cp_b.id,
        role="first_team_manager",
        employment_status="unemployed",
    )
    rehired_cand = next(
        (c for c in pool_b["candidates"] if c["profile_id"] == dismissed_profile_id),
        None,
    )
    assert rehired_cand is not None
    assert rehired_cand["employment_status"] == "unemployed"
    assert len(rehired_cand["career_history"]) >= 1

    # 3. Club B hires the dismissed manager and triggers 3D arrival cinematic
    hire_res = living_staff_market.hire_staff_from_market(
        session=session,
        user_id=u_b.id,
        club_id=cp_b.id,
        profile_id=dismissed_profile_id,
        role="first_team_manager",
        offered_salary_gtex=rehired_cand["expected_salary_gtex"] + 500,
        contract_years=3,
        marquee_wage_premium=True,
    )
    session.commit()

    assert hire_res["status"] == "accepted"
    assert hire_res["success"] is True
    assert hire_res["cinematic_event"] is not None
    assert hire_res["cinematic_event"]["event_type"] == "manager_arrival"
    assert hire_res["cinematic_event"]["scene_id"] == "manager_arrival"
    assert hire_res["cinematic_event"]["verified_transaction"] is True


# ==============================================================================
# Scenario C — Owner Delegates to GM Within Approved Authority
# ==============================================================================
def test_scenario_c_owner_delegates_to_gm_within_authority():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_c", "c_scen_c", prestige=80, cash_gtex=300000)

    # Configure GM-led delegation with generous staff salary limit
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "gm_led")
    living_gm_delegation.update_gm_matrix_and_financial_controls(
        session,
        u.id,
        cp.id,
        financial_controls={
            "max_expenditure_unapproved_gtex": 15000.0,
            "max_staff_salary_unapproved_gtex": 5000.0,
        },
    )
    session.commit()

    # Run GM operational cycle to fill Chief Scout vacancy autonomously
    cycle_res = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)
    session.commit()

    assert cycle_res["executed_actions_count"] >= 1
    decisions = list(session.scalars(select(ClubDelegatedDecision).where(ClubDelegatedDecision.club_id == cp.id)).all())
    assert len(decisions) >= 1


# ==============================================================================
# Scenario D — GM Exceeds Authority & Action Is Escalated for Owner Approval
# ==============================================================================
def test_scenario_d_gm_exceeds_authority_escalated_to_owner():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_d", "c_scen_d", prestige=80, cash_gtex=300000)

    # Configure balanced mode with a strict 500 GTEX salary cap so staff hiring escalates
    living_gm_delegation.update_gm_delegation_mode(session, u.id, cp.id, "balanced")
    living_gm_delegation.update_gm_matrix_and_financial_controls(
        session,
        u.id,
        cp.id,
        financial_controls={
            "max_staff_salary_unapproved_gtex": 500.0,
            "max_expenditure_unapproved_gtex": 500.0,
        },
    )
    session.commit()

    cash_before = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    cycle_res = living_gm_delegation.evaluate_gm_operational_cycle(session, u.id, cp.id)
    session.commit()
    cash_after = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)

    # No unauthorized transaction occurred; proposal escalated for owner approval
    assert cash_after == cash_before
    assert cycle_res["escalated_proposals_count"] >= 1
    esc = cycle_res["escalated_proposals"][0]
    assert "Exceeds authorized" in esc["reason"] or "ratification" in esc["reason"]


# ==============================================================================
# Scenario E — Medical Director and Manager Disagreement Over Injured Star
# ==============================================================================
def test_scenario_e_medical_director_and_manager_disagreement():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_e", "c_scen_e", prestige=75)

    star = OwnerSquadPlayer(
        id="p_star_scen_e",
        club_id=cp.id,
        name="Victor Osimhen II",
        position="ST",
        age=24,
        rating=86,
        potential=90,
        value_coin=Decimal("120000"),
        morale=76,
        minutes=800,
        injured_days=5,
        is_regen=True,
        personality_json={"fitness": 58, "leadership": 15},
    )
    session.add(star)
    session.commit()

    eval_res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)
    session.commit()

    med_event_id = next((e["id"] for e in eval_res["new_events"] if e["type"] == "medical"), None)
    assert med_event_id is not None

    # Resolve by backing medical protocol -> authoritative injury restriction remains enforced
    res = living_politics_engine.resolve_political_event(
        session,
        u.id,
        cp.id,
        event_id=med_event_id,
        action_id="back_medical",
        note="Follow full rehabilitation protocol",
    )
    session.commit()

    assert res["success"] is True
    assert res["action_taken"] == "back_medical"
    assert "Protected under full recovery protocol" in res["delta_report"]["player_injury_status"]
    refreshed_star = session.get(OwnerSquadPlayer, star.id)
    assert refreshed_star is not None
    assert refreshed_star.injured_days == 5


# ==============================================================================
# Scenario F — HOYD and Manager Disagree on Academy Prospect & Promotion
# ==============================================================================
def test_scenario_f_hoyd_and_manager_academy_disagreement_and_promotion():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_f", "c_scen_f", prestige=75)

    wonderkid = OwnerSquadPlayer(
        id="p_wonderkid_scen_f",
        club_id=cp.id,
        name="Kelechi Nwakali Jr",
        position="CAM",
        age=17,
        rating=76,
        potential=91,
        value_coin=Decimal("65000"),
        morale=72,
        minutes=40,
        injured_days=0,
        is_regen=True,
        personality_json={"squad_status": "academy", "face_bank_id": "fb_regen_99"},
    )
    session.add(wonderkid)
    session.commit()

    # Evaluate political cycle -> detects academy pathway disagreement
    eval_res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)
    session.commit()
    assert eval_res["events_evaluated"] >= 1

    # Promote academy player through the canonical service
    promo_res = service.academy_promote(session, u.id, cp.id, wonderkid.id)
    session.commit()
    assert promo_res["status"] == "promoted"
    assert promo_res["squad_status"] == "senior"

    # Trigger verified 3D academy wonderkid presentation preserving regen identity
    cin_res = living_cinema_showroom.trigger_verified_club_cinematic(
        session,
        u.id,
        cp.id,
        event_type="academy_wonderkid",
        subject_id=wonderkid.id,
    )
    session.commit()
    assert cin_res["cinematic_event"]["event_type"] == "academy_wonderkid"
    assert cin_res["cinematic_event"]["subject_id"] == wonderkid.id
    assert cin_res["cinematic_event"]["is_regen"] is True


# ==============================================================================
# Scenario G — Locker-Room Captain Grievance & Squad Morale Resolution
# ==============================================================================
def test_scenario_g_locker_room_captain_grievance_and_morale_resolution():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_g", "c_scen_g", prestige=70, cash_gtex=250000)

    p_capt = OwnerSquadPlayer(
        id="p_capt_scen_g",
        club_id=cp.id,
        name="William Troost-Ekong II",
        position="CB",
        age=29,
        rating=80,
        potential=81,
        value_coin=Decimal("55000"),
        morale=78,
        minutes=900,
        injured_days=0,
        is_regen=False,
        personality_json={"leadership": 19, "is_captain": True},
    )
    p_unhappy = OwnerSquadPlayer(
        id="p_unhappy_scen_g",
        club_id=cp.id,
        name="Alex Iwobi II",
        position="CM",
        age=24,
        rating=78,
        potential=82,
        value_coin=Decimal("50000"),
        morale=44,
        minutes=90,
        injured_days=0,
        is_regen=False,
        personality_json={"leadership": 14},
    )
    session.add_all([p_capt, p_unhappy])
    session.commit()

    eval_res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)
    session.commit()

    squad_event_id = next((e["id"] for e in eval_res["new_events"] if e["type"] == "squad"), None)
    assert squad_event_id is not None

    resolve_res = living_politics_engine.resolve_political_event(
        session,
        u.id,
        cp.id,
        event_id=squad_event_id,
        action_id="pledge_rotation",
        note="Guaranteed squad rotation opportunities",
    )
    session.commit()

    assert resolve_res["success"] is True
    refreshed_unhappy = session.get(OwnerSquadPlayer, p_unhappy.id)
    assert refreshed_unhappy is not None
    assert refreshed_unhappy.morale == 56  # 44 + 12


# ==============================================================================
# Scenario H — Continuous Year-Round Player Market (No Transfer Window Locks)
# ==============================================================================
def test_scenario_h_continuous_year_round_player_market_no_transfer_window_locks():
    session = _session()
    u, cp_1, state_1 = _bootstrap_club(session, "u_scen_h", "c_scen_h1", cash_gtex=50000)
    _, cp_2, state_2 = _bootstrap_club(session, "u_scen_h", "c_scen_h2", cash_gtex=50000, with_user=u)

    # Create three players transferred at different points of the calendar year (Day 45, Day 190, Day 310)
    for idx, world_day in enumerate((45, 190, 310), start=1):
        state_1.world_day = world_day
        state_2.world_day = world_day
        player = OwnerSquadPlayer(
            id=f"p_cont_{idx}",
            club_id=cp_1.id,
            player_ref=f"ref_cont_{idx}",
            name=f"Continuous Market Player {idx}",
            position="MID",
            age=23,
            rating=75,
            potential=82,
            value_coin=Decimal("2000"),
            morale=75,
            status="active",
        )
        session.add(player)
        session.commit()

        check = money.check_internal_transfer(session, u.id, player.id, cp_2.id, Decimal("2000"))
        assert check["allowed"] is True
        assert "transfer_window_open" not in check["rules"]

        res = money.internal_transfer(session, u.id, player.id, cp_2.id, Decimal("2000"))
        session.commit()
        assert res["player_id"] == player.id
        assert res["to_club_id"] == cp_2.id

        moved = session.get(OwnerSquadPlayer, player.id)
        assert moved is not None
        assert moved.club_id == cp_2.id


# ==============================================================================
# Scenario I — Prestige Asset Purchase, Idempotency & 3D Turntable Presentation
# ==============================================================================
def test_scenario_i_prestige_asset_purchase_idempotency_and_3d_presentation():
    session = _session()
    u, cp, _ = _bootstrap_club(session, "u_scen_i", "c_scen_i", prestige=75, cash_gtex=40000)

    cash_before = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    idem_key = "stage8-jet-purchase-idem-001"

    # 1. Purchase Sovereign 900X Private Jet
    purchase_1 = storytelling.purchase_showroom_asset(
        session,
        u.id,
        cp.id,
        "sovereign_900x_jet",
        custom_name="Atlantic One Sovereign Jet",
        idempotency_key=idem_key,
    )
    session.commit()
    cash_after_1 = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    assert cash_after_1 == cash_before - Decimal("4800.0")
    assert purchase_1["asset"]["catalog_key"] == "sovereign_900x_jet"

    # 2. Replay with the same idempotency_key -> no duplicate asset, no double debit
    purchase_2 = storytelling.purchase_showroom_asset(
        session,
        u.id,
        cp.id,
        "sovereign_900x_jet",
        custom_name="Atlantic One Sovereign Jet",
        idempotency_key=idem_key,
    )
    session.commit()
    cash_after_2 = ledger.balance(session, ledger.club_account(cp.id), ledger.GTEX)
    assert cash_after_2 == cash_after_1
    assert purchase_2["asset"]["id"] == purchase_1["asset"]["id"]

    owned_rows = list(
        session.scalars(
            select(OwnerShowroomAsset).where(
                OwnerShowroomAsset.club_id == cp.id,
                OwnerShowroomAsset.catalog_key == "sovereign_900x_jet",
            )
        ).all()
    )
    assert len(owned_rows) == 1

    # 3. Verify 3D Showroom Overview and Verified 3D Jet Showcase Cinematic
    overview = living_cinema_showroom.get_cinema_and_showroom_overview(session, u.id, cp.id)
    jet_entry = next(
        (item for item in overview["prestige_3d_catalog"] if item["catalog_key"] == "sovereign_900x_jet"),
        None,
    )
    assert jet_entry is not None
    assert jet_entry["is_owned"] is True
    assert jet_entry["webgl_3d"]["mesh_archetype"] == "private_jet"

    showcase = living_cinema_showroom.trigger_verified_club_cinematic(
        session,
        u.id,
        cp.id,
        event_type="private_jet_showcase",
        asset_catalog_key="sovereign_900x_jet",
    )
    session.commit()
    assert showcase["cinematic_event"]["scene_id"] == "luxury_inspection_turntable"
    assert showcase["cinematic_event"]["verified_transaction"] is True


# ==============================================================================
# Stage 8 Router & Tenancy Isolation End-to-End Verification
# ==============================================================================
def test_stage8_api_routes_and_tenancy_isolation():
    session = _session()
    owner_user, cp, _ = _bootstrap_club(session, "u_owner_s8", "c_club_s8")
    intruder_user = User(
        id="u_intruder_s8",
        email="intruder@gtex.test",
        username="intruder_s8",
        password_hash="synthetic_hash",  # pragma: allowlist secret
        role="authenticated",
        is_active=True,
    )
    session.add(intruder_user)
    session.commit()

    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_session] = lambda: session

    # 1. Authorized owner calls tactical proposal endpoint
    app.dependency_overrides[get_current_user] = lambda: owner_user
    client = TestClient(app)
    resp_ok = client.post(
        f"/owner/clubs/{cp.id}/living-world/tactics/propose",
        json={
            "proposed_formation": "4-2-3-1",
            "proposed_mentality": "attacking",
            "autonomy_mode": "owner_led",
            "rationale": "Press high at home",
        },
    )
    assert resp_ok.status_code == 200
    body = resp_ok.json()
    assert body["status"] == "accepted"
    assert body["implemented"] is True
    assert body["effective_tactics"]["formation"] == "4-2-3-1"

    # 2. Unauthorized user is blocked from mutating another owner's club tactics
    app.dependency_overrides[get_current_user] = lambda: intruder_user
    resp_forbidden = client.post(
        f"/owner/clubs/{cp.id}/living-world/tactics/propose",
        json={
            "proposed_formation": "5-3-2",
            "proposed_mentality": "defensive",
        },
    )
    assert resp_forbidden.status_code in (403, 404)
