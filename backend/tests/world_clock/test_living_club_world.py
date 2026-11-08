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
        session.flush()

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
    """Verifies P1 Directive Completion Semantics:
    1. Directive completes only when its real backend completion condition is satisfied.
    2. Repeated world ticks do not duplicate completion events or relationship rewards.
    3. Directive reaching deadline without completion becomes 'expired' with zero positive relationship reward.
    4. Vacant department never automatically completes a directive.
    """
    session = _session()
    state = _seed_club(session)

    # Ensure baseline relationships exist
    squad_players = list(
        session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
    )
    living_club_world.ensure_default_relationships(session, state, squad_players)
    med_rel_before = living_club_world.get_relationship_for_department(session, state.club_id, "medical_director")
    assert med_rel_before is not None
    initial_med_trust = med_rel_before["trust"]

    # 1. Issue medical directive on day 10 with deadline day 13
    dir_payload = living_club_world.issue_department_directive(
        session,
        state.owner_user_id,
        state.club_id,
        department="medical",
        directive_key="accelerate_recovery",
        title="Accelerate Hydrotherapy Protocols",
        instruction="Prioritize non-contact rehab for first-team players ahead of cup tie",
        objective_key="reduce_injury_burden",
        deadline_days=3,
    )
    assert dir_payload["status"] == "active"
    assert "Dr. Chidi Obi" in dir_payload["acknowledged_by"]
    assert dir_payload["deadline_day"] == 13

    # Advance to day 11 WITHOUT fulfilling condition -> remains active, not completed
    state.world_day = 11
    living_club_world.process_world_day_events(session, state, campus_effects={})
    directive = session.get(OwnerClubDirective, dir_payload["id"])
    assert directive is not None
    assert directive.status == "active"
    assert directive.completed_at is None
    assert directive.consequences_json["verification_status"] == "pending"

    # Now fulfill the authoritative medical condition (injured player progresses in recovery)
    p3 = session.get(OwnerSquadPlayer, f"p3-{state.club_id}")
    assert p3 is not None
    p3.injured_days = 1  # reduced from baseline injured_days=2
    session.commit()

    living_club_world.process_world_day_events(session, state, campus_effects={})
    session.refresh(directive)
    assert directive.status == "completed"
    assert directive.completed_at is not None
    assert directive.consequences_json["verification_status"] == "verified_completed"
    assert directive.consequences_json["progress_pct"] == 100
    assert directive.consequences_json["reward_granted"] is True

    med_rel_after = living_club_world.get_relationship_for_department(session, state.club_id, "medical_director")
    assert med_rel_after is not None
    # +3 on directive acknowledgment +4 on verified directive completion = +7 total
    assert med_rel_after["trust"] == initial_med_trust + 7

    # 2. Repeated world ticks on days 12 and 13 must NOT duplicate completion events or rewards
    state.world_day = 12
    living_club_world.process_world_day_events(session, state, campus_effects={})
    state.world_day = 13
    living_club_world.process_world_day_events(session, state, campus_effects={})

    med_rel_repeated = living_club_world.get_relationship_for_department(session, state.club_id, "medical_director")
    assert med_rel_repeated is not None
    assert med_rel_repeated["trust"] == med_rel_after["trust"]
    completion_events = list(
        session.scalars(
            select(OwnerClubEvent).where(
                OwnerClubEvent.club_id == state.club_id,
                OwnerClubEvent.event_type == "directive_completed",
                OwnerClubEvent.source_id == directive.id,
            )
        ).all()
    )
    assert len(completion_events) == 1

    # 3. Unfulfilled directive reaching deadline becomes 'expired' with NO positive relationship reward
    unfulfilled_payload = living_club_world.issue_department_directive(
        session,
        state.owner_user_id,
        state.club_id,
        department="academy",
        directive_key="expand_youth_pathway",
        title="Promote Two U18 Prospects",
        instruction="Upgrade youth pathway or promote academy prospects before deadline",
        deadline_days=2,
    )
    assert unfulfilled_payload["deadline_day"] == 15
    hoyd_rel_issued = living_club_world.get_relationship_for_department(
        session, state.club_id, "head_of_youth_development"
    )
    assert hoyd_rel_issued is not None
    hoyd_trust_issued = hoyd_rel_issued["trust"]
    hoyd_respect_issued = hoyd_rel_issued["respect"]

    # Advance to deadline day 15 without any academy upgrade, regen promotion, or youth rating gain
    state.world_day = 15
    living_club_world.process_world_day_events(session, state, campus_effects={})

    expired_dir = session.get(OwnerClubDirective, unfulfilled_payload["id"])
    assert expired_dir is not None
    assert expired_dir.status == "expired"
    assert expired_dir.completed_at is None
    assert expired_dir.consequences_json["verification_status"] == "expired_unfulfilled"
    assert expired_dir.consequences_json["reward_granted"] is False

    hoyd_rel_after = living_club_world.get_relationship_for_department(
        session, state.club_id, "head_of_youth_development"
    )
    assert hoyd_rel_after is not None
    # No completion reward (+6 trust, +5 respect) granted on expiry
    assert hoyd_rel_after["trust"] <= hoyd_trust_issued
    assert hoyd_rel_after["respect"] <= hoyd_respect_issued

    expired_events = list(
        session.scalars(
            select(OwnerClubEvent).where(
                OwnerClubEvent.club_id == state.club_id,
                OwnerClubEvent.event_type == "directive_expired",
                OwnerClubEvent.source_id == expired_dir.id,
            )
        ).all()
    )
    assert len(expired_events) == 1

    # 4. Vacant department NEVER automatically completes its directive even if underlying metrics improve
    vacant_state = _seed_club(
        session,
        club_id="club-vacant-dir",
        user_id="user-vacant-dir",
        appoint_executive_staff=False,
    )
    vacant_dir_payload = living_club_world.issue_department_directive(
        session,
        vacant_state.owner_user_id,
        vacant_state.club_id,
        department="medical",
        directive_key="vacant_rehab_protocol",
        title="Rehab Protocol Without Medical Director",
        instruction="Attempt rehab directive while medical director post is vacant",
        objective_key="reduce_injury_burden",
        deadline_days=2,
    )
    # Even if the injured player recovers on day 11, vacant medical department cannot verify/complete directive
    vacant_p3 = session.get(OwnerSquadPlayer, f"p3-{vacant_state.club_id}")
    assert vacant_p3 is not None
    vacant_p3.injured_days = 0
    session.commit()

    vacant_state.world_day = 11
    living_club_world.process_world_day_events(session, vacant_state, campus_effects={})
    vacant_dir = session.get(OwnerClubDirective, vacant_dir_payload["id"])
    assert vacant_dir is not None
    assert vacant_dir.status == "active"
    assert vacant_dir.consequences_json["evidence"]["lead_status"] == "vacant"
    assert vacant_dir.consequences_json["evidence"]["reason"] == "department_lead_vacant"

    # At deadline day 12, vacant department directive expires rather than completing
    vacant_state.world_day = 12
    living_club_world.process_world_day_events(session, vacant_state, campus_effects={})
    session.refresh(vacant_dir)
    assert vacant_dir.status == "expired"
    assert vacant_dir.completed_at is None
    assert living_club_world.get_relationship_for_department(session, vacant_state.club_id, "medical_director") is None


