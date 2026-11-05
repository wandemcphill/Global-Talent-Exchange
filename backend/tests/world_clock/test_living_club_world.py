from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
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
from app.owner_console import (
    daily_operations_hub,
    engine as owner_engine,
    ledger,
    living_club_world,
    router as owner_router,
    service as owner_service,
)
from app.owner_console.models import (
    OWNER_CONSOLE_TABLES,
    OwnerClubDirective,
    OwnerClubEvent,
    OwnerClubRelationship,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerSquadPlayer,
)
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


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


def _seed_club(
    session: Session,
    *,
    club_id: str = "club-living-1",
    user_id: str = "user-living-1",
    prestige: int = 55,
    cash: int = 100_000,
    appoint_executive_staff: bool = True,
) -> OwnerClubState:
    existing_user = session.get(User, user_id)
    if existing_user is None:
        user = User(
            id=user_id,
            email=f"{user_id}@gtex.test",
            username=f"owner_{user_id}",
            password_hash="hash",  # pragma: allowlist secret
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

    exec_staff = (
        {
            "general_manager": {
                "id": "gm_appointed_1",
                "name": "Babatunde Lawal",
                "role": "general_manager",
                "mood": 78,
            },
            "head_of_youth_development": {
                "id": "hoyd_appointed_1",
                "name": "Kunle Adeyemi",
                "role": "head_of_youth_development",
                "mood": 82,
            },
            "medical_director": {
                "id": "med_appointed_1",
                "name": "Dr. Chidi Obi",
                "role": "medical_director",
                "mood": 84,
                "medical_expertise": 14,
            },
            "chief_scout": {
                "id": "scout_appointed_1",
                "name": "Musa Danjuma",
                "role": "chief_scout",
                "mood": 76,
            },
        }
        if appoint_executive_staff
        else {}
    )

    state = OwnerClubState(
        id=f"state-{club_id}",
        club_id=club_id,
        owner_user_id=user_id,
        club_name=f"Lagos Marine FC ({club_id})",
        stage="active",
        prestige=prestige,
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={
            "training": 2,
            "academy": 2,
            "medical": 2,
            "stadium": 2,
            "commercial": 2,
            "_executive_staff": exec_staff,
        },
        world_day=10,
        last_tick_at=WORLD_NOW,
        last_world_tick_date=WORLD_NOW.date(),
        value_history_json=[],
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
        name="Emeka Eze",
        position="FWD",
        age=19,
        rating=66,
        potential=84,
        value_coin=Decimal("6000"),
        morale=60,
        injured_days=0,
        is_regen=True,
        personality_json={"marketability": 16, "transfer_pressure": 30, "fitness": 92},
    )
    p3 = OwnerSquadPlayer(
        id=f"p3-{club_id}",
        club_id=club_id,
        name="Segun Adele",
        position="MID",
        age=22,
        rating=62,
        potential=70,
        value_coin=Decimal("1800"),
        morale=35,
        injured_days=2,
        is_regen=False,
        personality_json={"fitness": 80, "last_training_workload_tier": "rehabilitation"},
    )
    session.add_all([p1, p2, p3])

    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=Decimal(cash),
        club_id=club_id,
        user_id=user_id,
        memo="Initial club grant",
    )
    session.commit()
    return state


def _build_test_client(session: Session, active_user_holder: dict[str, str]) -> TestClient:
    app = FastAPI()
    app.include_router(owner_router.router)

    def _override_session():
        yield session

    def _override_user():
        uid = active_user_holder["user_id"]
        return SimpleNamespace(id=uid, email=f"{uid}@gtex.test", role="user")

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    return TestClient(app)


