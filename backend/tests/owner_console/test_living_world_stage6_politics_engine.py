"""GTEX Living Football World - Stage 6
Test Suite: Living Football World Governance, Politics & Consequences Engine
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
from app.owner_console import living_club_world, living_politics_engine, router as owner_router
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubEvent,
    OwnerClubRelationship,
    OwnerClubState,
    OwnerSquadPlayer,
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
            LedgerAccount.__table__,
            LedgerBalanceProjection.__table__,
            LedgerEntry.__table__,
            LedgerTransaction.__table__,
            *OWNER_CONSOLE_TABLES,
        ],
    )
    return sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)()


def _bootstrap_club(
    session: Session, user_id: str, club_id: str, prestige: int = 70
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
        world_day=12,
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
                "medical_director": {
                    "id": "staff_med_default",
                    "name": "Dr. Chidi Obi",
                    "role": "Medical Director",
                    "rating": 82,
                    "mood": 80,
                },
                "head_of_youth_development": {
                    "id": "staff_hoyd_default",
                    "name": "Kunle Adeyemi",
                    "role": "Head of Youth Development",
                    "rating": 81,
                    "mood": 78,
                },
            },
            "medical_level": 3,
            "academy_level": 3,
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

    # Seed initial bilateral relationships using canonical pairing_key
    med_rel = OwnerClubRelationship(
        club_id=club_id,
        pairing_key=living_club_world.pairing_key(club_id, f"owner:{user_id}", "medical_director:staff_med_default"),
        participant_a_type="owner",
        participant_a_id=f"owner:{user_id}",
        participant_a_name=u.username,
        participant_b_type="staff",
        participant_b_id="medical_director:staff_med_default",
        participant_b_name="Dr. Chidi Obi",
        trust=65,
        respect=70,
        affinity=60,
        tension=15,
        alignment=70,
        influence=65,
        loyalty=75,
        status="active",
    )
    mgr_rel = OwnerClubRelationship(
        club_id=club_id,
        pairing_key=living_club_world.pairing_key(club_id, f"owner:{user_id}", "first_team_manager:staff_mgr_1"),
        participant_a_type="owner",
        participant_a_id=f"owner:{user_id}",
        participant_a_name=u.username,
        participant_b_type="staff",
        participant_b_id="first_team_manager:staff_mgr_1",
        participant_b_name="Emmanuel Amuneke",
        trust=70,
        respect=75,
        affinity=65,
        tension=18,
        alignment=72,
        influence=75,
        loyalty=80,
        status="active",
    )
    session.add_all([med_rel, mgr_rel])
    session.flush()

    # Seed baseline squad players
    p1 = OwnerSquadPlayer(
        id=f"p_star_{club_id}",
        club_id=club_id,
        name="Chukwudi Agbo",
        position="ST",
        age=26,
        rating=82,
        potential=85,
        value_coin=Decimal("150000"),
        morale=75,
        minutes=900,
        injured_days=0,
    )
    p2 = OwnerSquadPlayer(
        id=f"p_inj_{club_id}",
        club_id=club_id,
        name="Victor Onyema",
        position="CM",
        age=24,
        rating=79,
        potential=83,
        value_coin=Decimal("95000"),
        morale=70,
        minutes=720,
        injured_days=4,  # Injured player for medical return dispute
    )
    p3 = OwnerSquadPlayer(
        id=f"p_unhappy_{club_id}",
        club_id=club_id,
        name="Kingsley Madu",
        position="LB",
        age=22,
        rating=74,
        potential=80,
        value_coin=Decimal("45000"),
        morale=48,  # Unhappy player for captain intermediary
        minutes=110,
        injured_days=0,
    )
    session.add_all([p1, p2, p3])
    session.flush()

    return u, cp, state


# ==============================================================================
# Unit & Integration Tests
# ==============================================================================


def test_club_politics_overview_initialization():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_pol_1", "c_pol_1", prestige=72)

    overview = living_politics_engine.get_club_politics_overview(session, u.id, cp.id)

    assert overview["club_id"] == cp.id
    assert overview["world_day"] == 12

    # Verify board members
    board = overview["board_politics"]
    assert board["board_confidence"] >= 70
    assert len(board["directors"]) == 4
    chair = next((d for d in board["directors"] if d["archetype"] == "traditionalist"), None)
    assert chair is not None
    assert chair["name"] == "Sir Adebayo Adeleke"
    assert chair["influence_weight"] == 85

    # Verify dressing room & squad players
    dressing = overview["dressing_room"]
    assert dressing["squad_size"] == 3
    assert dressing["injured_players_count"] == 1
    assert len(dressing["unhappy_players"]) == 1
    assert dressing["unhappy_players"][0]["name"] == "Kingsley Madu"

    # Verify medical & youth development
    assert overview["medical_department"]["director"]["name"] == "Dr. Chidi Obi"
    assert overview["youth_development"]["hoyd"]["name"] == "Kunle Adeyemi"

    # Verify supporter sentiment
    assert overview["supporter_sentiment"]["confidence"] >= 70
    assert overview["supporter_sentiment"]["atmosphere_multiplier"] >= 1.0


def test_evaluate_political_cycle_triggers_medical_clearance_dispute():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_pol_2", "c_pol_2", prestige=70)

    res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)

    assert res["club_id"] == cp.id
    assert res["events_evaluated"] >= 1

    # Check that medical dispute event was generated
    events = session.scalars(
        select(OwnerClubEvent).where(
            OwnerClubEvent.club_id == cp.id,
            OwnerClubEvent.category == "medical",
        )
    ).all()
    assert len(events) >= 1
    med_event = events[0]
    assert "Victor Onyema" in med_event.title
    assert med_event.status == "awaiting_decision"
    assert len(med_event.actions_json) == 2


def test_resolve_medical_dispute_back_medical_protocol():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_pol_3", "c_pol_3", prestige=70)

    cycle_res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)
    med_event_id = next((e["id"] for e in cycle_res["new_events"] if e["type"] == "medical"), None)
    assert med_event_id is not None

    resolve_res = living_politics_engine.resolve_political_event(
        session, u.id, cp.id, event_id=med_event_id, action_id="back_medical", note="Follow doctor instructions"
    )

    assert resolve_res["success"] is True
    assert resolve_res["action_taken"] == "back_medical"
    assert "Protected under full recovery protocol" in resolve_res["delta_report"]["player_injury_status"]

    # Verify medical director relationship trust increased
    med_rel = session.scalars(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == cp.id,
            OwnerClubRelationship.pairing_key
            == living_club_world.pairing_key(cp.id, f"owner:{u.id}", "medical_director:staff_med_default"),
        )
    ).first()
    assert med_rel.trust == 70  # Baseline 65 + 5


def test_resolve_medical_dispute_rush_player_triggers_recurrence_penalty():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_pol_4", "c_pol_4", prestige=70)

    cycle_res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)
    med_event_id = next((e["id"] for e in cycle_res["new_events"] if e["type"] == "medical"), None)
    assert med_event_id is not None

    resolve_res = living_politics_engine.resolve_political_event(
        session, u.id, cp.id, event_id=med_event_id, action_id="rush_player", note="Need him on pitch now"
    )

    assert resolve_res["success"] is True
    assert resolve_res["delta_report"]["reinjury_recurrence"] is True

    # Verify player injured days increased by penalty (4 + 14 = 18)
    player = session.get(OwnerSquadPlayer, f"p_inj_{cp.id}")
    assert player.injured_days == 18

    # Verify medical director trust dropped and tension spiked
    med_rel = session.scalars(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == cp.id,
            OwnerClubRelationship.pairing_key
            == living_club_world.pairing_key(cp.id, f"owner:{u.id}", "medical_director:staff_med_default"),
        )
    ).first()
    assert med_rel.trust == 55  # 65 - 10
    assert med_rel.tension == 27  # 15 + 12


def test_evaluate_and_resolve_captain_grievance():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_pol_5", "c_pol_5", prestige=70)

    cycle_res = living_politics_engine.evaluate_political_cycle(session, u.id, cp.id)
    squad_event_id = next((e["id"] for e in cycle_res["new_events"] if e["type"] == "squad"), None)
    assert squad_event_id is not None

    # Resolve by pledging rotation to captain
    res = living_politics_engine.resolve_political_event(
        session, u.id, cp.id, event_id=squad_event_id, action_id="pledge_rotation"
    )

    assert res["success"] is True
    assert res["delta_report"]["player_morale"] == "+12"

    # Check unhappy player morale was boosted
    player = session.get(OwnerSquadPlayer, f"p_unhappy_{cp.id}")
    assert player.morale == 60  # 48 + 12


def test_dispatch_owner_media_statement_vote_of_confidence():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_pol_6", "c_pol_6", prestige=70)

    stmt_res = living_politics_engine.dispatch_owner_media_statement(
        session, u.id, cp.id, statement_type="vote_of_confidence", custom_text="We have absolute faith in Emmanuel."
    )

    assert stmt_res["success"] is True
    assert stmt_res["statement_type"] == "vote_of_confidence"

    # Manager trust should have increased
    mgr_rel = session.scalars(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == cp.id,
            OwnerClubRelationship.pairing_key
            == living_club_world.pairing_key(cp.id, f"owner:{u.id}", "first_team_manager:staff_mgr_1"),
        )
    ).first()
    assert mgr_rel.trust == 77  # Baseline 70 + 7
    assert mgr_rel.tension == 13  # Baseline 18 - 5

    # Check active rumours headline was registered
    overview = living_politics_engine.get_club_politics_overview(session, u.id, cp.id)
    headlines = overview["media_and_rumours"]["active_rumours"]
    assert len(headlines) >= 1
    assert "Vote Of Confidence" in headlines[0]["headline"]


def test_router_living_world_politics_endpoints():
    session = _session()
    u, cp, state = _bootstrap_club(session, "u_router_pol", "c_router_pol", prestige=75)

    app = FastAPI()
    app.include_router(owner_router.router)
    app.dependency_overrides[get_current_user] = lambda: u
    app.dependency_overrides[get_session] = lambda: session

    client = TestClient(app)

    # 1. GET overview
    res_get = client.get(f"/owner/clubs/{cp.id}/living-world/politics/overview")
    assert res_get.status_code == 200, res_get.text
    data = res_get.json()
    assert data["club_id"] == cp.id
    assert "board_politics" in data
    assert "dressing_room" in data
    assert "medical_department" in data

    # 2. POST evaluate-cycle
    res_eval = client.post(f"/owner/clubs/{cp.id}/living-world/politics/events/evaluate-cycle")
    assert res_eval.status_code == 200, res_eval.text
    eval_data = res_eval.json()
    assert "events_evaluated" in eval_data

    # 3. POST event respond
    if eval_data.get("new_events"):
        event_id = eval_data["new_events"][0]["id"]
        res_resp = client.post(
            f"/owner/clubs/{cp.id}/living-world/politics/events/{event_id}/respond",
            json={"action_id": "back_medical", "decision_note": "Medical protocol is paramount."},
        )
        assert res_resp.status_code == 200, res_resp.text
        assert res_resp.json()["success"] is True

    # 4. POST media statement
    res_stmt = client.post(
        f"/owner/clubs/{cp.id}/living-world/politics/media/statement",
        json={"statement_type": "praise_youth_academy", "custom_text": "Our future lies in our academy stars."},
    )
    assert res_stmt.status_code == 200, res_stmt.text
    assert res_stmt.json()["success"] is True
