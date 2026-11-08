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
from app.models.club_profile import ClubProfile
from app.models.event_backbone import EventOutbox
from app.models.wallet import (
    LedgerAccount,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
)
from app.models.risk_ops import AuditLog
from app.models.user import User
from app.models.world_clock import WorldClockState
from app.owner_console import living_club_world, router as owner_router
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    ClubDelegatedDecision,
    ClubDelegatedDecisionAuditLog,
    OwnerClubRelationship,
    OwnerClubRelationshipHistory,
    OwnerClubState,
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
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            WorldClockState.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    session = factory()
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
    session: Session, user_id: str = "u_owner_stage3", club_id: str = "c_lagos_stage3"
) -> tuple[OwnerClubState, list[OwnerSquadPlayer]]:
    user = User(
        id=user_id,
        email=f"{user_id}@gtex.test",
        username=f"owner_{user_id}",
        password_hash="synthetic_hash",  # pragma: allowlist secret
        role="user",
        is_active=True,
    )
    session.add(user)

    profile = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name=f"Lagos Marine FC ({club_id})",
        slug=f"lagos-marine-fc-{club_id}",
        primary_color="#0284c7",
        secondary_color="#0f172a",
        accent_color="#38bdf8",
    )
    session.add(profile)

    state = OwnerClubState(
        id=f"state-{club_id}",
        club_id=club_id,
        owner_user_id=user_id,
        club_name=f"Lagos Marine FC ({club_id})",
        stage="active",
        prestige=55,
        world_day=4,
        last_tick_at=WORLD_NOW,
        last_world_tick_date=WORLD_NOW.date(),
        value_history_json=[],
        facilities_json={
            "training": 2,
            "academy": 2,
            "medical": 2,
            "stadium": 2,
            "commercial": 2,
            "_executive_staff": {
                "general_manager": {
                    "id": "gm_dayo",
                    "staff_id": "gm_dayo",
                    "role": "general_manager",
                    "name": "Dayo Adeleke",
                    "style": "Strategic Builder",
                    "is_vacant": False,
                },
                "head_of_youth_development": {
                    "id": "hoyd_chidi",
                    "staff_id": "hoyd_chidi",
                    "role": "head_of_youth_development",
                    "name": "Chidi Eze",
                    "style": "Talent Incubator",
                    "is_vacant": False,
                },
                "medical_director": {
                    "id": "med_amara",
                    "staff_id": "med_amara",
                    "role": "medical_director",
                    "name": "Dr. Amara Okonkwo",
                    "style": "Biometric Precision",
                    "is_vacant": False,
                },
                "club_president": {
                    "id": "pres_babatunde",
                    "staff_id": "pres_babatunde",
                    "role": "club_president",
                    "name": "Chief Babatunde Balogun",
                    "style": "Statesman Guardian",
                    "is_vacant": False,
                },
                "finance_commercial_director": {
                    "id": "fin_funke",
                    "staff_id": "fin_funke",
                    "role": "finance_commercial_director",
                    "name": "Funke Williams",
                    "style": "Commercial Maximizer",
                    "is_vacant": False,
                },
            },
            "chat_messages": [],
        },
        manager_json={
            "id": "mgr_samson",
            "name": "Samson Siasia",
            "style": "High-Pressing Possession",
            "reputation": 65,
            "fitness": 90,
            "mood": 70,
        },
    )
    session.add(state)

    p1 = OwnerSquadPlayer(
        id=f"p_star_{club_id}",
        club_id=club_id,
        name="Victor Osimhen",
        position="ST",
        age=26,
        rating=87,
        potential=89,
        value_coin=Decimal("45000"),
        morale=75,
        injured_days=0,
        is_regen=False,
        personality_json={"leadership": 16, "fitness": 90},
    )
    p2 = OwnerSquadPlayer(
        id=f"p_prospect_{club_id}",
        club_id=club_id,
        name="Tobi Alabi",
        position="CAM",
        age=17,
        rating=68,
        potential=88,
        value_coin=Decimal("5000"),
        morale=70,
        injured_days=0,
        is_regen=True,
        personality_json={"leadership": 12, "fitness": 88},
    )
    session.add_all([p1, p2])
    session.commit()
    living_club_world.ensure_default_relationships(session, state, [p1, p2])
    from app.owner_console import ledger

    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=Decimal("100000"),
        club_id=club_id,
        user_id=user_id,
        memo="Initial club grant",
    )
    session.commit()
    return state, [p1, p2]


