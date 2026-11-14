from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.world_clock import WorldClockState
from app.owner_console import (
    autonomous_staff_engine,
    comms_persistence,
    engine as owner_engine,
    ledger,
    service,
)
from app.owner_console.models import (
    ClubDelegatedDecision,
    OwnerClubMeeting,
    OwnerClubRelationship,
    OwnerClubState,
    OwnerRecruitmentAssignment,
    OwnerStaffDecisionRecord,
    OwnerSquadPlayer,
)
from app.owner_console.router import router as owner_router
from app.services.world_clock_service import DEFAULT_CLOCK_ID

from uuid import uuid4

WORLD_NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)

_SHARED_ENGINE = None


def _get_shared_engine():
    global _SHARED_ENGINE
    if _SHARED_ENGINE is None:
        load_model_modules()
        _SHARED_ENGINE = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(_SHARED_ENGINE)
    return _SHARED_ENGINE


def _setup_test_env() -> tuple[Session, TestClient, OwnerClubState]:
    eng = _get_shared_engine()
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    session = factory()

    if session.get(WorldClockState, DEFAULT_CLOCK_ID) is None:
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

    suffix = uuid4().hex[:8]
    owner_id = f"owner-living-{suffix}"
    club_id = f"club-living-{suffix}"

    owner = User(
        id=owner_id,
        email=f"owner.{suffix}@gtex.test",
        username=f"owner_{suffix}",
        display_name="Chairman Adewale",
        password_hash="x",
        role=UserRole.USER,
        account_type=PublicAccountType.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner.id,
        club_name="Atlantic Sporting FC",
        short_name="ASFC",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug=f"atlantic-sporting-fc-{suffix}",
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
        country_code="NG",
        visibility="public",
    )
    state = OwnerClubState(
        club_id=club.id,
        owner_user_id=owner.id,
        club_name=club.club_name,
        stage="active",
        world_day=10,
        prestige=74,
        fans=18000,
        mentality="balanced",
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 3, "academy": 4, "medical": 3, "stadium": 3, "commercial": 3},
    )
    session.add_all([owner, club, state])
    session.flush()

    # Seed club treasury and owner Fan Coin
    ledger.record(
        session,
        event_type="test_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club.id),
        currency=ledger.GTEX,
        gross=850000,
        balance_class="deposited",
        club_id=club.id,
        user_id=owner.id,
        memo="Initial club treasury",
    )
    ledger.record(
        session,
        event_type="test_fan_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.user_account(owner.id),
        currency=ledger.FAN,
        gross=50000,
        club_id=club.id,
        user_id=owner.id,
        memo="Initial fan coin",
    )

    # Seed balanced 16-player squad + 16yo academy striker Lucas Vance
    squad_spec = [
        ("p-gk-1", "Emeka Obi", "GK", 28, 79, 80, False),
        ("p-gk-2", "Tariq Bello", "GK", 21, 71, 79, False),
        ("p-def-1", "Chidi Nwachukwu", "CB", 29, 80, 80, False),
        ("p-def-2", "Kofi Mensah", "CB", 27, 78, 79, False),
        ("p-def-3", "Seyi Balogun", "LB", 25, 77, 80, False),
        ("p-def-4", "Ibrahim Diallo", "RB", 26, 77, 79, False),
        ("p-def-5", "Dapo Afolabi", "CB", 22, 73, 81, False),
        ("p-mid-1", "Yusuf Lawal", "CM", 28, 81, 82, False),
        ("p-mid-2", "Nuno Silva", "CDM", 30, 79, 79, False),
        ("p-mid-3", "Tobi Ojo", "CAM", 24, 78, 83, False),
        ("p-mid-4", "Chuka Eze", "CM", 19, 70, 85, True),
        ("p-mid-5", "Akin Cole", "RM", 26, 76, 78, False),
        ("p-fwd-1", "Victor Okafor", "ST", 29, 82, 82, False),
        ("p-fwd-2", "Samuel Kalu", "LW", 27, 78, 79, False),
        ("p-fwd-3", "Musa Danjuma", "RW", 26, 77, 79, False),
        ("p-acad-st-16", "Lucas Vance", "ST", 16, 67, 89, True),
    ]
    for pid_base, name, pos, age, rtg, pot, is_regen in squad_spec:
        pid = f"{club.id}:{pid_base}" if pid_base != "p-acad-st-16" else f"{club.id}:p-acad-st-16"
        session.add(
            OwnerSquadPlayer(
                id=pid,
                club_id=club.id,
                name=name,
                position=pos,
                age=age,
                rating=rtg,
                potential=pot,
                value_coin=Decimal(str(rtg * 15)),
                morale=80,
                minutes=180 if not is_regen else 15,
                injured_days=0,
                is_regen=is_regen,
                personality_json={"fitness": 94, "is_academy": is_regen, "ambition": 16, "professionalism": 15},
                status="active",
                acquired_via="academy" if is_regen else "market",
            )
        )
    session.commit()

    app = FastAPI()
    app.include_router(owner_router)

    def _override_session() -> Iterator[Session]:
        yield session

    def _override_user() -> User:
        return session.get(User, owner_id)

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    client = TestClient(app)
    return session, client, state