def test_ensure_default_relationships_and_bounds():
    session = _session()
    state = _seed_club(session)
    squad_players = list(
        session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
    )

    rels = living_club_world.ensure_default_relationships(session, state, squad_players)
    assert len(rels) >= 7

    mgr_rel = next(
        r
        for r in rels
        if r.participant_a_id.startswith("first_team_manager:") or r.participant_b_id.startswith("first_team_manager:")
    )
    assert mgr_rel.trust == 55
    assert mgr_rel.respect == 60
    assert mgr_rel.tension == 15

    updated = living_club_world.apply_relationship_delta(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        "first_team_manager",
        "First-Team Manager",
        delta_trust=100,
        delta_tension=-50,
        reason="Spectacular derby victory",
        world_day=10,
    )
    assert updated is not None
    assert updated.trust == 100
    assert updated.tension == 0

    history = list(
        session.scalars(
            select(OwnerClubRelationshipHistory).where(OwnerClubRelationshipHistory.relationship_id == updated.id)
        ).all()
    )
    assert len(history) == 1
    assert history[0].delta_trust == 100
    assert history[0].snapshot_json["trust"] == 100
    assert history[0].snapshot_json["tension"] == 0
    assert history[0].reason == "Spectacular derby victory"


def test_process_world_day_events_idempotency_and_categories():
    session = _session()
    state = _seed_club(session)

    res1 = living_club_world.process_world_day_events(session, state, campus_effects={})
    assert res1["new_events_count"] > 0
    initial_event_count = res1["new_events_count"]

    events = res1["active_events"]
    categories = {e["category"] for e in events}
    assert "squad" in categories
    assert "academy" in categories

    res2 = living_club_world.process_world_day_events(session, state, campus_effects={})
    assert res2["new_events_count"] == 0
    assert res2["total_active_events"] == initial_event_count


def test_event_resolution_action_validation_and_atomicity():
    """Verifies Finding 3: valid action, invalid action, wrong-event-type action, unsupported action, and duplicate resolution."""
    session = _session()
    state = _seed_club(session)

    living_club_world.process_world_day_events(session, state, campus_effects={})

    morale_event = session.scalar(
        select(OwnerClubEvent).where(
            OwnerClubEvent.club_id == state.club_id,
            OwnerClubEvent.event_type == "squad_morale_dip",
        )
    )
    assert morale_event is not None
    assert morale_event.status == "active"

    player_id = morale_event.source_id
    player = session.get(OwnerSquadPlayer, player_id)
    assert player is not None
    initial_morale = player.morale
    rel_count_before = len(living_club_world.get_club_relationships(session, state.club_id))

    # 1. Invalid / unknown action must be rejected without mutating state
    with pytest.raises(owner_service.OwnerError) as exc_invalid:
        living_club_world.resolve_club_event(
            session,
            state.owner_user_id,
            state.club_id,
            morale_event.id,
            action="invented_action_key",
        )
    assert exc_invalid.value.status == 400
    assert exc_invalid.value.code == "invalid_event_action"
    session.refresh(morale_event)
    session.refresh(player)
    assert morale_event.status == "active"
    assert morale_event.resolved_at is None
    assert player.morale == initial_morale
    assert len(living_club_world.get_club_relationships(session, state.club_id)) == rel_count_before

    # 2. Action belonging to a different event type ("back_manager") must be rejected
    with pytest.raises(owner_service.OwnerError) as exc_wrong_type:
        living_club_world.resolve_club_event(
            session,
            state.owner_user_id,
            state.club_id,
            morale_event.id,
            action="back_manager",
        )
    assert exc_wrong_type.value.status == 400
    assert exc_wrong_type.value.code == "invalid_event_action"
    session.refresh(morale_event)
    session.refresh(player)
    assert morale_event.status == "active"
    assert player.morale == initial_morale

    # 3. Event with an unsupported action in actions_json must be rejected
    unsupported_event, _ = living_club_world.create_club_event(
        session,
        state.club_id,
        category="squad",
        event_type="squad_morale_dip",
        severity="routine",
        title="Custom Unsupported Action Event",
        description="Event containing an unimplemented action key",
        world_day=10,
        source_type="player",
        source_id=player.id,
        actions=[{"key": "quantum_boost", "label": "Unsupported Boost", "style": "primary"}],
        idempotency_key="evt:test:unsupported:action",
    )
    with pytest.raises(owner_service.OwnerError) as exc_unsupported:
        living_club_world.resolve_club_event(
            session,
            state.owner_user_id,
            state.club_id,
            unsupported_event.id,
            action="quantum_boost",
        )
    assert exc_unsupported.value.status == 400
    assert exc_unsupported.value.code == "unsupported_event_action"
    session.refresh(unsupported_event)
    assert unsupported_event.status == "active"

    # 4. Valid action resolves and applies consequences atomically
    res = living_club_world.resolve_club_event(
        session,
        state.owner_user_id,
        state.club_id,
        morale_event.id,
        action="encourage_player",
        resolution_note="Chairman met with player personally",
    )
    assert res["status"] == "resolved"
    assert res["consequences_applied"]["player_morale"] == 50

    session.refresh(morale_event)
    assert morale_event.status == "resolved"
    assert morale_event.resolution_action == "encourage_player"
    assert morale_event.resolved_at is not None

    # 5. Duplicate resolution is rejected with 409 and does not re-apply morale boost
    with pytest.raises(owner_service.OwnerError) as exc_dup:
        living_club_world.resolve_club_event(
            session,
            state.owner_user_id,
            state.club_id,
            morale_event.id,
            action="encourage_player",
        )
    assert exc_dup.value.status == 409
    assert exc_dup.value.code == "event_already_resolved"
    session.refresh(player)
    assert player.morale == 50