def test_directive_completion_requires_the_selected_objective():
    """A different improvement in the same department must not satisfy a directive."""
    session = _session()
    state = _seed_club(session, club_id="club-objective-match", user_id="user-objective-match")

    with pytest.raises(owner_service.OwnerError) as invalid_objective:
        living_club_world.issue_department_directive(
            session,
            state.owner_user_id,
            state.club_id,
            department="finance",
            directive_key="wrong-department-objective",
            title="Invalid objective",
            instruction="This objective belongs to another department",
            objective_key="change_team_mentality",
        )
    assert invalid_objective.value.status == 400
    assert invalid_objective.value.code == "invalid_directive_objective"

    payload = living_club_world.issue_department_directive(
        session,
        state.owner_user_id,
        state.club_id,
        department="manager",
        directive_key="change-mentality-only",
        title="Adopt a more attacking mentality",
        instruction="Change the first-team mentality to attacking",
        objective_key="change_team_mentality",
        deadline_days=5,
    )
    directive = session.get(OwnerClubDirective, payload["id"])
    assert directive is not None

    # Change formation only. This is a genuine manager-department change, but not
    # the selected objective and must not complete the directive or grant rewards.
    facilities = dict(state.facilities_json or {})
    facilities["_tactical_formation"] = "4-4-2"
    state.facilities_json = facilities
    flag_modified(state, "facilities_json")
    session.commit()

    living_club_world.process_world_day_events(session, state, campus_effects={})
    session.refresh(directive)
    assert directive.status == "active"
    assert directive.completed_at is None
    assert directive.consequences_json["verification_status"] == "pending"
    assert directive.consequences_json["reward_granted"] is False
    assert directive.consequences_json["evidence"]["objective_key"] == "change_team_mentality"
    assert directive.consequences_json["evidence"]["matched_checks"] == []

    # Only the selected authoritative condition completes it.
    state.mentality = "attacking"
    session.commit()
    living_club_world.process_world_day_events(session, state, campus_effects={})
    session.refresh(directive)
    assert directive.status == "completed"
    assert directive.consequences_json["evidence"]["matched_checks"] == ["tactical_mentality_updated:attacking"]
    assert directive.consequences_json["reward_granted"] is True


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
        respect=55,
        affinity=50,
        tension=25,
        updated_at=datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc),
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
        trust=78,
        respect=81,
        affinity=72,
        tension=9,
        updated_at=datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc),
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
        delta_trust=18,
        snapshot_json={"trust": 78},
    )
    session.add_all([h1, h2])
    session.commit()

    removed = living_club_world.deduplicate_club_relationships(session, state.club_id)
    assert removed == 1

    # Authoritative latest metrics from rel2 are preserved on surviving canonical relationship rel1
    surviving = session.get(OwnerClubRelationship, "rel-canon-1")
    assert surviving is not None
    assert surviving.trust == 78
    assert surviving.respect == 81
    assert surviving.affinity == 72
    assert surviving.tension == 9

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
    tactical_event, _ = living_club_world.create_club_event(
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
    tactical_event.status = "awaiting_decision"
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

    # Filter by status="active" includes actionable awaiting_decision events, but excludes resolved history
    active_tl = living_club_world.get_living_world_timeline(
        session, state.owner_user_id, state.club_id, status="active"
    )
    assert all(i["status"] in {"active", "awaiting_decision"} for i in active_tl["items"])
    assert any(i["id"] == tactical_event.id and i["status"] == "awaiting_decision" for i in active_tl["items"])
    assert all(i["kind"] != "relationship_shift" for i in active_tl["items"])


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


def test_high_fatigue_alert_with_healthy_fitness():
    """Verifies P2: high fatigue (>= 70) while fitness remains healthy (>= 70) accurately reports the fatigue metric."""
    session = _session()
    state = _seed_club(session, club_id="club-fatigue-healthy-1", user_id="user-fatigue-healthy-1")

    p1 = session.get(OwnerSquadPlayer, f"p1-{state.club_id}")
    assert p1 is not None
    p1.personality_json = {
        "leadership": 16,
        "fitness": 88,  # healthy conditioning (>= 70)
        "fatigue": 78,  # elevated fatigue (>= 70)
    }
    flag_modified(p1, "personality_json")
    session.commit()

    res = living_club_world.process_world_day_events(session, state, campus_effects={})
    fatigue_evt = next(
        (
            e
            for e in res["active_events"]
            if e["event_type"] == "high_fatigue_workload_alert" and e["source_id"] == p1.id
        ),
        None,
    )
    assert fatigue_evt is not None
    assert fatigue_evt["consequences"]["trigger_metric"] == "fatigue"
    assert fatigue_evt["consequences"]["fatigue"] == 78
    assert fatigue_evt["consequences"]["fitness"] == 88
    assert "78/100" in fatigue_evt["description"]
    assert "Conditioning 88%" in fatigue_evt["description"]
    # Must NEVER report the fatigue reading (78) as a fitness percentage or claim low conditioning
    assert "78% conditioning" not in fatigue_evt["description"]
    assert "conditioning has dropped" not in fatigue_evt["description"]


def test_migration_0226_reconciles_duplicates_preserving_history_and_latest_metrics():
    """Verifies P2 Migration 0226: starts with pre-0226 relationship schema, seeds duplicate and reversed pairings
    with different relationship metrics and history records on both, runs migration 0226, and verifies:
    - One canonical relationship remains
    - All history records remain attached to the surviving relationship
    - The authoritative latest relationship values (trust, respect, affinity, tension) are preserved
    - A raw duplicate DB insert is rejected by the unique constraint/index
    """
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    import sqlalchemy as sa

    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with eng.begin() as conn:
        conn.execute(sa.text("""
                CREATE TABLE owner_club_relationships (
                    id VARCHAR(64) PRIMARY KEY,
                    club_id VARCHAR(64) NOT NULL,
                    pairing_key VARCHAR(160) NOT NULL,
                    participant_a_type VARCHAR(32) NOT NULL,
                    participant_a_id VARCHAR(64) NOT NULL,
                    participant_a_name VARCHAR(120) NOT NULL,
                    participant_b_type VARCHAR(32) NOT NULL,
                    participant_b_id VARCHAR(64) NOT NULL,
                    participant_b_name VARCHAR(120) NOT NULL,
                    trust INTEGER NOT NULL DEFAULT 60,
                    respect INTEGER NOT NULL DEFAULT 60,
                    affinity INTEGER NOT NULL DEFAULT 55,
                    tension INTEGER NOT NULL DEFAULT 15,
                    status VARCHAR(32) NOT NULL DEFAULT 'active',
                    metadata_json JSON,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """))
        conn.execute(sa.text("""
                CREATE TABLE owner_club_relationship_history (
                    id VARCHAR(64) PRIMARY KEY,
                    relationship_id VARCHAR(64) NOT NULL,
                    club_id VARCHAR(64) NOT NULL,
                    world_day INTEGER NOT NULL DEFAULT 1,
                    reason VARCHAR(240) NOT NULL,
                    delta_trust INTEGER NOT NULL DEFAULT 0,
                    delta_respect INTEGER NOT NULL DEFAULT 0,
                    delta_affinity INTEGER NOT NULL DEFAULT 0,
                    delta_tension INTEGER NOT NULL DEFAULT 0,
                    snapshot_json JSON,
                    source_event_id VARCHAR(64),
                    created_at TIMESTAMP NOT NULL
                )
                """))

        # Seed older forward pairing and newer reversed pairing with different metrics
        conn.execute(sa.text("""
                INSERT INTO owner_club_relationships (
                    id, club_id, pairing_key,
                    participant_a_type, participant_a_id, participant_a_name,
                    participant_b_type, participant_b_id, participant_b_name,
                    trust, respect, affinity, tension, status, metadata_json,
                    created_at, updated_at
                ) VALUES
                (
                    'rel-mig-older', 'club-mig-1', 'club-mig-1:owner:player-1',
                    'owner', 'owner', 'Club Owner',
                    'player', 'player-1', 'Tunde Bakare',
                    52, 55, 48, 30, 'active', '{}',
                    '2026-11-05 09:00:00', '2026-11-05 10:00:00'
                ),
                (
                    'rel-mig-newer-reversed', 'club-mig-1', 'club-mig-1:player-1:owner',
                    'player', 'player-1', 'Tunde Bakare',
                    'owner', 'owner', 'Club Owner',
                    84, 79, 73, 8, 'active', '{}',
                    '2026-11-05 09:30:00', '2026-11-05 11:30:00'
                )
                """))
        conn.execute(sa.text("""
                INSERT INTO owner_club_relationship_history (
                    id, relationship_id, club_id, world_day, reason,
                    delta_trust, delta_respect, delta_affinity, delta_tension,
                    snapshot_json, created_at
                ) VALUES
                (
                    'hist-mig-1', 'rel-mig-older', 'club-mig-1', 10, 'Initial contract talk',
                    -8, -5, -7, 15, '{"trust": 52}', '2026-11-05 10:00:00'
                ),
                (
                    'hist-mig-2', 'rel-mig-newer-reversed', 'club-mig-1', 11, 'Resolved contract dispute',
                    32, 24, 25, -22, '{"trust": 84}', '2026-11-05 11:30:00'
                )
                """))

        # Load and execute migration 0226 upgrade()
        mig_path = (
            Path(__file__).resolve().parents[2]
            / "migrations"
            / "versions"
            / "20261105_0226_phase2_4_relationship_pair_uniqueness.py"
        )
        spec = importlib.util.spec_from_file_location("mig_0226", mig_path)
        assert spec is not None and spec.loader is not None
        mig_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig_mod)

        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mig_mod.upgrade()

        # 1. Verify exactly one canonical relationship remains
        rel_rows = conn.execute(
            sa.text(
                "SELECT id, pairing_key, trust, respect, affinity, tension FROM owner_club_relationships WHERE club_id = 'club-mig-1'"
            )
        ).fetchall()
        assert len(rel_rows) == 1
        surviving = rel_rows[0]
        assert surviving.id == "rel-mig-older"
        assert surviving.pairing_key == "club-mig-1:owner:player-1"

        # 2. Verify authoritative latest metrics from rel-mig-newer-reversed are preserved
        assert surviving.trust == 84
        assert surviving.respect == 79
        assert surviving.affinity == 73
        assert surviving.tension == 8

        # 3. Verify all history records remain attached to the surviving canonical relationship
        hist_rows = conn.execute(
            sa.text(
                "SELECT id, relationship_id FROM owner_club_relationship_history WHERE club_id = 'club-mig-1' ORDER BY id"
            )
        ).fetchall()
        assert len(hist_rows) == 2
        assert {h.relationship_id for h in hist_rows} == {"rel-mig-older"}

        # 4. Verify raw duplicate insert is rejected by the unique index/constraint
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(sa.text("""
                        INSERT INTO owner_club_relationships (
                            id, club_id, pairing_key,
                            participant_a_type, participant_a_id, participant_a_name,
                            participant_b_type, participant_b_id, participant_b_name,
                            trust, respect, affinity, tension, status, metadata_json,
                            created_at, updated_at
                        ) VALUES (
                            'rel-mig-dup-attempt', 'club-mig-1', 'club-mig-1:owner:player-1',
                            'owner', 'owner', 'Club Owner',
                            'player', 'player-1', 'Tunde Bakare',
                            60, 60, 55, 15, 'active', '{}',
                            '2026-11-05 12:00:00', '2026-11-05 12:00:00'
                        )
                        """))


