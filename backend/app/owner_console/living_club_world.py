from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.base import utcnow
from app.owner_console import engine, ledger
from app.owner_console.models import (
    OwnerClubDirective,
    OwnerClubEvent,
    OwnerClubRelationship,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerSquadPlayer,
)

logger = logging.getLogger(__name__)

EVENT_CATEGORIES = (
    "executive",
    "tactical",
    "squad",
    "academy",
    "medical",
    "financial",
    "culture",
)

EVENT_SEVERITIES = ("routine", "important", "critical")

EVENT_STATUSES = ("created", "active", "awaiting_decision", "resolved", "expired")

DIRECTIVE_DEPARTMENTS = (
    "manager",
    "medical",
    "academy",
    "finance",
    "scouting",
    "executive",
)

DEPARTMENT_TO_ROOM_MAP = {
    "manager": "managers_office",
    "medical": "medical_department",
    "academy": "academy_department",
    "finance": "finance_commercial_office",
    "scouting": "general_managers_office",
    "executive": "executive_office",
}

ROOM_TO_DEPARTMENT_MAP = {v: k for k, v in DEPARTMENT_TO_ROOM_MAP.items()}

DEFAULT_STAFF_METRICS = {
    "first_team_manager": {"trust": 55, "respect": 60, "affinity": 50, "tension": 15},
    "general_manager": {"trust": 65, "respect": 65, "affinity": 60, "tension": 10},
    "head_of_youth_development": {"trust": 60, "respect": 60, "affinity": 55, "tension": 10},
    "medical_director": {"trust": 65, "respect": 70, "affinity": 55, "tension": 5},
    "chief_scout": {"trust": 55, "respect": 55, "affinity": 50, "tension": 15},
}


def normalize_pairing(part_a_id: str, part_b_id: str) -> tuple[str, str]:
    return (min(part_a_id, part_b_id), max(part_a_id, part_b_id))


def pairing_key(club_id: str, part_a_id: str, part_b_id: str) -> str:
    p1, p2 = normalize_pairing(part_a_id, part_b_id)
    return f"{club_id}:{p1}:{p2}"


def compute_relationship_status_label(trust: int, respect: int, affinity: int, tension: int) -> str:
    if tension >= 65:
        return "Volatile"
    if tension >= 45:
        return "Strained"
    composite_positive = (trust + respect + affinity) // 3
    if composite_positive >= 80:
        return "Harmonious"
    if composite_positive >= 65:
        return "Strong"
    if composite_positive >= 45:
        return "Stable"
    return "Divergent"


def get_or_create_relationship(
    session: Session,
    club_id: str,
    part_a_type: str,
    part_a_id: str,
    part_a_name: str,
    part_b_type: str,
    part_b_id: str,
    part_b_name: str,
    *,
    initial_trust: int | None = None,
    initial_respect: int | None = None,
    initial_affinity: int | None = None,
    initial_tension: int | None = None,
) -> OwnerClubRelationship:
    key = pairing_key(club_id, part_a_id, part_b_id)
    rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == key,
        )
    )
    if rel is not None:
        return rel

    p1, p2 = normalize_pairing(part_a_id, part_b_id)
    if p1 == part_a_id:
        f_type_a, f_id_a, f_name_a = part_a_type, part_a_id, part_a_name
        f_type_b, f_id_b, f_name_b = part_b_type, part_b_id, part_b_name
    else:
        f_type_a, f_id_a, f_name_a = part_b_type, part_b_id, part_b_name
        f_type_b, f_id_b, f_name_b = part_a_type, part_a_id, part_a_name

    def_metrics = DEFAULT_STAFF_METRICS.get(part_b_id) or DEFAULT_STAFF_METRICS.get(part_a_id) or {}
    t = initial_trust if initial_trust is not None else def_metrics.get("trust", 50)
    r = initial_respect if initial_respect is not None else def_metrics.get("respect", 50)
    a = initial_affinity if initial_affinity is not None else def_metrics.get("affinity", 50)
    ten = initial_tension if initial_tension is not None else def_metrics.get("tension", 20)

    rel = OwnerClubRelationship(
        club_id=club_id,
        pairing_key=key,
        participant_a_type=f_type_a,
        participant_a_id=f_id_a,
        participant_a_name=f_name_a,
        participant_b_type=f_type_b,
        participant_b_id=f_id_b,
        participant_b_name=f_name_b,
        trust=engine.clamp(t, 0, 100),
        respect=engine.clamp(r, 0, 100),
        affinity=engine.clamp(a, 0, 100),
        tension=engine.clamp(ten, 0, 100),
        status="active",
        metadata_json={},
    )
    session.add(rel)
    session.flush()
    return rel