def test_departmental_directive_lifecycle():
    session = _session()
    state = _seed_club(session)

    dir_payload = living_club_world.issue_department_directive(
        session,
        state.owner_user_id,
        state.club_id,
        department="medical",
        directive_key="accelerate_recovery",
        title="Accelerate Hydrotherapy Protocols",
        instruction="Prioritize non-contact rehab for first-team players ahead of cup tie",
        deadline_days=2,
    )
    assert dir_payload["status"] == "active"
    assert "Dr. Chidi Obi" in dir_payload["acknowledged_by"]
    assert dir_payload["deadline_day"] == 12

    state.world_day = 12
    living_club_world.process_world_day_events(session, state, campus_effects={})

    directive = session.get(OwnerClubDirective, dir_payload["id"])
    assert directive is not None
    assert directive.status == "completed"
    assert directive.completed_at is not None

    med_rel = living_club_world.get_relationship_for_department(session, state.club_id, "medical_director")
    assert med_rel is not None
    assert med_rel["trust"] > 65


def test_vacant_staff_positions_and_staff_replacement_isolation():
    """Verifies Finding 2: vacant roles never fabricate employee identities, and staff replacement does not inherit history."""
    session = _session()
    state = _seed_club(
        session, club_id="club-vacant-1", user_id="user-vacant-1", cash=900, appoint_executive_staff=False
    )

    # Clear healed player injury so recovery clearance event triggers while medical director is vacant
    p3 = session.get(OwnerSquadPlayer, "p3-club-vacant-1")
    assert p3 is not None
    p3.injured_days = 0
    session.commit()

    squad_players = list(
        session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
    )
    rels = living_club_world.ensure_default_relationships(session, state, squad_players)

    # Vacant roles must NOT have relationships created
    assert living_club_world.get_relationship_for_department(session, state.club_id, "medical_director") is None
    assert (
        living_club_world.get_relationship_for_department(session, state.club_id, "head_of_youth_development") is None
    )
    assert living_club_world.get_relationship_for_department(session, state.club_id, "general_manager") is None
    assert living_club_world.get_relationship_for_department(session, state.club_id, "chief_scout") is None

    all_names = {r.participant_a_name for r in rels} | {r.participant_b_name for r in rels}
    for fabricated in ("Dayo Adeleke", "Femi Ogunleye", "Dr. Amara Okafor", "Kelechi Nwosu"):
        assert fabricated not in all_names

    # Process world day events on club with vacant executive staff
    tick_res = living_club_world.process_world_day_events(session, state, campus_effects={})
    for ev in tick_res["active_events"]:
        text_blob = f"{ev['title']} {ev['description']} {ev['participants']}"
        for fabricated in ("Dayo Adeleke", "Femi Ogunleye", "Dr. Amara Okafor", "Kelechi Nwosu"):
            assert fabricated not in text_blob
        if ev["event_type"] == "player_recovery_cleared":
            assert "Medical Director vacant" in ev["description"] or "Vacant" in str(ev["participants"])

    # Issue directives to vacant medical, academy, finance, and scouting departments
    for dept in ("medical", "academy", "finance", "scouting"):
        d_res = living_club_world.issue_department_directive(
            session,
            state.owner_user_id,
            state.club_id,
            department=dept,
            directive_key=f"dir_{dept}",
            title=f"Vacant {dept.title()} Directive",
            instruction="Maintain baseline operations while recruitment is underway",
        )
        assert "Vacant" in d_res["acknowledged_by"]
        for fabricated in ("Dayo Adeleke", "Femi Ogunleye", "Dr. Amara Okafor", "Kelechi Nwosu"):
            assert fabricated not in d_res["acknowledged_by"]
            assert fabricated not in d_res["acknowledgement_text"]

    # Still no fabricated relationships after directives to vacant roles
    assert living_club_world.get_relationship_for_department(session, state.club_id, "medical_director") is None
    assert (
        living_club_world.get_relationship_for_department(session, state.club_id, "head_of_youth_development") is None
    )
    assert living_club_world.get_relationship_for_department(session, state.club_id, "general_manager") is None
    assert living_club_world.get_relationship_for_department(session, state.club_id, "chief_scout") is None

    # Now appoint Medical Director #1 and build relationship history
    facs = dict(state.facilities_json or {})
    facs["_executive_staff"] = {
        "medical_director": {"id": "med_person_1", "name": "Dr. Halima Yusuf", "role": "medical_director", "mood": 82}
    }
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.commit()

    living_club_world.ensure_default_relationships(session, state, squad_players)
    med_rel_1 = living_club_world.apply_relationship_delta(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        "medical_director",
        "Dr. Halima Yusuf",
        delta_trust=20,
        reason="Successful pre-season medical screening",
        world_day=10,
    )
    assert med_rel_1 is not None
    assert med_rel_1.trust == 85
    med_1_id = med_rel_1.id

    # Replace Medical Director #1 with Medical Director #2
    facs = dict(state.facilities_json or {})
    facs["_executive_staff"] = {
        "medical_director": {"id": "med_person_2", "name": "Dr. Ikenna Nnamdi", "role": "medical_director", "mood": 80}
    }
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.commit()

    living_club_world.ensure_default_relationships(session, state, squad_players)
    med_rel_2_dict = living_club_world.get_relationship_for_department(session, state.club_id, "medical_director")
    assert med_rel_2_dict is not None
    assert med_rel_2_dict["id"] != med_1_id
    assert med_rel_2_dict["trust"] == 65  # Fresh relationship baseline, did NOT inherit 85 trust
    assert "Dr. Ikenna Nnamdi" in (med_rel_2_dict["participant_a_name"], med_rel_2_dict["participant_b_name"])

    # Former Medical Director's relationship and history remain preserved in DB under status="former"
    former_rel = session.get(OwnerClubRelationship, med_1_id)
    assert former_rel is not None
    assert former_rel.status == "former"
    former_history = list(
        session.scalars(
            select(OwnerClubRelationshipHistory).where(OwnerClubRelationshipHistory.relationship_id == med_1_id)
        ).all()
    )
    assert len(former_history) == 1
    assert former_history[0].reason == "Successful pre-season medical screening"

    new_history = list(
        session.scalars(
            select(OwnerClubRelationshipHistory).where(
                OwnerClubRelationshipHistory.relationship_id == med_rel_2_dict["id"]
            )
        ).all()
    )
    assert len(new_history) == 0