_ARCHETYPE_DEFAULT_NAMES = {
    "youth_development_visionary": "Marco Bellini",
    "veteran_pragmatist": "Viktor Krall",
    "balanced_collaborator": "Julian Vance",
    "high_pressing_autocrat": "Lukas Richter",
    "possession_architect": "Mateo Alcaraz",
}


def _assign_manager_archetype(session: Session, state: OwnerClubState, archetype_key: str) -> dict:
    mgr_template = dict(autonomous_staff_engine.MANAGER_ARCHETYPES[archetype_key])
    mgr_name = _ARCHETYPE_DEFAULT_NAMES.get(archetype_key, mgr_template["archetype_label"])
    mgr_json = {
        "id": f"mgr_{archetype_key}",
        "manager_id": f"mgr_{archetype_key}",
        "name": mgr_name,
        "display_name": mgr_name,
        "archetype_key": archetype_key,
        "mood": 78,
        "loyalty": mgr_template["loyalty"] // 5,
        "youth_development": max(5, mgr_template["youth_development_commitment"] // 5),
        "tactical_flexibility": max(5, mgr_template["tactical_flexibility"] // 5),
        "personality_profile": dict(mgr_template),
    }
    state.manager_json = mgr_json
    flag_modified(state, "manager_json")
    fac = dict(state.facilities_json or {})
    fac.pop("_manager_matchday_commitments", None)
    fac.pop("_manager_matchday_rejections", None)
    state.facilities_json = fac
    flag_modified(state, "facilities_json")
    session.commit()
    return mgr_json


def test_scenarios_a_b_c_manager_independence_on_academy_striker_selection() -> None:
    """Scenarios A, B, and C:
    Verify three distinct outcomes for the exact same owner request ('I want to see our 16-year-old
    academy striker in the next match. I think he deserves an opportunity.') across:
    - Manager A (`youth_development_visionary` - Marco Bellini): accepts and selects Lucas Vance.
    - Manager B (`veteran_pragmatist` - Viktor Krall): declines and protects senior selection.
    - Manager C (`balanced_collaborator` - Julian Vance): partially accepts (substitute bench role).
    """
    session, client, state = _setup_test_env()
    try:
        prompt = "I want to see our 16-year-old academy striker in the next match. I think he deserves an opportunity."
        acad_id = f"{state.club_id}:p-acad-st-16"
        senior_st_id = f"{state.club_id}:p-fwd-1"

        # --- SCENARIO A: Youth-oriented Manager (Marco Bellini) ---
        _assign_manager_archetype(session, state, "youth_development_visionary")
        res_a = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "staff:first_team_manager", "message": prompt, "topic": "Academy Opportunity"},
        )
        assert res_a.status_code == 200
        body_a = res_a.json()
        assert body_a["decision_record"]["decision_outcome"] == "accepted"
        assert body_a["decision_record"]["request_intent"] == "academy_player_opportunity"
        assert "Lucas Vance" in body_a["reply"]["body"]

        sel_a = client.get(f"/owner/clubs/{state.club_id}/matchday-selection").json()
        assert acad_id in sel_a["starting_xi_ids"] or acad_id in sel_a["bench_ids"]

        # --- SCENARIO B: Conservative Veteran-Preferring Manager (Viktor Krall) ---
        _assign_manager_archetype(session, state, "veteran_pragmatist")
        res_b = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "staff:first_team_manager", "message": prompt, "topic": "Academy Opportunity"},
        )
        assert res_b.status_code == 200
        body_b = res_b.json()
        assert body_b["decision_record"]["decision_outcome"] == "declined"
        assert "not believe he is ready" in body_b["reply"]["body"].lower() or "develop" in body_b["reply"]["body"].lower()

        sel_b = client.get(f"/owner/clubs/{state.club_id}/matchday-selection").json()
        assert acad_id not in sel_b["starting_xi_ids"]
        assert senior_st_id in sel_b["starting_xi_ids"]

        # --- SCENARIO C: Balanced Manager (Julian Vance) ---
        _assign_manager_archetype(session, state, "balanced_collaborator")
        res_c = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "staff:first_team_manager", "message": prompt, "topic": "Academy Opportunity"},
        )
        assert res_c.status_code == 200
        body_c = res_c.json()
        assert body_c["decision_record"]["decision_outcome"] == "partially_accepted"
        assert "substitute" in body_c["reply"]["body"].lower() or "bench" in body_c["reply"]["body"].lower()

        sel_c = client.get(f"/owner/clubs/{state.club_id}/matchday-selection").json()
        assert acad_id in sel_c["bench_ids"]
        assert senior_st_id in sel_c["starting_xi_ids"]
    finally:
        session.close()