def test_get_or_create_delegation_policy_initializes_defaults() -> None:
    session = _session()
    user_id = "u_del_policy"
    club_id = "c_del_policy"
    _bootstrap_club(session, user_id=user_id, club_id=club_id)

    policy = living_club_world.get_or_create_delegation_policy(session, club_id, user_id)
    assert policy.club_id == club_id
    assert policy.owner_user_id == user_id
    assert policy.mode == "balanced"
    assert policy.is_suspended is False
    assert "first_team_manager" in policy.financial_thresholds_json
    assert "general_manager" in policy.financial_thresholds_json
    assert policy.financial_thresholds_json["general_manager"]["max_amount_gtex"] == 2500

    # Second call returns existing policy without duplicate creation
    policy2 = living_club_world.get_or_create_delegation_policy(session, club_id, user_id)
    assert policy2.id == policy.id


def test_simulate_autonomous_staff_decisions_executes_actions_and_logs_audit() -> None:
    session = _session()
    user_id = "u_auto_sim"
    club_id = "c_auto_sim"
    state, players = _bootstrap_club(session, user_id=user_id, club_id=club_id)

    res = living_club_world.simulate_autonomous_staff_decisions(session, user_id, club_id)
    assert res["club_id"] == club_id
    assert res["is_suspended"] is False
    assert res["simulated_count"] > 0

    # Verify decisions created in DB
    db_decisions = list(
        session.scalars(
            select(ClubDelegatedDecision)
            .where(ClubDelegatedDecision.club_id == club_id)
            .order_by(ClubDelegatedDecision.created_at.asc())
        ).all()
    )
    assert len(db_decisions) >= 5

    approved_decisions = [d for d in db_decisions if d.status == "approved"]
    assert len(approved_decisions) >= 5
    for d in approved_decisions:
        assert d.execution_status == "executed"
        assert d.requires_owner_approval is False
        assert d.decided_by_user_id == "staff_autonomous"

    # Verify audit logs created
    audit_logs = list(
        session.scalars(
            select(ClubDelegatedDecisionAuditLog).where(ClubDelegatedDecisionAuditLog.club_id == club_id)
        ).all()
    )
    assert len(audit_logs) >= len(db_decisions)
    assert any(a.action == "execute_autonomous" for a in audit_logs)

    # Verify squad consequence applied
    session.refresh(players[0])
    session.refresh(players[1])
    assert players[0].morale > 75
    assert players[1].morale > 70

    # Verify chat messages synced to facilities_json
    session.refresh(state)
    chat_msgs = state.facilities_json.get("chat_messages") or []
    assert len(chat_msgs) >= 5
    assert any("Samson Siasia" in m["sender"] or "tactical" in m["message"].lower() for m in chat_msgs)


def test_simulate_autonomous_staff_decisions_respects_suspension() -> None:
    session = _session()
    user_id = "u_auto_susp"
    club_id = "c_auto_susp"
    _bootstrap_club(session, user_id=user_id, club_id=club_id)

    policy = living_club_world.get_or_create_delegation_policy(session, club_id, user_id)
    policy.is_suspended = True
    policy.suspension_reason = "Board audit in progress."
    session.flush()

    res = living_club_world.simulate_autonomous_staff_decisions(session, user_id, club_id)
    assert res["is_suspended"] is True
    assert res["simulated_count"] == 0
    assert "Board audit in progress" in res["suspension_reason"]

    # No new decisions added
    db_decisions = list(
        session.scalars(select(ClubDelegatedDecision).where(ClubDelegatedDecision.club_id == club_id)).all()
    )
    assert len(db_decisions) == 0


def test_simulate_autonomous_staff_decisions_escalates_alienated_staff() -> None:
    session = _session()
    user_id = "u_auto_alien"
    club_id = "c_auto_alien"
    state, _ = _bootstrap_club(session, user_id=user_id, club_id=club_id)

    # Set Manager to acute tension and low alignment
    living_club_world.reconcile_staff_relationships(session, state)
    roster = living_club_world.resolve_club_staff_roster(state)
    mgr_slot = roster["first_team_manager"]
    key = living_club_world.pairing_key(club_id, "owner", mgr_slot["person_id"])
    mgr_rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == key,
        )
    )
    assert mgr_rel is not None
    mgr_rel.tension = 85
    mgr_rel.alignment = 20
    session.flush()

    res = living_club_world.simulate_autonomous_staff_decisions(session, user_id, club_id)
    mgr_decision = next(d for d in res["decisions"] if d["role_key"] == "first_team_manager")
    assert mgr_decision["status"] == "escalated"
    assert mgr_decision["execution_status"] == "blocked"
    assert "escalated" in mgr_decision["outcome_text"].lower()


