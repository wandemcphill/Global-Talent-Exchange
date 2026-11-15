from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

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
    competitions as owner_competitions,
    engine as owner_engine,
    ledger,
)
from app.owner_console.models import (
    OwnerClubRelationship,
    OwnerClubState,
    OwnerCompetitionEntry,
    OwnerSquadPlayer,
)
from app.owner_console.router import router as owner_router
from app.services.world_clock_service import DEFAULT_CLOCK_ID

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


def _setup_test_env() -> tuple[Session, TestClient, OwnerClubState, User]:
    engine_db = _get_shared_engine()
    SessionLocal = sessionmaker(bind=engine_db, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    uid = uuid4().hex[:8]
    user = User(
        id=f"u_s1_{uid}",
        email=f"stage1_{uid}@gtex.test",
        username=f"stage1owner_{uid}",
        full_name="Chief Owner Adeyemi",
        display_name="Chief Owner Adeyemi",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
        account_type=PublicAccountType.USER,
    )
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
    cp = ClubProfile(
        id=f"c_s1_{uid}",
        owner_user_id=user.id,
        club_name=f"Stage One FC {uid}",
        short_name=f"S{uid[:3]}".upper(),
        slug=f"stage-one-{uid}",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#00ff88",
        country_code="NG",
        visibility="public",
    )
    state = OwnerClubState(
        club_id=cp.id,
        owner_user_id=user.id,
        club_name=cp.club_name,
        stage="active",
        world_day=12,
        prestige=72,
        fans=18000,
        mentality="balanced",
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 3, "academy": 3, "medical": 3, "stadium": 3, "commercial": 3},
    )
    session.add_all([user, cp, state])
    session.flush()
    ledger.record(
        session,
        event_type="test_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(cp.id),
        currency=ledger.GTEX,
        gross=850000,
        balance_class="deposited",
        club_id=cp.id,
        user_id=user.id,
        memo="Stage 1 initial treasury",
    )
    for idx, (pos, age, rtg) in enumerate(
        [
            ("GK", 27, 78),
            ("CB", 28, 79),
            ("CB", 26, 77),
            ("LB", 24, 76),
            ("RB", 25, 76),
            ("CM", 27, 80),
            ("CDM", 29, 78),
            ("CAM", 23, 78),
            ("LW", 22, 77),
            ("RW", 24, 77),
            ("ST", 26, 81),
            ("ST", 19, 71),
        ],
        start=1,
    ):
        session.add(
            OwnerSquadPlayer(
                id=f"{cp.id}-p-{idx}",
                club_id=cp.id,
                name=f"StageOne Player {idx}",
                position=pos,
                age=age,
                rating=rtg,
                potential=max(rtg + 2, 82),
                value_coin=Decimal(str(rtg * 15)),
                morale=76,
                minutes=180 if idx < 12 else 15,
                injured_days=0,
                is_regen=idx == 12,
                personality_json={"fitness": 94, "is_academy": idx == 12},
                status="active",
                acquired_via="academy" if idx == 12 else "market",
            )
        )
    session.commit()

    app = FastAPI()
    app.include_router(owner_router)

    def _get_db() -> Iterator[Session]:
        yield session

    def _get_user() -> User:
        return session.get(User, user.id)

    app.dependency_overrides[get_session] = _get_db
    app.dependency_overrides[get_current_user] = _get_user

    return session, TestClient(app), state, user