def test_scenario_d_repeated_owner_interference_escalates_to_ultimatum_and_resignation() -> None:
    """Scenario D:
    Repeated owner interference on team selection against a fiercely independent manager
    increases tension, reduces trust/autonomy across the 9 relationship dimensions, and
    escalates through `formal_disagreement`, `ultimatum`, and `resignation_notice`.
    """
    session, client, state = _setup_test_env()
    try:
        _assign_manager_archetype(session, state, "veteran_pragmatist")
        outcomes: list[str] = []
        last_payload: dict = {}
        for idx in range(1, 5):
            res = client.post(
                f"/owner/clubs/{state.club_id}/communications/messages",
                json={
                    "thread_id": "staff:first_team_manager",
                    "message": f"I am overriding you ({idx}): start our 16-year-old academy striker Lucas Vance in the next match.",
                    "topic": "Selection Override",
                },
            )
            assert res.status_code == 200
            last_payload = res.json()
            outcomes.append(last_payload["decision_record"]["decision_outcome"])

        assert "formal_disagreement" in outcomes
        assert "ultimatum" in outcomes
        assert outcomes[-1] == "resignation_notice"

        mgr_rel_at_resignation = last_payload["decision_record"]["relationship_snapshot"]
        assert mgr_rel_at_resignation["tension"] >= 45
        assert mgr_rel_at_resignation["autonomy"] < 92
        assert mgr_rel_at_resignation["interference_count"] >= 4
        assert mgr_rel_at_resignation["resignation_notice_served"] is True
    finally:
        session.close()