def apply_relationship_delta(
    session: Session,
    club_id: str,
    part_a_type: str,
    part_a_id: str,
    part_a_name: str,
    part_b_type: str,
    part_b_id: str,
    part_b_name: str,
    *,
    delta_trust: int = 0,
    delta_respect: int = 0,
    delta_affinity: int = 0,
    delta_tension: int = 0,
    reason: str = "World interaction",
    source_event_id: str | None = None,
    world_day: int = 1,
) -> OwnerClubRelationship:
    rel = get_or_create_relationship(
        session,
        club_id,
        part_a_type,
        part_a_id,
        part_a_name,
        part_b_type,
        part_b_id,
        part_b_name,
    )

    rel.trust = engine.clamp(rel.trust + delta_trust, 0, 100)
    rel.respect = engine.clamp(rel.respect + delta_respect, 0, 100)
    rel.affinity = engine.clamp(rel.affinity + delta_affinity, 0, 100)
    rel.tension = engine.clamp(rel.tension + delta_tension, 0, 100)
    rel.updated_at = utcnow()

    history = OwnerClubRelationshipHistory(
        relationship_id=rel.id,
        club_id=club_id,
        world_day=world_day,
        reason=reason,
        source_event_id=source_event_id,
        delta_trust=delta_trust,
        delta_respect=delta_respect,
        delta_affinity=delta_affinity,
        delta_tension=delta_tension,
        snapshot_json={
            "trust": rel.trust,
            "respect": rel.respect,
            "affinity": rel.affinity,
            "tension": rel.tension,
            "status_label": compute_relationship_status_label(rel.trust, rel.respect, rel.affinity, rel.tension),
        },
    )
    session.add(history)
    session.flush()
    return rel


def ensure_default_relationships(
    session: Session,
    state: OwnerClubState,
    squad_players: list[OwnerSquadPlayer],
) -> list[OwnerClubRelationship]:
    club_id = state.club_id
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))
    gm = exec_staff.get("general_manager") or {"name": "Dayo Adeleke", "role": "general_manager"}
    hoyd = exec_staff.get("head_of_youth_development") or {"name": "Femi Ogunleye", "role": "head_of_youth_development"}
    med = exec_staff.get("medical_director") or {"name": "Dr. Amara Okafor", "role": "medical_director"}
    scout = exec_staff.get("chief_scout") or {"name": "Kelechi Nwosu", "role": "chief_scout"}

    captain = None
    if squad_players:
        sorted_candidates = sorted(
            squad_players,
            key=lambda p: (int(p.personality_json.get("leadership", 10)), p.rating, p.age),
            reverse=True,
        )
        captain = sorted_candidates[0]

    relationships: list[OwnerClubRelationship] = []

    # 1. Owner <-> Manager
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "owner",
            "owner",
            "Club Owner",
            "staff",
            "first_team_manager",
            mgr.get("name", "First-Team Manager"),
            initial_trust=55,
            initial_respect=60,
            initial_affinity=50,
            initial_tension=15,
        )
    )

    # 2. Owner <-> General Manager
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "owner",
            "owner",
            "Club Owner",
            "staff",
            "general_manager",
            gm.get("name", "Dayo Adeleke"),
            initial_trust=65,
            initial_respect=65,
            initial_affinity=60,
            initial_tension=10,
        )
    )

    # 3. Owner <-> Head of Youth Development
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "owner",
            "owner",
            "Club Owner",
            "staff",
            "head_of_youth_development",
            hoyd.get("name", "Femi Ogunleye"),
            initial_trust=60,
            initial_respect=60,
            initial_affinity=55,
            initial_tension=10,
        )
    )

    # 4. Owner <-> Medical Director
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "owner",
            "owner",
            "Club Owner",
            "staff",
            "medical_director",
            med.get("name", "Dr. Amara Okafor"),
            initial_trust=65,
            initial_respect=70,
            initial_affinity=55,
            initial_tension=5,
        )
    )

    # 5. Owner <-> Chief Scout
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "owner",
            "owner",
            "Club Owner",
            "staff",
            "chief_scout",
            scout.get("name", "Kelechi Nwosu"),
            initial_trust=55,
            initial_respect=55,
            initial_affinity=50,
            initial_tension=15,
        )
    )

    # 6. Manager <-> Medical Director
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "staff",
            "first_team_manager",
            mgr.get("name", "First-Team Manager"),
            "staff",
            "medical_director",
            med.get("name", "Dr. Amara Okafor"),
            initial_trust=50,
            initial_respect=60,
            initial_affinity=45,
            initial_tension=25,
        )
    )

    # 7. Manager <-> Head of Youth Development
    relationships.append(
        get_or_create_relationship(
            session,
            club_id,
            "staff",
            "first_team_manager",
            mgr.get("name", "First-Team Manager"),
            "staff",
            "head_of_youth_development",
            hoyd.get("name", "Femi Ogunleye"),
            initial_trust=55,
            initial_respect=55,
            initial_affinity=50,
            initial_tension=20,
        )
    )

    # 8. Owner <-> Captain & Manager <-> Captain
    if captain:
        relationships.append(
            get_or_create_relationship(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "player",
                captain.id,
                f"{captain.name} (C)",
                initial_trust=60,
                initial_respect=65,
                initial_affinity=55,
                initial_tension=15,
            )
        )
        relationships.append(
            get_or_create_relationship(
                session,
                club_id,
                "staff",
                "first_team_manager",
                mgr.get("name", "First-Team Manager"),
                "player",
                captain.id,
                f"{captain.name} (C)",
                initial_trust=65,
                initial_respect=70,
                initial_affinity=60,
                initial_tension=15,
            )
        )

    return relationships