def test_get_or_create_living_boardroom_dilemma_constructs_balanced_choices() -> None:
    session = _session()
    user_id = "u_dilemma_init"
    club_id = "c_dilemma_init"
    _bootstrap_club(session, user_id=user_id, club_id=club_id)

    dilemma = living_club_world.get_or_create_living_boardroom_dilemma(session, user_id, club_id)
    assert dilemma["status"] == "open"
    assert "Transfer War Chest" in dilemma["title"]
    assert dilemma["role_a"] == "first_team_manager"
    assert dilemma["role_b"] == "general_manager"
    assert len(dilemma["choices"]) == 3

    choice_ids = [c["choice_id"] for c in dilemma["choices"]]
    assert "back_manager_recruitment" in choice_ids
    assert "enforce_gm_wage_discipline" in choice_ids
    assert "ratify_performance_compromise" in choice_ids

    # Each choice has 7-metric projections for both roles
    for c in dilemma["choices"]:
        assert "delta_role_a" in c
        assert "delta_role_b" in c
        assert "alignment" in c["delta_role_a"]
        assert "tension" in c["delta_role_a"]
        assert "loyalty" in c["delta_role_b"]


def test_resolve_living_boardroom_dilemma_backs_manager() -> None:
    session = _session()
    user_id = "u_dilemma_mgr"
    club_id = "c_dilemma_mgr"
    state, players = _bootstrap_club(session, user_id=user_id, club_id=club_id)

    dilemma = living_club_world.get_or_create_living_boardroom_dilemma(session, user_id, club_id)
    res = living_club_world.resolve_living_boardroom_dilemma(
        session,
        user_id,
        club_id,
        dilemma_id=dilemma["dilemma_id"],
        choice_id="back_manager_recruitment",
        decision_note="Competitive results require immediate sporting backing.",
    )

    assert res["dilemma"]["status"] == "resolved"
    assert res["dilemma"]["selected_choice_id"] == "back_manager_recruitment"

    # Check relationships
    roster = living_club_world.resolve_club_staff_roster(state)
    mgr_key = living_club_world.pairing_key(club_id, "owner", roster["first_team_manager"]["person_id"])
    gm_key = living_club_world.pairing_key(club_id, "owner", roster["general_manager"]["person_id"])
    mgr_rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.pairing_key == mgr_key))
    gm_rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.pairing_key == gm_key))

    # Manager should gain trust & alignment; GM should experience increased tension
    assert mgr_rel.trust > 50
    assert mgr_rel.alignment > 60
    assert gm_rel.tension >= 20

    # Verify history logs created for both personas
    hist_mgr = list(
        session.scalars(
            select(OwnerClubRelationshipHistory).where(OwnerClubRelationshipHistory.relationship_id == mgr_rel.id)
        ).all()
    )
    hist_gm = list(
        session.scalars(
            select(OwnerClubRelationshipHistory).where(OwnerClubRelationshipHistory.relationship_id == gm_rel.id)
        ).all()
    )
    assert len(hist_mgr) >= 1
    assert len(hist_gm) >= 1

    # Verify squad morale boost
    session.refresh(players[0])
    assert players[0].morale == 83  # 75 + 8

    # Verify delegated decision logged
    del_decision = session.scalar(
        select(ClubDelegatedDecision).where(ClubDelegatedDecision.activity_key == f"dilemma_{dilemma['dilemma_id']}")
    )
    assert del_decision is not None
    assert del_decision.status == "resolved"
    assert del_decision.execution_status == "executed"


def test_resolve_living_boardroom_dilemma_backs_general_manager() -> None:
    session = _session()
    user_id = "u_dilemma_gm"
    club_id = "c_dilemma_gm"
    state, players = _bootstrap_club(session, user_id=user_id, club_id=club_id)

    dilemma = living_club_world.get_or_create_living_boardroom_dilemma(session, user_id, club_id)
    res = living_club_world.resolve_living_boardroom_dilemma(
        session,
        user_id,
        club_id,
        dilemma_id=dilemma["dilemma_id"],
        choice_id="enforce_gm_wage_discipline",
        decision_note="Fiscal prudence protects club long-term solvency.",
    )

    assert res["dilemma"]["status"] == "resolved"
    assert res["dilemma"]["selected_choice_id"] == "enforce_gm_wage_discipline"

    roster = living_club_world.resolve_club_staff_roster(state)
    mgr_key = living_club_world.pairing_key(club_id, "owner", roster["first_team_manager"]["person_id"])
    gm_key = living_club_world.pairing_key(club_id, "owner", roster["general_manager"]["person_id"])
    mgr_rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.pairing_key == mgr_key))
    gm_rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.pairing_key == gm_key))

    # GM gains trust & respect; Manager gains tension
    assert gm_rel.trust > 50
    assert gm_rel.respect > 50
    assert mgr_rel.tension > 20

    # Squad morale dipped slightly
    session.refresh(players[0])
    assert players[0].morale == 72  # 75 - 3