def test_scenario_e_gm_and_chief_scout_recruitment_workflow_and_counterproposal() -> None:
    """Scenario E:
    Owner asks the General Manager to sign a left winger with a GSI between 80 and 85.
    Verify GM coordinates with Chief Scout, persists `OwnerRecruitmentAssignment`, posts shortlist
    to Staff Technical Room, and counterproposes a younger value alternative when budget/risk is tight.
    """
    session, client, state = _setup_test_env()
    try:
        # 1. Ambitious GM with ample budget accepts / conditionally accepts and creates shortlist
        fac = dict(state.facilities_json or {})
        exec_staff = dict(fac.get("_executive_staff") or {})
        exec_staff["general_manager"] = {
            "id": "gm_ambitious_1",
            "name": "Damian Cross",
            "role": "general_manager",
            "archetype_key": "ambitious_squad_architect",
            "personality_profile": dict(autonomous_staff_engine.GM_ARCHETYPES["ambitious_squad_architect"]),
        }
        fac["_executive_staff"] = exec_staff
        state.facilities_json = fac
        flag_modified(state, "facilities_json")
        session.commit()

        res1 = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:general_manager",
                "message": "I want us to sign a left winger with a GSI between 80 and 85.",
                "topic": "Transfer Target",
            },
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["decision_record"]["request_intent"] == "transfer_recruitment_target"
        assert data1["decision_record"]["decision_outcome"] in ("accepted", "conditional_acceptance")
        effects1 = data1["decision_record"]["state_effects"]
        assert "recruitment_workflow" in effects1
        assert effects1["recommended_candidate"]["position"] == "LW"
        assert 80 <= effects1["recommended_candidate"]["gsi"] <= 85

        # Verify Chief Scout posted shortlist coordination into the Staff Technical Room
        staff_room_msgs = data1["communications"]["staff_room"]
        assert any("Shortlist" in (m.get("topic") or "") or "LW" in (m.get("body") or "") for m in staff_room_msgs)

        # Verify DB persistence of OwnerRecruitmentAssignment and ClubDelegatedDecision
        assignments = list(
            session.scalars(
                select(OwnerRecruitmentAssignment).where(OwnerRecruitmentAssignment.club_id == state.club_id)
            ).all()
        )
        assert len(assignments) >= 1
        assert assignments[0].target_position == "LW"
        assert assignments[0].min_gsi == 80
        assert assignments[0].max_gsi == 85

        # 2. Conservative GM with constrained budget returns a counterproposal for a younger value target
        exec_staff["general_manager"] = {
            "id": "gm_conservative_2",
            "name": "Henrik Lindqvist",
            "role": "general_manager",
            "archetype_key": "financially_conservative_guardian",
            "personality_profile": dict(autonomous_staff_engine.GM_ARCHETYPES["financially_conservative_guardian"]),
        }
        fac["_executive_staff"] = exec_staff
        state.facilities_json = fac
        flag_modified(state, "facilities_json")
        # Drain most club cash so marquee LW exceeds conservative threshold
        bal = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
        if bal > 15000:
            ledger.record(
                session,
                event_type="capital_allocation",
                source=ledger.club_account(state.club_id),
                destination=ledger.WORLD_MARKET,
                currency=ledger.GTEX,
                gross=int(bal - 12000),
                club_id=state.club_id,
                user_id=state.owner_user_id,
                memo="Reserve lock",
            )
        session.commit()

        res2 = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:general_manager",
                "message": "I want us to sign a marquee left winger with a GSI between 80 and 85 immediately.",
                "topic": "Transfer Target",
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["decision_record"]["decision_outcome"] == "counterproposal"
        rec_cand = data2["decision_record"]["state_effects"]["recommended_candidate"]
        assert rec_cand["age"] <= 21
    finally:
        session.close()