def test_executive_office_gm_and_finance_identity_separation() -> None:
    """1A: Executive Office belongs to the Club Owner (`room:staff`), GM has its own office
    and identity, Finance & Commercial has its own office/identity, and vacant roles do not
    manufacture fake NPC personas."""
    session, client, state, user = _setup_test_env()
    try:
        res = client.get(f"/owner/clubs/{state.club_id}/operations-hub")
        assert res.status_code == 200
        hub = res.json()

        dests = {d["destination_key"]: d for d in hub["destinations"]}

        # Executive Office is Owner Command + office-wide room:staff (never General Manager)
        exec_office = dests["executive_office"]
        assert exec_office["lead_role_key"] == "owner"
        assert exec_office["communication_thread_id"] == "room:staff"
        assert exec_office["communication_channel_mode"] == "office_wide"
        assert exec_office["staff_lead"]["role_key"] == "owner"
        assert exec_office["staff_lead"]["name"] == user.display_name
        assert exec_office["staff_lead"]["is_owner_workspace"] is True

        # General Manager & Finance Office start honestly vacant with separate roles
        gm_office = dests["general_managers_office"]
        assert gm_office["lead_role_key"] == "general_manager"
        assert gm_office["communication_thread_id"] == "staff:general_manager"
        assert gm_office["communication_channel_mode"] == "vacant"
        assert gm_office["staff_lead"]["is_vacant"] is True
        assert "Dayo Adeleke" not in gm_office["staff_lead"]["name"]

        fin_office = dests["finance_commercial_office"]
        assert fin_office["lead_role_key"] == "finance_commercial_director"
        assert fin_office["communication_thread_id"] == "staff:finance_commercial_director"
        assert fin_office["communication_channel_mode"] == "vacant"
        assert fin_office["staff_lead"]["is_vacant"] is True

        # Appoint ONLY a real General Manager; Executive Office & Finance remain separate
        fac = dict(state.facilities_json or {})
        exec_staff = dict(fac.get("_executive_staff") or {})
        exec_staff["general_manager"] = {
            "id": "gm_appointed_real_1",
            "name": "Ngozi Iweala-GM",
            "role": "general_manager",
            "archetype_key": "ambitious_squad_architect",
            "mood": 82,
        }
        fac["_executive_staff"] = exec_staff
        state.facilities_json = fac
        flag_modified(state, "facilities_json")
        session.commit()

        hub2 = client.get(f"/owner/clubs/{state.club_id}/operations-hub").json()
        dests2 = {d["destination_key"]: d for d in hub2["destinations"]}
        assert dests2["executive_office"]["lead_role_key"] == "owner"
        assert dests2["executive_office"]["staff_lead"]["name"] == user.display_name
        assert dests2["general_managers_office"]["communication_channel_mode"] == "direct"
        assert dests2["general_managers_office"]["staff_lead"]["name"] == "Ngozi Iweala-GM"
        assert dests2["general_managers_office"]["staff_lead"]["is_vacant"] is False
        assert dests2["finance_commercial_office"]["communication_channel_mode"] == "vacant"
        assert dests2["finance_commercial_office"]["staff_lead"]["is_vacant"] is True
    finally:
        session.close()


def test_communications_never_fake_owner_reply_or_vacant_npc() -> None:
    """1A: Direct owner self-messaging is rejected, unknown threads return 404, vacant staff
    threads record owner memos without fake NPC replies or fake relationship rows, and office-wide
    `room:staff` routes only to actually appointed staff (never Owner)."""
    session, client, state, user = _setup_test_env()
    try:
        # Owner self-thread is explicitly rejected on both durable comms and legacy chat
        r_owner = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "staff:owner", "message": "Self reply test"},
        )
        assert r_owner.status_code == 400

        r_legacy_owner = client.post(
            f"/owner/clubs/{state.club_id}/staff/chat",
            json={"role": "owner", "message": "Self reply legacy test"},
        )
        assert r_legacy_owner.status_code == 400

        r_legacy_vacant_gm = client.post(
            f"/owner/clubs/{state.club_id}/staff/chat",
            json={"role": "general_manager", "message": "Hello vacant GM"},
        )
        assert r_legacy_vacant_gm.status_code == 409

        # Unknown recipient returns 404 rather than silently hijacking another staffer
        r_unknown = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "staff:nonexistent_officer", "message": "Hello"},
        )
        assert r_unknown.status_code == 404

        # Vacant General Manager: memo stored, NO fake NPC reply ("Dayo Adeleke"), NO relationship created
        r_gm_vacant = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "staff:general_manager", "message": "Status check on commercial plan."},
        )
        assert r_gm_vacant.status_code == 200
        d_vacant = r_gm_vacant.json()
        assert d_vacant["role_vacant"] is True
        assert d_vacant["reply"] is None
        assert d_vacant["reply_message"] is None

        gm_rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == state.club_id,
                OwnerClubRelationship.participant_b_type == "staff",
                OwnerClubRelationship.participant_b_id == "general_manager",
            )
        )
        assert gm_rel is None

        # Vacating first-team manager too so ALL senior seats are vacant:
        # room:staff must NEVER reply as Owner or manufacture a fake NPC!
        saved_mgr = dict(state.manager_json or {})
        state.manager_json = {"is_vacant": True, "name": ""}
        flag_modified(state, "manager_json")
        session.commit()

        r_room_all_vacant = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "room:staff", "message": "Executive directive to whole clubroom."},
        )
        assert r_room_all_vacant.status_code == 200
        d_room_vacant = r_room_all_vacant.json()
        assert d_room_vacant["role_vacant"] is True
        assert d_room_vacant["reply"] is None

        # Restore manager & appoint distinct GM; room:staff responds as GM, NOT Owner
        state.manager_json = saved_mgr
        flag_modified(state, "manager_json")
        fac = dict(state.facilities_json or {})
        exec_staff = dict(fac.get("_executive_staff") or {})
        exec_staff["general_manager"] = {
            "id": "gm_appointed_real_2",
            "name": "Chika Nwankwo",
            "role": "general_manager",
            "archetype_key": "ambitious_squad_architect",
        }
        fac["_executive_staff"] = exec_staff
        state.facilities_json = fac
        flag_modified(state, "facilities_json")
        session.commit()

        r_room_appointed = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={"thread_id": "room:staff", "message": "Update commercial briefing for matchday."},
        )
        assert r_room_appointed.status_code == 200
        d_room_ok = r_room_appointed.json()
        assert d_room_ok["role_vacant"] is False
        assert d_room_ok["reply"] is not None
        assert d_room_ok["reply"]["sender_name"] == "Chika Nwankwo"
        assert d_room_ok["reply"]["sender_name"] != user.display_name
        assert d_room_ok["reply"]["sender_role"] == "General Manager"
    finally:
        session.close()