def format_relationship_dict(rel: OwnerClubRelationship) -> dict[str, Any]:
    return {
        "id": rel.id,
        "club_id": rel.club_id,
        "pairing_key": rel.pairing_key,
        "participant_a_type": rel.participant_a_type,
        "participant_a_id": rel.participant_a_id,
        "participant_a_name": rel.participant_a_name,
        "participant_b_type": rel.participant_b_type,
        "participant_b_id": rel.participant_b_id,
        "participant_b_name": rel.participant_b_name,
        "trust": rel.trust,
        "respect": rel.respect,
        "affinity": rel.affinity,
        "tension": rel.tension,
        "status": rel.status,
        "status_label": compute_relationship_status_label(rel.trust, rel.respect, rel.affinity, rel.tension),
        "metadata": rel.metadata_json or {},
        "created_at": rel.created_at.isoformat() if rel.created_at else None,
        "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
    }


def get_club_relationships(session: Session, club_id: str) -> list[dict[str, Any]]:
    rows = list(
        session.scalars(
            select(OwnerClubRelationship)
            .where(OwnerClubRelationship.club_id == club_id, OwnerClubRelationship.status == "active")
            .order_by(OwnerClubRelationship.created_at.asc())
        ).all()
    )
    return [format_relationship_dict(r) for r in rows]


def get_relationship_for_department(session: Session, club_id: str, department_lead_role: str) -> dict[str, Any] | None:
    key = pairing_key(club_id, "owner", department_lead_role)
    rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == key,
        )
    )
    return format_relationship_dict(rel) if rel else None