def test_scenario_f_boardroom_meeting_multi_staff_disagreement_and_resolution() -> None:
    """Scenario F:
    Convene a boardroom meeting where Manager, General Manager, HOYD, and Chief Scout present
    distinct positions and explicit inter-staff disagreements, then ratify an owner resolution.
    """
    session, client, state = _setup_test_env()
    try:
        res = client.post(
            f"/owner/clubs/{state.club_id}/communications/meetings",
            json={
                "title": "Recruitment Budget & Academy Pathway Summit",
                "meeting_type": "recruitment_budget_meeting",
                "agenda": "Resolve tension between immediate 80-85 GSI recruitment and U18 striker pathway.",
                "convene_now": True,
            },
        )
        assert res.status_code == 200
        mtg = res.json()["meeting"]
        assert len(mtg["contributions"]) >= 4
        assert len(mtg["disagreements"]) >= 2
        axes = {d["axis"] for d in mtg["disagreements"]}
        assert "Manager vs General Manager" in axes
        assert "Head of Youth Development vs First-Team Manager" in axes
        assert len(mtg["proposed_resolutions"]) == 3

        # Resolve the meeting by backing the youth pathway & disciplined cap
        res_resolve = client.post(
            f"/owner/clubs/{state.club_id}/communications/meetings/{mtg['id']}/resolve",
            json={
                "resolution_id": "enforce_gm_sustainable_value",
                "owner_note": "Prioritize academy pathway and protect our wage structure.",
            },
        )
        assert res_resolve.status_code == 200
        resolved_payload = res_resolve.json()
        assert resolved_payload["status"] in ("completed", "resolved")
        assert resolved_payload["meeting"]["status"] == "completed"
        assert len(resolved_payload["meeting"]["decisions"]) == 1
    finally:
        session.close()


def test_scenario_g_staff_replacement_archives_predecessor_relationship_history() -> None:
    """Scenario G:
    Replacing a manager or executive staff member archives the predecessor's relationship history
    and never transfers it to the newly appointed replacement.
    """
    session, client, state = _setup_test_env()
    try:
        _assign_manager_archetype(session, state, "veteran_pragmatist")
        # Create tension with Manager 1 (Viktor Krall)
        client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:first_team_manager",
                "message": "Play our 16-year-old academy striker Lucas Vance in the next match.",
                "topic": "Selection",
            },
        )
        comms_before = client.get(f"/owner/clubs/{state.club_id}/communications").json()
        rel_before = comms_before["relationship_health"]["first_team_manager"]
        assert rel_before["actor_name"] == "Viktor Krall"
        assert rel_before["interference_count"] >= 1

        # Fire current manager and appoint a new manager with a different identity
        service.fire_manager(session, state.owner_user_id, state.club_id)
        service.appoint_manager(
            session,
            state.owner_user_id,
            state.club_id,
            {
                "manager_id": "mgr_new_visionary",
                "display_name": "Marco Bellini",
                "name": "Marco Bellini",
                "tactics": ["possession", "high_press"],
                "traits": ["youth_developer"],
            },
        )
        session.commit()

        comms_after = client.get(f"/owner/clubs/{state.club_id}/communications").json()
        rel_after = comms_after["relationship_health"]["first_team_manager"]
        assert rel_after["actor_name"] == "Marco Bellini"
        assert rel_after["interference_count"] == 0
        assert rel_after["tension"] == 16

        session.refresh(state)
        archived_rels = list((state.facilities_json or {}).get("_archived_staff_relationships") or [])
        assert any(r.get("staff_name") == "Viktor Krall" for r in archived_rels)
    finally:
        session.close()


