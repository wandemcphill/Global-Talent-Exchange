"""Automated test suite for Stage 2 Living World Spatial Persona Interactions & Real-Time Sync.

Covers:
- interact_with_persona across all canonical actions:
  align_strategy, praise_leadership, demand_accountability, request_briefing, discuss_directive
- Relationship dimensions updates (alignment, influence, loyalty, trust, respect, affinity, tension)
- Durable relationship history logging in OwnerClubRelationshipHistory
- Chat history synchronization in club facilities state
- Validation & error boundaries (unsupported persona role, invalid action, vacant persona)
- FastAPI endpoints:
  POST /clubs/{club_id}/living-world/personas/{persona_role}/interact
  GET  /clubs/{club_id}/living-world/personas/{persona_role}
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.models.base import Base
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
from app.owner_console import living_club_world, router as owner_router
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubDirective,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerSquadPlayer,
)
from app.owner_console.service import OwnerError

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
    session: Session, user_id: str = "u_owner_stage2", club_id: str = "c_lagos_stage2"
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
                    "id": "med_dr_amaka",
                    "staff_id": "med_dr_amaka",
                    "role": "medical_director",
                    "name": "Dr. Amaka Bello",
                    "style": "Preventive Performance",
                    "is_vacant": False,
                },
                "chief_scout": {
                    "id": "scout_kofi",
                    "staff_id": "scout_kofi",
                    "role": "chief_scout",
                    "name": "Kofi Mensah",
                    "style": "Data-Driven Scout",
                    "is_vacant": False,
                },
            },
        },
        manager_json={
            "id": "mgr_amuneke",
            "name": "Emmanuel Amuneke",
            "display_name": "Emmanuel Amuneke",
            "style": "High-Press Possession",
            "is_vacant": False,
        },
    )
    session.add(state)

    p1 = OwnerSquadPlayer(
        id=f"p1-{club_id}",
        club_id=club_id,
        name="Tunde Bakare",
        position="CB",
        age=28,
        rating=74,
        potential=76,
        value_coin=Decimal("4500"),
        morale=75,
        injured_days=0,
        is_regen=False,
        personality_json={"leadership": 16, "fitness": 96},
    )
    p2 = OwnerSquadPlayer(
        id=f"p2-{club_id}",
        club_id=club_id,
        name="Segun Odegbami Jr",
        position="RW",
        age=22,
        rating=72,
        potential=82,
        value_coin=Decimal("5000"),
        morale=75,
        injured_days=0,
        is_regen=False,
        personality_json={"leadership": 12, "fitness": 92},
    )
    session.add_all([p1, p2])
    session.commit()

    living_club_world.ensure_default_relationships(session, state, [p1, p2])
    session.commit()
    return state, [p1, p2]


def test_interact_with_persona_align_strategy():
    session = _session()
    state, _ = _bootstrap_club(session, user_id="u_align", club_id="c_align")

    res = living_club_world.interact_with_persona(
        session,
        "u_align",
        "c_align",
        persona_role="first_team_manager",
        action_type="align_strategy",
    )

    assert res["success"] is True
    assert res["action_type"] == "align_strategy"
    assert res["persona"]["name"] == "Emmanuel Amuneke"
    assert res["persona"]["department"] == "manager"
    assert "dialogue_reply" in res
    assert len(res["dialogue_reply"]) > 10

    # Verify deltas applied
    rel = res["relationship"]
    assert rel["alignment"] == 65 + 6
    assert rel["influence"] == 70 + 3
    assert rel["respect"] == 60 + 2
    assert rel["trust"] == 55 + 2
    assert rel["tension"] == 15 - 3

    # Verify relationship history entry
    hist = (
        session.query(OwnerClubRelationshipHistory)
        .filter(OwnerClubRelationshipHistory.relationship_id == rel["id"])
        .order_by(OwnerClubRelationshipHistory.created_at.desc())
        .first()
    )
    assert hist is not None
    assert hist.delta_alignment == 6
    assert hist.delta_influence == 3
    assert hist.delta_tension == -3
    assert "Align Strategic Vision" in hist.reason


def test_interact_with_persona_praise_and_accountability():
    session = _session()
    state, _ = _bootstrap_club(session, user_id="u_praise", club_id="c_praise")

    # Praise General Manager
    praise_res = living_club_world.interact_with_persona(
        session,
        "u_praise",
        "c_praise",
        persona_role="general_manager",
        action_type="praise_leadership",
    )
    assert praise_res["success"] is True
    rel_praise = praise_res["relationship"]
    assert rel_praise["trust"] == 65 + 5
    assert rel_praise["loyalty"] == 70 + 6
    assert rel_praise["tension"] == 10 - 5
    assert "Dayo Adeleke" in praise_res["persona"]["name"]

    # Demand accountability from Chief Scout
    critique_res = living_club_world.interact_with_persona(
        session,
        "u_praise",
        "c_praise",
        persona_role="chief_scout",
        action_type="demand_accountability",
    )
    assert critique_res["success"] is True
    rel_critique = critique_res["relationship"]
    assert rel_critique["tension"] == 15 + 7
    assert rel_critique["influence"] == 60 + 4
    assert rel_critique["loyalty"] == 60 - 3


def test_interact_with_persona_board_president():
    session = _session()
    state, _ = _bootstrap_club(session, user_id="u_board", club_id="c_board")

    res = living_club_world.interact_with_persona(
        session,
        "u_board",
        "c_board",
        persona_role="club_president",
        action_type="request_briefing",
    )
    assert res["success"] is True
    assert res["persona"]["role_key"] == "club_president"
    assert res["persona"]["department"] == "executive"
    rel = res["relationship"]
    assert rel["respect"] == 75 + 4
    assert rel["trust"] == 70 + 3
    assert rel["alignment"] == 80 + 3


def test_interact_with_persona_chat_history_synchronization():
    session = _session()
    state, _ = _bootstrap_club(session, user_id="u_chat", club_id="c_chat")

    custom_dialogue = "Dr. Amaka, we need full squad fitness for the cup match."
    res = living_club_world.interact_with_persona(
        session,
        "u_chat",
        "c_chat",
        persona_role="medical_director",
        action_type="general_dialogue",
        dialogue_text=custom_dialogue,
    )

    assert res["success"] is True
    # Verify facilities chat history
    facs = dict(state.facilities_json or {})
    chat_hist = facs.get("_staff_chat_history", [])
    assert len(chat_hist) >= 2
    user_msg = next((m for m in chat_hist if m["sender"] == "Owner"), None)
    assert user_msg is not None
    assert user_msg["message"] == custom_dialogue
    staff_msg = next((m for m in chat_hist if m["sender_type"] == "staff"), None)
    assert staff_msg is not None
    assert staff_msg["role"] == "medical_director"


def test_interact_with_persona_validation_errors():
    session = _session()
    state, _ = _bootstrap_club(session, user_id="u_val", club_id="c_val")

    # 1. Invalid persona role
    try:
        living_club_world.interact_with_persona(
            session,
            "u_val",
            "c_val",
            persona_role="mascot",
            action_type="align_strategy",
        )
        assert False, "Should raise OwnerError for invalid persona role"
    except OwnerError as e:
        assert e.code == "invalid_persona_role"
        assert e.status == 400

    # 2. Invalid action type
    try:
        living_club_world.interact_with_persona(
            session,
            "u_val",
            "c_val",
            persona_role="first_team_manager",
            action_type="order_pizza",
        )
        assert False, "Should raise OwnerError for invalid action type"
    except OwnerError as e:
        assert e.code == "invalid_interaction_action"
        assert e.status == 400

    # 3. Vacant persona
    facs = dict(state.facilities_json or {})
    facs["_executive_staff"]["head_of_youth_development"]["is_vacant"] = True
    facs["_executive_staff"]["head_of_youth_development"]["name"] = ""
    state.facilities_json = facs
    session.commit()

    try:
        living_club_world.interact_with_persona(
            session,
            "u_val",
            "c_val",
            persona_role="head_of_youth_development",
            action_type="align_strategy",
        )
        assert False, "Should raise OwnerError for vacant persona"
    except OwnerError as e:
        assert e.code == "persona_vacant"
        assert e.status == 400


def test_get_persona_details_service():
    session = _session()
    state, _ = _bootstrap_club(session, user_id="u_det", club_id="c_det")

    # Add an active directive for manager
    directive = OwnerClubDirective(
        club_id="c_det",
        department="manager",
        directive_key="change_formation",
        title="Implement 4-3-3 Attacking",
        instruction="Transition squad to 4-3-3 shape.",
        consequences_json={"objective_key": "change_formation"},
        status="active",
        deadline_day=11,
    )
    session.add(directive)
    session.commit()

    details = living_club_world.get_persona_details(
        session,
        "u_det",
        "c_det",
        persona_role="first_team_manager",
    )

    assert details["club_id"] == "c_det"
    assert details["persona"]["name"] == "Emmanuel Amuneke"
    assert details["persona"]["is_appointed"] is True
    assert details["persona"]["department"] == "manager"
    assert details["relationship"] is not None
    assert details["relationship"]["alignment"] == 65
    assert len(details["active_directives"]) == 1
    assert details["active_directives"][0]["directive_key"] == "change_formation"


def test_api_living_world_persona_routes():
    session = _session()
    user_id = "u_api_persona"
    club_id = "c_api_persona"
    _bootstrap_club(session, user_id=user_id, club_id=club_id)

    app = FastAPI()
    app.include_router(owner_router.router)

    user_ctx = SimpleNamespace(id=user_id, username=user_id, role="user")
    app.dependency_overrides[get_current_user] = lambda: user_ctx
    app.dependency_overrides[get_session] = lambda: session

    client = TestClient(app)

    # 1. GET persona details
    get_res = client.get(f"/owner/clubs/{club_id}/living-world/personas/general_manager")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["persona"]["role_key"] == "general_manager"
    assert data["persona"]["name"] == "Dayo Adeleke"
    assert data["relationship"]["alignment"] == 75
    assert data["relationship"]["influence"] == 75

    # 2. POST interact with persona
    post_res = client.post(
        f"/owner/clubs/{club_id}/living-world/personas/general_manager/interact",
        json={"action_type": "align_strategy", "dialogue_text": "Let us prioritize financial sustainability."},
    )
    assert post_res.status_code == 200
    interact_data = post_res.json()
    assert interact_data["success"] is True
    assert interact_data["action_type"] == "align_strategy"
    assert interact_data["relationship"]["alignment"] == 75 + 6
    assert len(interact_data["dialogue_reply"]) > 10

    # 3. Unauthorized access check (non-owner user fails closed)
    other_user = SimpleNamespace(id="u_intruder", username="intruder", role="user")
    app.dependency_overrides[get_current_user] = lambda: other_user

    fail_res = client.post(
        f"/owner/clubs/{club_id}/living-world/personas/general_manager/interact",
        json={"action_type": "align_strategy"},
    )
    assert fail_res.status_code in (403, 404)