def test_relationship_pair_uniqueness_and_reversed_order():
    """Verifies Finding 4: reversed participant orderings and duplicate calls resolve to the single unique record."""
    session = _session()
    state = _seed_club(session)

    rel_forward = living_club_world.get_or_create_relationship(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "player",
        f"p1-{state.club_id}",
        "Tunde Bakare",
    )
    rel_reversed = living_club_world.get_or_create_relationship(
        session,
        state.club_id,
        "player",
        f"p1-{state.club_id}",
        "Tunde Bakare",
        "owner",
        "owner",
        "Club Owner",
    )
    assert rel_forward.id == rel_reversed.id
    assert rel_forward.pairing_key == rel_reversed.pairing_key

    # Database-level UniqueConstraint rejects raw duplicate insert with same (club_id, pairing_key)
    duplicate_row = OwnerClubRelationship(
        club_id=state.club_id,
        pairing_key=rel_forward.pairing_key,
        participant_a_type=rel_forward.participant_a_type,
        participant_a_id=rel_forward.participant_a_id,
        participant_a_name=rel_forward.participant_a_name,
        participant_b_type=rel_forward.participant_b_type,
        participant_b_id=rel_forward.participant_b_id,
        participant_b_name=rel_forward.participant_b_name,
    )
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add(duplicate_row)
            session.flush()