def create_club_event(
    session: Session,
    club_id: str,
    category: str,
    event_type: str,
    severity: str,
    title: str,
    description: str,
    world_day: int,
    *,
    source_type: str = "system",
    source_id: str | None = None,
    participants: list[dict[str, Any]] | None = None,
    consequences: dict[str, Any] | None = None,
    actions: list[dict[str, Any]] | None = None,
    idempotency_key: str | None = None,
    status: str = "active",
) -> tuple[OwnerClubEvent, bool]:
    if idempotency_key:
        existing = session.scalar(
            select(OwnerClubEvent).where(
                OwnerClubEvent.club_id == club_id,
                OwnerClubEvent.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing, False

    event = OwnerClubEvent(
        club_id=club_id,
        category=category,
        event_type=event_type,
        severity=severity,
        status=status,
        source_type=source_type,
        source_id=source_id,
        title=title,
        description=description,
        participants_json=participants or [],
        world_day=world_day,
        consequences_json=consequences or {},
        actions_json=actions or [],
        idempotency_key=idempotency_key,
    )
    session.add(event)
    session.flush()
    return event, True


def format_event_dict(event: OwnerClubEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "club_id": event.club_id,
        "category": event.category,
        "event_type": event.event_type,
        "severity": event.severity,
        "status": event.status,
        "source_type": event.source_type,
        "source_id": event.source_id,
        "title": event.title,
        "description": event.description,
        "participants": event.participants_json or [],
        "world_day": event.world_day,
        "consequences": event.consequences_json or {},
        "actions": event.actions_json or [],
        "idempotency_key": event.idempotency_key,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "resolution_action": event.resolution_action,
        "resolution_note": event.resolution_note,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def format_directive_dict(dir_row: OwnerClubDirective) -> dict[str, Any]:
    return {
        "id": dir_row.id,
        "club_id": dir_row.club_id,
        "department": dir_row.department,
        "directive_key": dir_row.directive_key,
        "title": dir_row.title,
        "instruction": dir_row.instruction,
        "target_scope": dir_row.target_scope,
        "target_scope_id": dir_row.target_scope_id,
        "status": dir_row.status,
        "issued_day": dir_row.issued_day,
        "deadline_day": dir_row.deadline_day,
        "acknowledged_by": dir_row.acknowledged_by,
        "acknowledgement_text": dir_row.acknowledgement_text,
        "consequences": dir_row.consequences_json or {},
        "completed_at": dir_row.completed_at.isoformat() if dir_row.completed_at else None,
        "created_at": dir_row.created_at.isoformat() if dir_row.created_at else None,
        "updated_at": dir_row.updated_at.isoformat() if dir_row.updated_at else None,
    }


def issue_department_directive(
    session: Session,
    user_id: str,
    club_id: str,
    department: str,
    directive_key: str,
    title: str,
    instruction: str,
    *,
    deadline_days: int | None = 7,
    target_scope: str | None = None,
    target_scope_id: str | None = None,
) -> dict[str, Any]:
    if department not in DIRECTIVE_DEPARTMENTS:
        raise ValueError(f"Invalid department '{department}'. Must be one of {DIRECTIVE_DEPARTMENTS}.")

    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if state is None:
        raise ValueError("Club state not found.")

    squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    ensure_default_relationships(session, state, squad_players)

    world_day = int(state.world_day or 1)
    deadline_day = (world_day + deadline_days) if deadline_days else None

    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))

    staff_leads = {
        "manager": (mgr.get("name", "First-Team Manager"), "First-Team Manager", "first_team_manager"),
        "medical": (
            (exec_staff.get("medical_director") or {}).get("name", "Dr. Amara Okafor"),
            "Medical Director",
            "medical_director",
        ),
        "academy": (
            (exec_staff.get("head_of_youth_development") or {}).get("name", "Femi Ogunleye"),
            "Head of Youth Development",
            "head_of_youth_development",
        ),
        "finance": (
            (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke"),
            "General Manager",
            "general_manager",
        ),
        "scouting": (
            (exec_staff.get("chief_scout") or {}).get("name", "Kelechi Nwosu"),
            "Chief Scout",
            "chief_scout",
        ),
        "executive": (
            (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke"),
            "Executive Directorate",
            "general_manager",
        ),
    }

    lead_name, lead_title, lead_role_id = staff_leads[department]
    rel_key = pairing_key(club_id, "owner", lead_role_id)
    rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == rel_key,
        )
    )

    trust = rel.trust if rel else 50
    tension = rel.tension if rel else 20

    if tension >= 60:
        ack_text = (
            f"Understood, Chairman. The {department} team has logged this directive. Given current operational tensions, "
            f"we will execute as resources permit by World Day {deadline_day or 'the deadline'}."
        )
    elif trust >= 70:
        ack_text = (
            f"Directive received with full priority, Chairman. {lead_name} and the {department} staff are aligned "
            f"and already advancing instructions. Expected target completion by World Day {deadline_day}."
        )
    else:
        ack_text = (
            f"Directive acknowledged, Chairman. The {department} division has scheduled implementation "
            f"with milestone targets for World Day {deadline_day}."
        )

    directive = OwnerClubDirective(
        club_id=club_id,
        department=department,
        directive_key=directive_key,
        title=title,
        instruction=instruction,
        target_scope=target_scope,
        target_scope_id=target_scope_id,
        status="active",
        issued_day=world_day,
        deadline_day=deadline_day,
        acknowledged_by=f"{lead_name} ({lead_title})",
        acknowledgement_text=ack_text,
        consequences_json={
            "initial_trust": trust,
            "department": department,
            "target_scope": target_scope,
        },
    )
    session.add(directive)
    session.flush()

    # Create associated living world event
    create_club_event(
        session,
        club_id,
        category="executive",
        event_type="directive_dispatched",
        severity="important",
        title=f"Directive Issued: {title}",
        description=f"Chairman issued departmental directive to {lead_name} ({department}): '{instruction}'. Acknowledged: '{ack_text}'",
        world_day=world_day,
        source_type="staff",
        source_id=lead_role_id,
        participants=[
            {"role": "owner", "name": "Chairman & Owner"},
            {"role": department, "name": lead_name, "title": lead_title},
        ],
        consequences={"directive_id": directive.id, "deadline_day": deadline_day},
        idempotency_key=f"evt:{club_id}:{world_day}:dir:{directive.id}",
    )

    # Slight positive relationship shift for proactive leadership
    apply_relationship_delta(
        session,
        club_id,
        "owner",
        "owner",
        "Club Owner",
        "staff",
        lead_role_id,
        lead_name,
        delta_respect=2,
        delta_trust=1,
        reason=f"Issued strategic directive: {title}",
        world_day=world_day,
    )

    return format_directive_dict(directive)


def process_world_day_events(
    session: Session,
    state: OwnerClubState,
    campus_effects: dict[str, Any],
) -> dict[str, Any]:
    """Authoritative living world tick engine. Generates idempotent simulation-grounded events and updates social dynamics."""
    club_id = state.club_id
    world_day = int(state.world_day or 1)
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))
    players = list(
        session.scalars(
            select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id, OwnerSquadPlayer.status == "active")
        ).all()
    )

    ensure_default_relationships(session, state, players)

    new_events: list[OwnerClubEvent] = []

    # 1. Executive Cashflow / Treasury Scrutiny
    club_cash = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
    if club_cash < 1_500:
        evt, created = create_club_event(
            session,
            club_id,
            category="financial",
            event_type="treasury_low_reserves",
            severity="critical" if club_cash < 500 else "important",
            title="Treasury Working Capital Low",
            description=(
                f"Club operational balance has dropped to {int(club_cash):,} GTEX Coin. "
                f"General Manager recommends securing new commercial sponsors or capital injection."
            ),
            world_day=world_day,
            source_type="finance",
            source_id="treasury",
            participants=[
                {
                    "role": "general_manager",
                    "name": (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke"),
                }
            ],
            consequences={"current_balance": int(club_cash)},
            actions=[
                {"key": "review_sponsors", "label": "Review Sponsor Offers", "style": "primary"},
                {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:fin:low_cash",
        )
        if created:
            new_events.append(evt)

    # 2. Medical & Rehabilitation Simulation Events
    healed_players = [
        p
        for p in players
        if p.injured_days == 0 and (p.personality_json or {}).get("last_training_workload_tier") == "rehabilitation"
    ]
    for hp in healed_players[:2]:
        evt, created = create_club_event(
            session,
            club_id,
            category="medical",
            event_type="player_recovery_cleared",
            severity="important",
            title=f"Medical Clearance: {hp.name}",
            description=(
                f"{hp.name} has completed full physical rehabilitation at the Medical Centre "
                f"and has been cleared for full squad training by Dr. Amara Okafor."
            ),
            world_day=world_day,
            source_type="player",
            source_id=hp.id,
            participants=[
                {"role": "player", "id": hp.id, "name": hp.name},
                {
                    "role": "medical_director",
                    "name": (exec_staff.get("medical_director") or {}).get("name", "Dr. Amara Okafor"),
                },
            ],
            consequences={"fitness": (hp.personality_json or {}).get("fitness", 90), "player_id": hp.id},
            actions=[
                {"key": "praise_medical", "label": "Commend Medical Staff", "style": "primary"},
                {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:med:cleared:{hp.id}",
        )
        if created:
            new_events.append(evt)

    injured_players = [p for p in players if p.injured_days > 0]
    if len(injured_players) >= 3:
        evt, created = create_club_event(
            session,
            club_id,
            category="medical",
            event_type="injury_crisis_alert",
            severity="critical",
            title="Medical Department Under Strain",
            description=(
                f"{len(injured_players)} first-team players are currently sidelined with injuries. "
                f"The medical team advises reviewing training workload intensities."
            ),
            world_day=world_day,
            source_type="department",
            source_id="medical",
            participants=[
                {
                    "role": "medical_director",
                    "name": (exec_staff.get("medical_director") or {}).get("name", "Dr. Amara Okafor"),
                },
                {"role": "first_team_manager", "name": mgr.get("name", "First-Team Manager")},
            ],
            consequences={"injured_count": len(injured_players)},
            actions=[
                {"key": "reduce_workload", "label": "Reduce Training Intensity", "style": "primary"},
                {"key": "acknowledge", "label": "Maintain Program", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:med:crisis",
        )
        if created:
            new_events.append(evt)

    # 3. Academy & Youth Development Events
    promising_regens = [p for p in players if p.is_regen and p.rating >= 62]
    if promising_regens:
        top_regen = max(promising_regens, key=lambda p: p.rating)
        evt, created = create_club_event(
            session,
            club_id,
            category="academy",
            event_type="regen_prospect_spotlight",
            severity="important",
            title=f"Academy Spotlight: {top_regen.name}",
            description=(
                f"Academy graduate {top_regen.name} ({top_regen.position}, age {top_regen.age}) has reached "
                f"rating {top_regen.rating} (potential {top_regen.potential}). Head of Youth Development reports high senior squad readiness."
            ),
            world_day=world_day,
            source_type="player",
            source_id=top_regen.id,
            participants=[
                {"role": "player", "id": top_regen.id, "name": top_regen.name},
                {
                    "role": "head_of_youth_development",
                    "name": (exec_staff.get("head_of_youth_development") or {}).get("name", "Femi Ogunleye"),
                },
            ],
            consequences={"player_id": top_regen.id, "rating": top_regen.rating},
            actions=[
                {"key": "praise_prospect", "label": "Commend Player & HOYD", "style": "primary"},
                {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:acad:spotlight:{top_regen.id}",
        )
        if created:
            new_events.append(evt)

    # 4. Squad & Culture Events (Morale / Hierarchy)
    low_morale_players = [p for p in players if p.morale < 45]
    if low_morale_players:
        unhappy = low_morale_players[0]
        evt, created = create_club_event(
            session,
            club_id,
            category="squad",
            event_type="squad_morale_dip",
            severity="important",
            title=f"Dressing Room Concern: {unhappy.name}",
            description=(
                f"{unhappy.name}'s morale has dropped to {unhappy.morale}/100. "
                f"The squad leadership group suggests addressing player playing assurances."
            ),
            world_day=world_day,
            source_type="player",
            source_id=unhappy.id,
            participants=[
                {"role": "player", "id": unhappy.id, "name": unhappy.name},
                {"role": "first_team_manager", "name": mgr.get("name", "First-Team Manager")},
            ],
            consequences={"player_id": unhappy.id, "morale": unhappy.morale},
            actions=[
                {"key": "encourage_player", "label": "Hold Private Conversation", "style": "primary"},
                {"key": "ignore", "label": "Leave to Manager", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:sqd:morale:{unhappy.id}",
        )
        if created:
            new_events.append(evt)

    # 5. Tactical / Manager Harmony
    mgr_rel_key = pairing_key(club_id, "owner", "first_team_manager")
    mgr_rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == mgr_rel_key,
        )
    )
    if mgr_rel and mgr_rel.tension >= 50:
        evt, created = create_club_event(
            session,
            club_id,
            category="tactical",
            event_type="managerial_tension_alert",
            severity="critical",
            title=f"Tactical Friction with {mgr.get('name', 'Manager')}",
            description=(
                f"Operational friction with manager {mgr.get('name', 'First-Team Manager')} has escalated "
                f"(Tension {mgr_rel.tension}/100, Trust {mgr_rel.trust}/100). Tactical office requests board alignment."
            ),
            world_day=world_day,
            source_type="staff",
            source_id="first_team_manager",
            participants=[
                {"role": "first_team_manager", "name": mgr.get("name", "First-Team Manager")},
                {"role": "owner", "name": "Chairman & Owner"},
            ],
            consequences={"tension": mgr_rel.tension, "trust": mgr_rel.trust},
            actions=[
                {"key": "back_manager", "label": "Reaffirm Full Board Support", "style": "primary"},
                {"key": "demand_results", "label": "Demand Immediate Improvements", "style": "secondary"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:tac:tension",
        )
        if created:
            new_events.append(evt)

    # 6. Evaluate Active Directives
    active_directives = list(
        session.scalars(
            select(OwnerClubDirective).where(
                OwnerClubDirective.club_id == club_id,
                OwnerClubDirective.status == "active",
            )
        ).all()
    )
    for directive in active_directives:
        # Check deadline
        if directive.deadline_day and world_day >= directive.deadline_day:
            directive.status = "completed"
            directive.completed_at = utcnow()
            # Reward relationship trust
            lead_role = (
                "first_team_manager"
                if directive.department == "manager"
                else (
                    "medical_director"
                    if directive.department == "medical"
                    else (
                        "head_of_youth_development"
                        if directive.department == "academy"
                        else ("chief_scout" if directive.department == "scouting" else "general_manager")
                    )
                )
            )
            apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                lead_role,
                directive.acknowledged_by or "Department Head",
                delta_trust=6,
                delta_respect=5,
                delta_tension=-4,
                reason=f"Directive '{directive.title}' fulfilled successfully.",
                world_day=world_day,
            )
            evt, created = create_club_event(
                session,
                club_id,
                category="executive",
                event_type="directive_completed",
                severity="routine",
                title=f"Directive Completed: {directive.title}",
                description=f"Department {directive.department} has fulfilled Chairman's directive '{directive.instruction}'.",
                world_day=world_day,
                source_type="department",
                source_id=directive.department,
                consequences={"directive_id": directive.id, "status": "completed"},
                idempotency_key=f"evt:{club_id}:{world_day}:dir_done:{directive.id}",
            )
            if created:
                new_events.append(evt)

    session.flush()

    active_events = list(
        session.scalars(
            select(OwnerClubEvent)
            .where(
                OwnerClubEvent.club_id == club_id,
                OwnerClubEvent.status.in_(["active", "awaiting_decision"]),
            )
            .order_by(OwnerClubEvent.world_day.desc(), OwnerClubEvent.created_at.desc())
        ).all()
    )

    return {
        "world_day": world_day,
        "new_events_count": len(new_events),
        "total_active_events": len(active_events),
        "active_events": [format_event_dict(e) for e in active_events],
    }


def resolve_club_event(
    session: Session,
    user_id: str,
    club_id: str,
    event_id: str,
    action: str,
    resolution_note: str | None = None,
) -> dict[str, Any]:
    event = session.scalar(
        select(OwnerClubEvent).where(
            OwnerClubEvent.id == event_id,
            OwnerClubEvent.club_id == club_id,
        )
    )
    if event is None:
        raise ValueError("Event not found or does not belong to this club.")

    if event.status not in ("active", "awaiting_decision"):
        raise ValueError(f"Event cannot be resolved; status is '{event.status}'.")

    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    world_day = int(state.world_day or 1) if state else event.world_day
    mgr_name = (state.manager_json or {}).get("name", "First-Team Manager") if state else "First-Team Manager"

    consequences_applied: dict[str, Any] = {}

    # Event consequence handling
    if event.event_type == "managerial_tension_alert":
        if action == "back_manager":
            apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                "first_team_manager",
                mgr_name,
                delta_trust=10,
                delta_respect=8,
                delta_tension=-18,
                reason="Owner publicly reaffirmed full board backing for manager.",
                source_event_id=event.id,
                world_day=world_day,
            )
            consequences_applied["manager_mood_delta"] = 15
            consequences_applied["tension_delta"] = -18
        elif action == "demand_results":
            apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                "first_team_manager",
                mgr_name,
                delta_trust=-6,
                delta_respect=4,
                delta_tension=12,
                reason="Owner issued formal ultimatum demanding immediate tactical improvements.",
                source_event_id=event.id,
                world_day=world_day,
            )
            consequences_applied["manager_mood_delta"] = -10
            consequences_applied["tension_delta"] = 12

    elif event.event_type in ("squad_morale_dip", "player_discontent"):
        player_id = (event.consequences_json or {}).get("player_id") or event.source_id
        if player_id:
            player = session.get(OwnerSquadPlayer, player_id)
            if player:
                if action == "encourage_player":
                    player.morale = engine.clamp(player.morale + 15, 0, 100)
                    flag_modified(player, "morale")
                    apply_relationship_delta(
                        session,
                        club_id,
                        "owner",
                        "owner",
                        "Club Owner",
                        "player",
                        player.id,
                        player.name,
                        delta_trust=12,
                        delta_affinity=10,
                        delta_tension=-8,
                        reason="Owner held personal morale consultation with player.",
                        source_event_id=event.id,
                        world_day=world_day,
                    )
                    consequences_applied["player_morale"] = player.morale
                elif action == "ignore":
                    player.morale = engine.clamp(player.morale - 5, 0, 100)
                    flag_modified(player, "morale")
                    consequences_applied["player_morale"] = player.morale

    elif event.event_type == "player_recovery_cleared":
        if action == "praise_medical":
            apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                "medical_director",
                "Dr. Amara Okafor",
                delta_trust=8,
                delta_respect=8,
                delta_affinity=6,
                delta_tension=-5,
                reason="Owner commended medical team for timely player recovery clearance.",
                source_event_id=event.id,
                world_day=world_day,
            )
            consequences_applied["medical_trust_delta"] = 8

    elif event.event_type == "regen_prospect_spotlight":
        if action == "praise_prospect":
            apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                "head_of_youth_development",
                "Femi Ogunleye",
                delta_trust=8,
                delta_respect=8,
                delta_affinity=8,
                reason="Owner recognized academy breakthrough prospect.",
                source_event_id=event.id,
                world_day=world_day,
            )
            consequences_applied["hoyd_trust_delta"] = 8

    event.status = "resolved"
    event.resolution_action = action
    event.resolution_note = resolution_note or f"Action '{action}' executed by Chairman."
    event.resolved_at = utcnow()
    session.flush()

    return {
        "status": "resolved",
        "event": format_event_dict(event),
        "consequences_applied": consequences_applied,
    }


def get_living_world_timeline(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Returns a unified, chronological Living Club World timeline aggregating authoritative events, directives, and relationship shifts."""
    query = select(OwnerClubEvent).where(OwnerClubEvent.club_id == club_id)
    if category:
        query = query.where(OwnerClubEvent.category == category)
    if severity:
        query = query.where(OwnerClubEvent.severity == severity)
    if status:
        query = query.where(OwnerClubEvent.status == status)

    total_count = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    events = list(
        session.scalars(
            query.order_by(OwnerClubEvent.world_day.desc(), OwnerClubEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )

    directives = list(
        session.scalars(
            select(OwnerClubDirective)
            .where(OwnerClubDirective.club_id == club_id)
            .order_by(OwnerClubDirective.issued_day.desc(), OwnerClubDirective.created_at.desc())
            .limit(20)
        ).all()
    )

    relationship_milestones = list(
        session.scalars(
            select(OwnerClubRelationshipHistory)
            .where(
                OwnerClubRelationshipHistory.club_id == club_id,
                (func.abs(OwnerClubRelationshipHistory.delta_trust) >= 5)
                | (func.abs(OwnerClubRelationshipHistory.delta_tension) >= 5),
            )
            .order_by(OwnerClubRelationshipHistory.world_day.desc(), OwnerClubRelationshipHistory.created_at.desc())
            .limit(20)
        ).all()
    )

    timeline_items = []

    for ev in events:
        timeline_items.append(
            {
                "id": ev.id,
                "kind": "event",
                "category": ev.category,
                "severity": ev.severity,
                "title": ev.title,
                "description": ev.description,
                "world_day": ev.world_day,
                "status": ev.status,
                "participants": ev.participants_json or [],
                "consequences": ev.consequences_json or {},
                "actions": ev.actions_json or [],
                "resolved_at": ev.resolved_at.isoformat() if ev.resolved_at else None,
                "resolution_action": ev.resolution_action,
                "resolution_note": ev.resolution_note,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
        )

    for d in directives:
        timeline_items.append(
            {
                "id": d.id,
                "kind": "directive",
                "category": "executive",
                "severity": "important",
                "title": f"Directive: {d.title}",
                "description": f"Target: {d.department.title()} Department. {d.instruction}",
                "world_day": d.issued_day,
                "status": d.status,
                "participants": [{"role": d.department, "name": d.acknowledged_by or d.department}],
                "consequences": d.consequences_json or {},
                "actions": [],
                "resolved_at": d.completed_at.isoformat() if d.completed_at else None,
                "resolution_action": d.status,
                "resolution_note": d.acknowledgement_text,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
        )

    for rm in relationship_milestones:
        timeline_items.append(
            {
                "id": rm.id,
                "kind": "relationship_shift",
                "category": "culture",
                "severity": "routine" if abs(rm.delta_tension) < 10 else "important",
                "title": f"Relationship Milestone: {rm.reason}",
                "description": f"Trust delta: {rm.delta_trust:+d}, Tension delta: {rm.delta_tension:+d}.",
                "world_day": rm.world_day,
                "status": "resolved",
                "participants": [],
                "consequences": rm.snapshot_json or {},
                "actions": [],
                "resolved_at": rm.created_at.isoformat() if rm.created_at else None,
                "resolution_action": "shift_recorded",
                "resolution_note": rm.reason,
                "created_at": rm.created_at.isoformat() if rm.created_at else None,
            }
        )

    timeline_items.sort(
        key=lambda item: (item.get("world_day") or 0, item.get("created_at") or ""),
        reverse=True,
    )

    return {
        "club_id": club_id,
        "total_events_count": total_count,
        "limit": limit,
        "offset": offset,
        "items": timeline_items[:limit],
    }