def test_manager_tactical_authority_matrix_thresholds_and_variants() -> None:
    """1B: Canonical authority decision covers high/low independence, high/low tolerance,
    acceptance, rejection, and balanced compromise without contradictory thresholds."""
    # High independence + low tolerance (Tunde Bakare archetype, prefers defensive) -> REJECT attacking
    high_indep_mgr = {
        "id": "mgr_tunde",
        "name": "Tunde Bakare",
        "personality_profile": {
            "professional_independence": 89,
            "tolerance_for_owner_interference": 27,
            "tactical_flexibility": 46,
            "loyalty": 72,
            "attacking_vs_defensive": 29,
            "preferred_formations": ["4-4-2"],
        },
    }
    res_rej = autonomous_staff_engine.resolve_manager_mentality_decision(
        high_indep_mgr,
        requested_mentality="attacking",
    )
    assert res_rej["decision_status"] == "rejected"
    assert res_rej["effective_mentality"] == "defensive"
    assert res_rej["owner_requested_mentality"] == "attacking"
    assert res_rej["implemented_as_requested"] is False

    # High independence even with high tolerance (indep=82 >= 75) -> REJECT override
    high_indep_high_tol = {
        "id": "mgr_autocrat",
        "name": "Autocrat Boss",
        "personality_profile": {
            "professional_independence": 82,
            "tolerance_for_owner_interference": 80,
            "tactical_flexibility": 70,
            "loyalty": 70,
            "attacking_vs_defensive": 32,
            "preferred_formations": ["4-4-2"],
        },
    }
    res_indep = autonomous_staff_engine.resolve_manager_mentality_decision(
        high_indep_high_tol,
        requested_mentality="attacking",
    )
    assert res_indep["decision_status"] == "rejected"
    assert res_indep["effective_mentality"] == "defensive"

    # Low independence + low tolerance (tol=30 < 40) -> REJECT override
    low_indep_low_tol = {
        "id": "mgr_touchy",
        "name": "Low Tolerance Boss",
        "personality_profile": {
            "professional_independence": 40,
            "tolerance_for_owner_interference": 30,
            "tactical_flexibility": 60,
            "loyalty": 65,
            "attacking_vs_defensive": 50,
            "preferred_formations": ["4-3-3"],
        },
    }
    res_low_tol = autonomous_staff_engine.resolve_manager_mentality_decision(
        low_indep_low_tol,
        requested_mentality="attacking",
    )
    assert res_low_tol["decision_status"] == "rejected"
    assert res_low_tol["effective_mentality"] == "balanced"

    # Low independence + high tolerance -> ACCEPT owner's attacking preference
    collaborative_mgr = {
        "id": "mgr_collab",
        "name": "Collaborative Coach",
        "personality_profile": {
            "professional_independence": 25,
            "tolerance_for_owner_interference": 85,
            "tactical_flexibility": 75,
            "loyalty": 75,
            "attacking_vs_defensive": 50,
            "preferred_formations": ["4-3-3"],
        },
    }
    res_acc = autonomous_staff_engine.resolve_manager_mentality_decision(
        collaborative_mgr,
        requested_mentality="attacking",
    )
    assert res_acc["decision_status"] == "accepted"
    assert res_acc["effective_mentality"] == "attacking"
    assert res_acc["implemented_as_requested"] is True

    # Moderate compromise band (deference_score ~40.6, distance == 2) -> MODIFIED to balanced
    compromise_mgr = {
        "id": "mgr_pragmatic",
        "name": "Pragmatic Compromiser",
        "personality_profile": {
            "professional_independence": 50,
            "tolerance_for_owner_interference": 62,
            "tactical_flexibility": 60,
            "loyalty": 65,
            "attacking_vs_defensive": 30,
            "preferred_formations": ["4-3-3"],
        },
    }
    res_mod = autonomous_staff_engine.resolve_manager_mentality_decision(
        compromise_mgr,
        requested_mentality="attacking",
    )
    assert res_mod["decision_status"] == "modified"
    assert res_mod["effective_mentality"] == "balanced"
    assert res_mod["implemented_as_requested"] is False