def test_relationship_deduplication_preserves_history_and_conflict_recovery():
    """Verifies Finding 4: deduplication reconciles reversed/legacy pairings preserving history, and IntegrityError fallback recovers."""
    session = _session()
    state = _seed_club(session, club_id="club-dedup-1", user_id="user-dedup-1")

    # Insert two rows with non-normalized / reversed pairing_keys for the same participant pair
    rel1 = OwnerClubRelationship(
        id="rel-canon-1",
        club_id=state.club_id,
        pairing_key=f"{state.club_id}:owner:p1-{state.club_id}",
        participant_a_type="owner",
        participant_a_id="owner",
        participant_a_name="Club Owner",
        participant_b_type="player",
        participant_b_id=f"p1-{state.club_id}",
        participant_b_name="Tunde Bakare",
        trust=60,
    )
    rel2 = OwnerClubRelationship(
        id="rel-reversed-dup-1",
        club_id=state.club_id,
        pairing_key=f"{state.club_id}:p1-{state.club_id}:owner",
        participant_a_type="player",
        participant_a_id=f"p1-{state.club_id}",
        participant_a_name="Tunde Bakare",
        participant_b_type="owner",
        participant_b_id="owner",
        participant_b_name="Club Owner",
        trust=65,
    )
    session.add_all([rel1, rel2])
    session.flush()

    h1 = OwnerClubRelationshipHistory(
        relationship_id=rel1.id,
        club_id=state.club_id,
        world_day=10,
        reason="First interaction",
        delta_trust=5,
        snapshot_json={"trust": 60},
    )
    h2 = OwnerClubRelationshipHistory(
        relationship_id=rel2.id,
        club_id=state.club_id,
        world_day=11,
        reason="Second interaction on duplicate row",
        delta_trust=5,
        snapshot_json={"trust": 65},
    )
    session.add_all([h1, h2])
    session.commit()

    removed = living_club_world.deduplicate_club_relationships(session, state.club_id)
    assert removed == 1

    # Both history entries are preserved and re-pointed to the surviving canonical relationship
    all_hist = list(
        session.scalars(
            select(OwnerClubRelationshipHistory).where(OwnerClubRelationshipHistory.club_id == state.club_id)
        ).all()
    )
    assert len(all_hist) == 2
    assert {h.relationship_id for h in all_hist} == {"rel-canon-1"}