def test_scenario_h_owner_cannot_control_live_match_coaching_and_lineup_is_non_binding() -> None:
    """Scenario H:
    Verify the owner cannot issue live coaching commands, and any owner lineup/formation submission
    is recorded strictly as a non-binding preference while the First-Team Manager authoritatively
    selects the matchday squad and formation.
    """
    session, client, state = _setup_test_env()
    try:
        _assign_manager_archetype(session, state, "veteran_pragmatist")
        acad_id = f"{state.club_id}:p-acad-st-16"
        comms = client.get(f"/owner/clubs/{state.club_id}/communications").json()
        assert comms["owner_authority"]["can_coach_matchday"] is False
        assert comms["permissions"]["can_control_matchday_tactics"] is False
        assert comms["permissions"]["can_control_live_substitutions"] is False

        # Owner submits a non-binding preference asking for 3-4-3 and the 16yo academy striker
        pref_res = client.post(
            f"/owner/clubs/{state.club_id}/lineup-preference",
            json={
                "preferred_formation": "3-4-3",
                "preferred_player_ids": [acad_id],
                "note": "Owner preference for 3-4-3 with Lucas Vance",
            },
        )
        assert pref_res.status_code == 200
        pref_data = pref_res.json()
        assert pref_data["is_non_binding_preference"] is True
        assert pref_data["authority_model"] == "first_team_manager_authoritative"

        # Independent manager Viktor Krall keeps his preferred 4-4-2 and senior striker
        mgr_sel = pref_data["manager_selection"]
        assert mgr_sel["formation"] == "4-4-2"
        assert acad_id not in mgr_sel["starting_xi_ids"]
    finally:
        session.close()


def test_scenario_i_persistent_club_culture_evolves_gradually_across_world_ticks() -> None:
    """Scenario I:
    Verify club culture transitions start gradually (not instantaneously) when requested by the owner
    and continue evolving across world ticks (`tick_club`) even when the owner is offline.
    """
    session, client, state = _setup_test_env()
    try:
        _assign_manager_archetype(session, state, "youth_development_visionary")
        res = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:first_team_manager",
                "message": "I want our academy players to receive more first-team opportunities and define our club identity.",
                "topic": "Club Philosophy",
            },
        )
        assert res.status_code == 200
        culture_initial = res.json()["communications"]["club_culture"]
        assert culture_initial["target_identity"] == "youth_development"
        initial_progress = int(culture_initial["transition_progress_pct"])
        assert initial_progress < 100

        # Advance club world tick (simulating background progression while owner is offline)
        session.refresh(state)
        service.tick_club(session, state, use_ai=False)
        session.commit()

        comms_after = client.get(f"/owner/clubs/{state.club_id}/communications").json()
        culture_after = comms_after["club_culture"]
        assert int(culture_after["transition_progress_pct"]) > initial_progress
    finally:
        session.close()


def test_scenario_j_idempotency_and_grounded_fallback_when_ai_provider_unavailable(monkeypatch) -> None:
    """Scenario J:
    When no external LLM key is configured or the AI provider fails, Layer A still persists the
    authoritative `OwnerStaffDecisionRecord`, Layer B produces a strictly grounded response without
    inventing players/transfers/budgets, and `idempotency_key` prevents duplicate decisions.
    """
    session, client, state = _setup_test_env()
    try:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GTEX_AI_API_KEY", raising=False)

        idem_key = "idem-test-scenario-j-001"
        res1 = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:assistant_attacking",
                "message": "Focus attacking drills on finishing and final-third combinations this week.",
                "topic": "Training Focus",
                "idempotency_key": idem_key,
            },
        )
        assert res1.status_code == 200
        body1 = res1.json()
        assert body1["decision_record"]["ai_generation_status"] in ("grounded_deterministic", "grounded_template_fallback")
        decision_id_1 = body1["decision_record"]["id"]

        # Replay with same idempotency_key -> must return the exact same decision record without duplicating
        res2 = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:assistant_attacking",
                "message": "Focus attacking drills on finishing and final-third combinations this week.",
                "topic": "Training Focus",
                "idempotency_key": idem_key,
            },
        )
        assert res2.status_code == 200
        body2 = res2.json()
        assert body2.get("idempotent_replay") is True
        assert body2["decision_record"]["id"] == decision_id_1

        records = list(
            session.scalars(
                select(OwnerStaffDecisionRecord).where(OwnerStaffDecisionRecord.idempotency_key == idem_key)
            ).all()
        )
        assert len(records) == 1
    finally:
        session.close()