def test_mentality_api_hub_selection_and_competition_parity_across_manager_replacement() -> None:
    """1B + 1C: API, Operations Hub, Matchday Lineup Selection, and Competition `_side`
    consume the exact same canonical decision before and after manager replacement."""
    session, client, state, _user = _setup_test_env()
    try:
        # 1. Appoint high-independence defensive manager
        state.manager_json = {
            "id": "mgr_stubborn_1",
            "name": "Emeka Ironside",
            "temperament": "pragmatic",
            "style": "low_block_counter",
            "youth_development": 10,
            "loyalty": 14,
            "personality_profile": {
                "archetype_key": "veteran_pragmatist",
                "archetype_label": "Veteran Pragmatist",
                "professional_independence": 89,
                "tolerance_for_owner_interference": 27,
                "tactical_flexibility": 44,
                "loyalty": 70,
                "attacking_vs_defensive": 29,
                "pressing_philosophy": 45,
                "preferred_tactical_philosophy": "defensive_organization",
                "preferred_formations": ["4-4-2"],
            },
        }
        flag_modified(state, "manager_json")
        session.commit()

        put_res = client.put(f"/owner/clubs/{state.club_id}/mentality", json={"mentality": "attacking"})
        assert put_res.status_code == 200
        put_data = put_res.json()
        assert put_data["owner_requested_mentality"] == "attacking"
        assert put_data["effective_matchday_mentality"] == "defensive"
        assert put_data["mentality"] == "defensive"
        assert put_data["manager_decision_status"] == "rejected"
        assert put_data["implemented_as_requested"] is False
        assert "Emeka Ironside" in put_data["manager_decision_reasoning"]

        hub = client.get(f"/owner/clubs/{state.club_id}/operations-hub").json()
        assert hub["club"]["owner_requested_mentality"] == "attacking"
        assert hub["club"]["effective_matchday_mentality"] == "defensive"
        assert hub["club"]["mentality"] == "defensive"
        assert hub["club"]["manager_decision_status"] == "rejected"

        lineup = autonomous_staff_engine.select_manager_matchday_lineup(session, state)
        assert lineup["mentality"] == "defensive"
        assert lineup["mentality_authority"]["decision_status"] == "rejected"

        comp_entry = OwnerCompetitionEntry(
            id=f"ce_{state.club_id}",
            competition_id=f"comp_{state.club_id}",
            club_id=state.club_id,
            club_name=state.club_name,
            owner_user_id=state.owner_user_id,
            is_ai=False,
        )
        comp_side = owner_competitions._side(session, comp_entry, state.mentality, "standard")
        assert comp_side["mentality"] == "defensive"
        assert comp_side["owner_requested_mentality"] == "attacking"
        assert comp_side["manager_decision_status"] == "rejected"

        # 2. Replace with a flexible collaborative manager -> same stored preference now accepted cleanly
        state.manager_json = {
            "id": "mgr_flexible_2",
            "name": "Amina Tactician",
            "temperament": "ambitious",
            "style": "fluid_attack",
            "youth_development": 14,
            "loyalty": 16,
            "personality_profile": {
                "archetype_key": "ambitious_progressive",
                "archetype_label": "Ambitious Progressive",
                "professional_independence": 28,
                "tolerance_for_owner_interference": 84,
                "tactical_flexibility": 78,
                "loyalty": 76,
                "attacking_vs_defensive": 52,
                "pressing_philosophy": 74,
                "preferred_tactical_philosophy": "positional_play",
                "preferred_formations": ["4-3-3"],
            },
        }
        flag_modified(state, "manager_json")
        session.commit()

        put_res2 = client.put(f"/owner/clubs/{state.club_id}/mentality", json={"mentality": "attacking"})
        assert put_res2.status_code == 200
        put_data2 = put_res2.json()
        assert put_data2["effective_matchday_mentality"] == "attacking"
        assert put_data2["mentality"] == "attacking"
        assert put_data2["manager_decision_status"] == "accepted"
        assert put_data2["implemented_as_requested"] is True
        assert "Amina Tactician" in put_data2["manager_decision_reasoning"]

        hub2 = client.get(f"/owner/clubs/{state.club_id}/operations-hub").json()
        assert hub2["club"]["effective_matchday_mentality"] == "attacking"
        assert hub2["club"]["manager_decision_status"] == "accepted"

        lineup2 = autonomous_staff_engine.select_manager_matchday_lineup(session, state)
        assert lineup2["mentality"] == "attacking"

        comp_side2 = owner_competitions._side(session, comp_entry, state.mentality, "standard")
        assert comp_side2["mentality"] == "attacking"
        assert comp_side2["manager_decision_status"] == "accepted"
    finally:
        session.close()