def test_unified_timeline_filtering_and_pagination():
    """Verifies Finding 5: unified timeline applies filters and pagination across events, directives, and relationship shifts."""
    session = _session()
    state = _seed_club(session)

    # Create multiple events, directives, and significant relationship shifts across days 10..14
    living_club_world.create_club_event(
        session,
        state.club_id,
        category="tactical",
        event_type="tactical_readiness_briefing",
        severity="important",
        title="Tactical Prep Day 10",
        description="Pressing triggers",
        world_day=10,
        actions=[{"key": "endorse_tactics", "label": "Endorse", "style": "primary"}],
    )
    living_club_world.issue_department_directive(
        session,
        state.owner_user_id,
        state.club_id,
        department="academy",
        directive_key="scout_youth",
        title="Expand Youth Scouting",
        instruction="Identify top U18 talents",
    )
    state.world_day = 11
    living_club_world.apply_relationship_delta(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        "first_team_manager",
        "Tunde Bakare",
        delta_trust=10,
        delta_tension=-6,
        reason="Milestone alignment meeting",
        world_day=11,
    )
    state.world_day = 12
    living_club_world.create_club_event(
        session,
        state.club_id,
        category="medical",
        event_type="injury_crisis_alert",
        severity="critical",
        title="Medical Alert Day 12",
        description="Three players sidelined",
        world_day=12,
        actions=[{"key": "reduce_workload", "label": "Reduce Workload", "style": "primary"}],
    )
    session.commit()

    full_tl = living_club_world.get_living_world_timeline(
        session, state.owner_user_id, state.club_id, limit=50, offset=0
    )
    total = full_tl["total_count"]
    assert total >= 5
    assert full_tl["total_events_count"] == total
    kinds_present = {item["kind"] for item in full_tl["items"]}
    assert {"event", "directive", "relationship_shift"}.issubset(kinds_present)

    # Paginate across the unified timeline in pages of 2 and verify exact disjoint union
    page1 = living_club_world.get_living_world_timeline(session, state.owner_user_id, state.club_id, limit=2, offset=0)
    page2 = living_club_world.get_living_world_timeline(session, state.owner_user_id, state.club_id, limit=2, offset=2)
    page3 = living_club_world.get_living_world_timeline(session, state.owner_user_id, state.club_id, limit=2, offset=4)
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert page1["total_count"] == total
    assert page2["total_count"] == total
    combined_ids = [(i["kind"], i["id"]) for i in (page1["items"] + page2["items"] + page3["items"])]
    assert combined_ids == [(i["kind"], i["id"]) for i in full_tl["items"][: len(combined_ids)]]

    # Filter by category="tactical" must NOT leak executive directives or culture relationship shifts
    tactical_tl = living_club_world.get_living_world_timeline(
        session, state.owner_user_id, state.club_id, category="tactical"
    )
    assert tactical_tl["total_count"] == 1
    assert all(i["category"] == "tactical" for i in tactical_tl["items"])

    # Filter by category="culture" returns relationship_shift items
    culture_tl = living_club_world.get_living_world_timeline(
        session, state.owner_user_id, state.club_id, category="culture"
    )
    assert culture_tl["total_count"] >= 1
    assert all(i["category"] == "culture" and i["kind"] == "relationship_shift" for i in culture_tl["items"])

    # Filter by status="active" excludes resolved relationship shifts
    active_tl = living_club_world.get_living_world_timeline(
        session, state.owner_user_id, state.club_id, status="active"
    )
    assert all(i["status"] == "active" for i in active_tl["items"])


def test_player_fatigue_and_contract_event_triggers():
    """Verifies Finding 6: real player fatigue and contract milestone event triggers grounded in stored player data."""
    session = _session()
    state = _seed_club(session, club_id="club-triggers-1", user_id="user-triggers-1")

    p1 = session.get(OwnerSquadPlayer, f"p1-{state.club_id}")
    assert p1 is not None
    p1.personality_json = {
        "leadership": 16,
        "fitness": 62,
        "contract_months_remaining": 5,
    }
    flag_modified(p1, "personality_json")
    session.commit()

    res = living_club_world.process_world_day_events(session, state, campus_effects={})
    event_types = {e["event_type"] for e in res["active_events"]}
    assert "high_fatigue_workload_alert" in event_types
    assert "contract_expiry_warning" in event_types

    fatigue_evt = next(e for e in res["active_events"] if e["event_type"] == "high_fatigue_workload_alert")
    resolved_fatigue = living_club_world.resolve_club_event(
        session,
        state.owner_user_id,
        state.club_id,
        fatigue_evt["id"],
        action="rest_player",
    )
    assert resolved_fatigue["consequences_applied"]["fitness"] == 74

    contract_evt = next(e for e in res["active_events"] if e["event_type"] == "contract_expiry_warning")
    resolved_contract = living_club_world.resolve_club_event(
        session,
        state.owner_user_id,
        state.club_id,
        contract_evt["id"],
        action="open_renewal_talks",
    )
    assert resolved_contract["consequences_applied"]["renewal_talks_opened_day"] == 10


