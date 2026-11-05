from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
from app.owner_console import daily_operations_hub, engine as owner_engine, ledger, living_club_world
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
) -> OwnerClubState:
    user = User(
        id=user_id,
        email=f"{user_id}@gtex.test",
        username=f"owner_{user_id}",
        password_hash="hash",  # pragma: allowlist secret
    )
    profile = ClubProfile(
        id=club_id,
        owner_user_id=user_id,
        club_name="Lagos Marine FC",
        slug=f"lagos-marine-fc-{club_id}",
        primary_color="#0284c7",
        secondary_color="#0f172a",
        accent_color="#38bdf8",
    )
    session.add(user)
    session.add(profile)

    state = OwnerClubState(
        id=f"state-{club_id}",
        club_id=club_id,
        owner_user_id=user_id,
        club_name="Lagos Marine FC",
        stage="active",
        prestige=prestige,
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={
            "training": 2,
            "academy": 2,
            "medical": 2,
            "stadium": 2,
            "commercial": 2,
            "_executive_staff": {
                "general_manager": {"name": "Dayo Adeleke", "role": "general_manager", "mood": 78},
                "head_of_youth_development": {"name": "Femi Ogunleye", "role": "head_of_youth_development", "mood": 82},
                "medical_director": {
                    "name": "Dr. Amara Okafor",
                    "role": "medical_director",
                    "mood": 84,
                    "medical_expertise": 14,
                },
                "chief_scout": {"name": "Kelechi Nwosu", "role": "chief_scout", "mood": 76},
            },
        },
        world_day=10,
        last_tick_at=WORLD_NOW,
        last_world_tick_date=WORLD_NOW.date(),
        value_history_json=[],
    )
    session.add(state)

    # Add squad players
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
        morale=35,  # Low morale to trigger discontent
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


def test_ensure_default_relationships_and_bounds():
    session = _session()
    state = _seed_club(session)
    squad_players = list(
        session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
    )

    # Ensure default relationships initialized
    rels = living_club_world.ensure_default_relationships(session, state, squad_players)
    assert len(rels) >= 7

    # Check Owner <-> Manager
    mgr_rel = next(r for r in rels if "first_team_manager" in (r.participant_a_id, r.participant_b_id))
    assert mgr_rel.trust == 55
    assert mgr_rel.respect == 60
    assert mgr_rel.tension == 15

    # Check bounds enforcement
    updated = living_club_world.apply_relationship_delta(
        session,
        state.club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        "first_team_manager",
        "First-Team Manager",
        delta_trust=100,  # Should clamp to 100
        delta_tension=-50,  # Should clamp to 0
        reason="Spectacular derby victory",
        world_day=10,
    )
    assert updated.trust == 100
    assert updated.tension == 0

    # Verify audit history
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

    # World tick process events
    res1 = living_club_world.process_world_day_events(session, state, campus_effects={})
    assert res1["new_events_count"] > 0
    initial_event_count = res1["new_events_count"]

    # Verify categories present
    events = res1["active_events"]
    categories = {e["category"] for e in events}
    assert "squad" in categories  # Triggered by Segun Adele morale 35
    assert "academy" in categories  # Triggered by Emeka Eze regen 66 OVR

    # Idempotency check: repeated execution on same day must not duplicate events
    res2 = living_club_world.process_world_day_events(session, state, campus_effects={})
    assert res2["new_events_count"] == 0
    assert res2["total_active_events"] == initial_event_count