def test_resolve_living_boardroom_dilemma_compromise() -> None:
    session = _session()
    user_id = "u_dilemma_comp"
    club_id = "c_dilemma_comp"
    state, players = _bootstrap_club(session, user_id=user_id, club_id=club_id)

    dilemma = living_club_world.get_or_create_living_boardroom_dilemma(session, user_id, club_id)
    res = living_club_world.resolve_living_boardroom_dilemma(
        session,
        user_id,
        club_id,
        dilemma_id=dilemma["dilemma_id"],
        choice_id="ratify_performance_compromise",
    )

    assert res["dilemma"]["status"] == "resolved"
    assert res["dilemma"]["selected_choice_id"] == "ratify_performance_compromise"

    roster = living_club_world.resolve_club_staff_roster(state)
    mgr_key = living_club_world.pairing_key(club_id, "owner", roster["first_team_manager"]["person_id"])
    gm_key = living_club_world.pairing_key(club_id, "owner", roster["general_manager"]["person_id"])
    mgr_rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.pairing_key == mgr_key))
    gm_rel = session.scalar(select(OwnerClubRelationship).where(OwnerClubRelationship.pairing_key == gm_key))

    # Both roles gain trust & alignment
    assert mgr_rel.alignment > 60
    assert gm_rel.alignment > 60
    assert mgr_rel.tension < 20
    assert gm_rel.tension < 20

    # Prestige gained
    session.refresh(state)
    assert state.prestige == 56  # 55 + 1


def test_get_delegated_decisions_history() -> None:
    session = _session()
    user_id = "u_hist"
    club_id = "c_hist"
    _bootstrap_club(session, user_id=user_id, club_id=club_id)

    # Simulate decisions
    living_club_world.simulate_autonomous_staff_decisions(session, user_id, club_id)

    history = living_club_world.get_delegated_decisions_history(session, user_id, club_id, limit=10)
    assert history["club_id"] == club_id
    assert "policy" in history
    assert history["policy"]["mode"] == "balanced"
    assert len(history["decisions"]) >= 5
    for d in history["decisions"]:
        assert "activity_key" in d
        assert "title" in d
        assert "financial_amount_gtex" in d


def test_living_world_stage3_api_routes() -> None:
    session = _session()
    user_id = "u_api_stage3"
    club_id = "c_api_stage3"
    _bootstrap_club(session, user_id=user_id, club_id=club_id)

    user = session.get(User, user_id)
    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = lambda: session

    client = TestClient(app)

    # 1. GET /owner/clubs/{club_id}/living-world/dilemmas/active
    r_dil = client.get(f"/owner/clubs/{club_id}/living-world/dilemmas/active")
    assert r_dil.status_code == 200
    dil_data = r_dil.json()
    assert dil_data["status"] == "open"
    dilemma_id = dil_data["dilemma_id"]

    # 2. POST /owner/clubs/{club_id}/living-world/dilemmas/{dilemma_id}/resolve
    r_res = client.post(
        f"/owner/clubs/{club_id}/living-world/dilemmas/{dilemma_id}/resolve",
        json={"choice_id": "ratify_performance_compromise", "decision_note": "Approved via API"},
    )
    assert r_res.status_code == 200
    res_data = r_res.json()
    assert res_data["dilemma"]["status"] == "resolved"

    # 3. POST /owner/clubs/{club_id}/living-world/autonomous-decisions/simulate
    r_sim = client.post(
        f"/owner/clubs/{club_id}/living-world/autonomous-decisions/simulate",
        json={"dry_run": False},
    )
    assert r_sim.status_code == 200
    sim_data = r_sim.json()
    assert sim_data["simulated_count"] > 0

    # 4. GET /owner/clubs/{club_id}/living-world/delegated-decisions
    r_dec = client.get(f"/owner/clubs/{club_id}/living-world/delegated-decisions?limit=10")
    assert r_dec.status_code == 200
    dec_data = r_dec.json()
    assert len(dec_data["decisions"]) > 0