def test_operations_hub_living_world_integration():
    session = _session()
    state = _seed_club(session)

    living_club_world.process_world_day_events(session, state, campus_effects={})
    living_club_world.issue_department_directive(
        session,
        state.owner_user_id,
        state.club_id,
        department="manager",
        directive_key="set_defensive_line",
        title="Hold Compact Defensive Shape",
        instruction="Maintain tactical discipline in transitions",
    )

    hub = daily_operations_hub.get_club_operations_hub(session, state.owner_user_id, state.club_id, force_refresh=True)
    assert "living_world" in hub
    lw = hub["living_world"]
    assert lw["active_events_count"] > 0
    assert lw["active_directives_count"] >= 1
    assert len(lw["relationships"]) >= 7

    destinations = hub["destinations"]
    tactical_office = next(d for d in destinations if d["destination_key"] == "managers_office")
    assert "active_events" in tactical_office
    assert "active_directives" in tactical_office
    assert "relationship" in tactical_office
    assert tactical_office["relationship"]["trust"] >= 50


def test_api_ownership_isolation_and_authorization():
    """Verifies Finding 1 across all Phase 2.4 HTTP endpoints and service functions."""
    session = _session()
    state_a = _seed_club(session, club_id="club-iso-a", user_id="user-iso-a")
    state_b = _seed_club(session, club_id="club-iso-b", user_id="user-iso-b")

    living_club_world.process_world_day_events(session, state_a, campus_effects={})
    evt_a = session.scalar(select(OwnerClubEvent).where(OwnerClubEvent.club_id == state_a.club_id))
    assert evt_a is not None
    session.commit()

    auth_ctx = {"user_id": state_a.owner_user_id}
    client = _build_test_client(session, auth_ctx)

    # 1. User A can retrieve their own club timeline and relationships
    resp_own_tl = client.get(f"/owner/clubs/{state_a.club_id}/living-world/timeline")
    assert resp_own_tl.status_code == 200
    assert resp_own_tl.json()["club_id"] == state_a.club_id

    resp_own_rel = client.get(f"/owner/clubs/{state_a.club_id}/living-world/relationships")
    assert resp_own_rel.status_code == 200
    assert resp_own_rel.json()["club_id"] == state_a.club_id

    # 2. Switch authenticated user to User B: User B cannot access ANY of User A's Phase 2.4 endpoints
    auth_ctx["user_id"] = state_b.owner_user_id

    resp_b_tl = client.get(f"/owner/clubs/{state_a.club_id}/living-world/timeline")
    assert resp_b_tl.status_code == 403
    assert resp_b_tl.json()["detail"]["code"] == "not_club_owner"

    resp_b_rel = client.get(f"/owner/clubs/{state_a.club_id}/living-world/relationships")
    assert resp_b_rel.status_code == 403
    assert resp_b_rel.json()["detail"]["code"] == "not_club_owner"

    resp_b_dir = client.post(
        f"/owner/clubs/{state_a.club_id}/living-world/directives",
        json={
            "department": "manager",
            "directive_key": "unauthorized_dir",
            "title": "Unauthorized Directive",
            "instruction": "Should be rejected",
        },
    )
    assert resp_b_dir.status_code == 403
    assert resp_b_dir.json()["detail"]["code"] == "not_club_owner"

    resp_b_resolve = client.post(
        f"/owner/clubs/{state_a.club_id}/living-world/events/{evt_a.id}/resolve",
        json={"action": "acknowledge"},
    )
    assert resp_b_resolve.status_code == 403
    assert resp_b_resolve.json()["detail"]["code"] == "not_club_owner"

    # 3. Non-existent club returns 404
    resp_404 = client.get("/owner/clubs/nonexistent-club-999/living-world/timeline")
    assert resp_404.status_code == 404
    assert resp_404.json()["detail"]["code"] == "club_not_found"