def test_event_resolution_and_simulation_consequences():
    session = _session()
    state = _seed_club(session)

    living_club_world.process_world_day_events(session, state, campus_effects={})

    # Find squad morale event
    morale_event = session.scalar(
        select(OwnerClubEvent).where(
            OwnerClubEvent.club_id == state.club_id,
            OwnerClubEvent.event_type == "squad_morale_dip",
        )
    )
    assert morale_event is not None
    assert morale_event.status == "active"

    # Resolve event
    res = living_club_world.resolve_club_event(
        session,
        state.owner_user_id,
        state.club_id,
        morale_event.id,
        action="encourage_player",
        resolution_note="Chairman met with player personally",
    )
    assert res["status"] == "resolved"
    assert res["consequences_applied"]["player_morale"] == 50  # Morale rose from 35 to 50

    # Verify event state persisted
    session.refresh(morale_event)
    assert morale_event.status == "resolved"
    assert morale_event.resolution_action == "encourage_player"
    assert morale_event.resolved_at is not None

    # Cannot resolve again
    with pytest.raises(ValueError, match="Event cannot be resolved"):
        living_club_world.resolve_club_event(
            session,
            state.owner_user_id,
            state.club_id,
            morale_event.id,
            action="encourage_player",
        )


def test_departmental_directive_lifecycle():
    session = _session()
    state = _seed_club(session)

    # Issue directive to Medical Department
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
    assert "Dr. Amara Okafor" in dir_payload["acknowledged_by"]
    assert (
        "Directive acknowledged" in dir_payload["acknowledgement_text"]
        or "Directive received" in dir_payload["acknowledgement_text"]
    )
    assert dir_payload["deadline_day"] == 12  # world_day 10 + 2

    # Advance world day to deadline (day 12)
    state.world_day = 12
    living_club_world.process_world_day_events(session, state, campus_effects={})

    # Verify directive completed
    directive = session.get(OwnerClubDirective, dir_payload["id"])
    assert directive.status == "completed"
    assert directive.completed_at is not None

    # Verify medical director relationship trust increased
    med_rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == state.club_id,
            OwnerClubRelationship.pairing_key
            == living_club_world.pairing_key(state.club_id, "owner", "medical_director"),
        )
    )
    assert med_rel.trust > 65  # Base was 65, increased on completion


def test_living_world_timeline_filtering_and_aggregation():
    session = _session()
    state = _seed_club(session)

    # Create an event and a directive
    living_club_world.create_club_event(
        session,
        state.club_id,
        category="tactical",
        event_type="derby_briefing",
        severity="important",
        title="Tactical Derby Preparation",
        description="Manager outlined high-pressing shape",
        world_day=10,
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

    # Timeline without filter
    timeline = living_club_world.get_living_world_timeline(session, state.owner_user_id, state.club_id, limit=20)
    assert len(timeline["items"]) >= 2

    # Filter by category
    tactical_timeline = living_club_world.get_living_world_timeline(
        session, state.owner_user_id, state.club_id, category="tactical"
    )
    for item in tactical_timeline["items"]:
        if item["kind"] == "event":
            assert item["category"] == "tactical"


def test_operations_hub_living_world_integration():
    session = _session()
    state = _seed_club(session)

    # Generate events & directives
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

    # Fetch Operations Hub
    hub = daily_operations_hub.get_club_operations_hub(session, state.owner_user_id, state.club_id, force_refresh=True)
    assert "living_world" in hub
    lw = hub["living_world"]
    assert lw["active_events_count"] > 0
    assert lw["active_directives_count"] >= 1
    assert len(lw["relationships"]) >= 7

    # Verify destinations enriched
    destinations = hub["destinations"]
    tactical_office = next(d for d in destinations if d["destination_key"] == "managers_office")
    assert "active_events" in tactical_office
    assert "active_directives" in tactical_office
    assert "relationship" in tactical_office
    assert tactical_office["relationship"]["trust"] >= 50


def test_club_isolation_and_authorization():
    session = _session()
    state1 = _seed_club(session, club_id="club-iso-1", user_id="user-iso-1")
    state2 = _seed_club(session, club_id="club-iso-2", user_id="user-iso-2")

    evt1, _ = living_club_world.create_club_event(
        session,
        state1.club_id,
        category="executive",
        event_type="board_meeting",
        severity="routine",
        title="Board Meeting Club 1",
        description="Private meeting",
        world_day=10,
    )

    # Club 2 cannot resolve Club 1's event
    with pytest.raises(ValueError, match="Event not found"):
        living_club_world.resolve_club_event(
            session,
            state2.owner_user_id,
            state2.club_id,
            evt1.id,
            action="approve",
        )