def _find_pg_bin(exe_name: str) -> str | None:
    import glob
    import shutil

    found = shutil.which(exe_name)
    if found:
        return found
    candidates = [
        *glob.glob(f"C:/Program Files/PostgreSQL/*/bin/{exe_name}.exe"),
        *glob.glob(f"/usr/lib/postgresql/*/bin/{exe_name}"),
    ]
    return sorted(candidates)[-1] if candidates else None


@pytest.fixture()
def postgres_engine(tmp_path):
    """Provides a real PostgreSQL SQLAlchemy engine for row-locking concurrency tests.
    Uses GTE_TEST_POSTGRES_URL if provided; otherwise initializes an ephemeral local PostgreSQL cluster.
    """
    import os
    import socket
    import subprocess
    import uuid
    import sqlalchemy as sa

    env_url = os.environ.get("GTE_TEST_POSTGRES_URL", "").strip()
    if env_url:
        base_eng = create_engine(env_url, isolation_level="AUTOCOMMIT")
        schema_name = f"test_p24_{uuid.uuid4().hex[:8]}"
        with base_eng.connect() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{schema_name}"'))
        eng = create_engine(
            env_url,
            connect_args={"options": f"-c search_path={schema_name}"},
        )
        try:
            yield eng
        finally:
            eng.dispose()
            with base_eng.connect() as conn:
                conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            base_eng.dispose()
        return

    initdb_bin = _find_pg_bin("initdb")
    pg_ctl_bin = _find_pg_bin("pg_ctl")
    if not initdb_bin or not pg_ctl_bin:
        pytest.skip("PostgreSQL binaries (initdb/pg_ctl) not available and GTE_TEST_POSTGRES_URL not set")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    pgdata = tmp_path / "pgdata"
    logfile = tmp_path / "postgres.log"
    try:
        subprocess.run(
            [initdb_bin, "-D", str(pgdata), "-U", "postgres", "-A", "trust", "-E", "UTF8", "--no-locale"],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [pg_ctl_bin, "-D", str(pgdata), "-l", str(logfile), "-o", f"-F -p {port} -h 127.0.0.1", "-w", "start"],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, OSError):
        pytest.skip("Local ephemeral initdb cluster creation failed; set GTE_TEST_POSTGRES_URL to test real PostgreSQL concurrency")
    url = f"postgresql+psycopg://postgres@127.0.0.1:{port}/postgres"
    eng = create_engine(url, pool_size=5, max_overflow=5)
    try:
        yield eng
    finally:
        eng.dispose()
        subprocess.run(
            [pg_ctl_bin, "-D", str(pgdata), "-m", "immediate", "-w", "stop"],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def test_concurrent_postgres_event_resolution_no_duplicate_consequences(postgres_engine):
    """Verifies P1 Concurrent Event Resolution Protection on PostgreSQL:
    Uses two independent SQLAlchemy sessions and two concurrent requests attempting to resolve the same event:
    - Exactly one request succeeds
    - The competing request receives a 409 conflict (event_already_resolved)
    - Exactly one consequence execution occurs (player morale +15 once, not +30)
    - Exactly one set of relationship-history changes is recorded
    - The event ends in a consistent 'resolved' state
    """
    import threading

    Base.metadata.create_all(
        postgres_engine,
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
    factory = sessionmaker(bind=postgres_engine, autoflush=False, expire_on_commit=False)

    setup_session = factory()
    setup_session.add(
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
    setup_session.commit()

    state = _seed_club(setup_session, club_id="club-pg-conc-1", user_id="user-pg-conc-1")
    living_club_world.process_world_day_events(setup_session, state, campus_effects={})
    setup_session.commit()

    morale_event = setup_session.scalar(
        select(OwnerClubEvent).where(
            OwnerClubEvent.club_id == state.club_id,
            OwnerClubEvent.event_type == "squad_morale_dip",
        )
    )
    assert morale_event is not None
    event_id = morale_event.id
    player_id = morale_event.source_id
    user_id = state.owner_user_id
    club_id = state.club_id
    setup_session.close()

    barrier = threading.Barrier(2)
    results: list[dict] = []
    errors: list[owner_service.OwnerError] = []
    unexpected_errors: list[Exception] = []
    lock = threading.Lock()

    def _worker(worker_idx: int) -> None:
        worker_session = factory()
        try:
            barrier.wait(timeout=10.0)
            res = living_club_world.resolve_club_event(
                worker_session,
                user_id,
                club_id,
                event_id,
                action="encourage_player",
                resolution_note=f"Concurrent worker {worker_idx}",
            )
            worker_session.commit()
            with lock:
                results.append(res)
        except owner_service.OwnerError as exc:
            worker_session.rollback()
            with lock:
                errors.append(exc)
        except Exception as exc:  # pragma: no cover
            worker_session.rollback()
            with lock:
                unexpected_errors.append(exc)
        finally:
            worker_session.close()

    t1 = threading.Thread(target=_worker, args=(1,))
    t2 = threading.Thread(target=_worker, args=(2,))
    t1.start()
    t2.start()
    t1.join(timeout=15.0)
    t2.join(timeout=15.0)

    assert not unexpected_errors, f"Unexpected worker errors: {unexpected_errors}"
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 conflict error, got {len(errors)}"
    assert errors[0].status == 409
    assert errors[0].code == "event_already_resolved"

    verify_session = factory()
    try:
        final_event = verify_session.get(OwnerClubEvent, event_id)
        assert final_event is not None
        assert final_event.status == "resolved"
        assert final_event.resolution_action == "encourage_player"
        assert final_event.resolved_at is not None

        player = verify_session.get(OwnerSquadPlayer, player_id)
        assert player is not None
        # Initial morale was 35; encourage_player adds +15 exactly once -> 50 (never 65)
        assert player.morale == 50

        rel_history = list(
            verify_session.scalars(
                select(OwnerClubRelationshipHistory).where(
                    OwnerClubRelationshipHistory.club_id == club_id,
                    OwnerClubRelationshipHistory.source_event_id == event_id,
                )
            ).all()
        )
        assert len(rel_history) == 1
    finally:
        verify_session.close()
