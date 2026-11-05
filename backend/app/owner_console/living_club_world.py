from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.base import utcnow
from app.owner_console import engine, ledger, service
from app.owner_console.models import (
    OwnerClubDirective,
    OwnerClubEvent,
    OwnerClubRelationship,
    OwnerClubRelationshipHistory,
    OwnerClubState,
    OwnerMatch,
    OwnerScoutingWatchlist,
    OwnerSponsorDeal,
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

DEPARTMENT_TO_ROLE_KEY = {
    "manager": "first_team_manager",
    "medical": "medical_director",
    "academy": "head_of_youth_development",
    "finance": "general_manager",
    "scouting": "chief_scout",
    "executive": "general_manager",
}

DEFAULT_STAFF_METRICS = {
    "first_team_manager": {"trust": 55, "respect": 60, "affinity": 50, "tension": 15},
    "general_manager": {"trust": 65, "respect": 65, "affinity": 60, "tension": 10},
    "head_of_youth_development": {"trust": 60, "respect": 60, "affinity": 55, "tension": 10},
    "medical_director": {"trust": 65, "respect": 70, "affinity": 55, "tension": 5},
    "chief_scout": {"trust": 55, "respect": 55, "affinity": 50, "tension": 15},
}

STAFF_ROLE_LABELS = {
    "first_team_manager": "First-Team Manager",
    "general_manager": "General Manager",
    "head_of_youth_development": "Head of Youth Development",
    "medical_director": "Medical Director",
    "chief_scout": "Chief Scout",
}

ALLOWED_ACTIONS_BY_EVENT_TYPE: dict[str, set[str]] = {
    "treasury_low_reserves": {"review_sponsors", "acknowledge"},
    "player_recovery_cleared": {"praise_medical", "acknowledge"},
    "injury_crisis_alert": {"reduce_workload", "acknowledge"},
    "regen_prospect_spotlight": {"praise_prospect", "acknowledge"},
    "squad_morale_dip": {"encourage_player", "ignore"},
    "player_discontent": {"encourage_player", "ignore"},
    "managerial_tension_alert": {"back_manager", "demand_results"},
    "contract_expiry_warning": {"open_renewal_talks", "acknowledge"},
    "scholar_contract_milestone": {"open_renewal_talks", "acknowledge"},
    "high_fatigue_workload_alert": {"rest_player", "acknowledge"},
    "tactical_readiness_briefing": {"endorse_tactics", "acknowledge"},
    "directive_dispatched": {"acknowledge"},
    "directive_completed": {"acknowledge"},
    "directive_expired": {"acknowledge"},
}


def _slugify_staff_id(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return cleaned or "staff"


def staff_participant_id(role_key: str, staff_record: dict[str, Any] | str | None) -> str:
    role_clean = str(role_key or "").strip()
    if isinstance(staff_record, dict):
        raw_uid = (
            staff_record.get("id")
            or staff_record.get("staff_id")
            or staff_record.get("manager_id")
            or staff_record.get("name")
            or staff_record.get("display_name")
            or role_clean
        )
        return f"{role_clean}:{_slugify_staff_id(str(raw_uid))}"
    if isinstance(staff_record, str):
        s = staff_record.strip()
        if ":" in s and s.split(":", 1)[0] in STAFF_ROLE_LABELS:
            return s
        return f"{role_clean}:{_slugify_staff_id(s)}"
    return f"{role_clean}:default"


def _extract_staff_role_key(participant_id: str, metadata: dict[str, Any] | None = None) -> str | None:
    if metadata and isinstance(metadata, dict) and metadata.get("role_key") in STAFF_ROLE_LABELS:
        return str(metadata["role_key"])
    prefix = str(participant_id or "").split(":", 1)[0].strip()
    if prefix in STAFF_ROLE_LABELS:
        return prefix
    return None


def resolve_club_staff_roster(state: OwnerClubState) -> dict[str, dict[str, Any]]:
    """Resolves the club's current staff roster strictly from authoritative appointed records.

    Unappointed roles are represented as vacant (`is_appointed=False`, `person_id=None`)
    and never fall back to fabricated personal identities.
    """
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})

    roster: dict[str, dict[str, Any]] = {}

    # 1. First-Team Manager
    mgr_exec = exec_staff.get("first_team_manager")
    mgr_raw: dict[str, Any] | None = None
    if isinstance(mgr_exec, dict) and str(mgr_exec.get("name") or "").strip() and not mgr_exec.get("is_vacant"):
        mgr_raw = dict(mgr_exec)
    elif (
        isinstance(state.manager_json, dict)
        and str(state.manager_json.get("name") or state.manager_json.get("display_name") or "").strip()
        and not state.manager_json.get("is_vacant")
    ):
        mgr_raw = dict(state.manager_json)

    if mgr_raw is not None:
        mgr_name = str(mgr_raw.get("name") or mgr_raw.get("display_name")).strip()
        mgr_person_id = staff_participant_id("first_team_manager", mgr_raw)
        roster["first_team_manager"] = {
            "role_key": "first_team_manager",
            "role_label": STAFF_ROLE_LABELS["first_team_manager"],
            "name": mgr_name,
            "person_id": mgr_person_id,
            "status": "appointed",
            "is_appointed": True,
            "is_default": bool(mgr_raw.get("is_default")),
        }
    else:
        roster["first_team_manager"] = {
            "role_key": "first_team_manager",
            "role_label": STAFF_ROLE_LABELS["first_team_manager"],
            "name": "First-Team Manager (Vacant)",
            "person_id": None,
            "status": "vacant",
            "is_appointed": False,
            "is_default": False,
        }

    # 2. Executive Department Heads
    for role_key in ("general_manager", "head_of_youth_development", "medical_director", "chief_scout"):
        role_label = STAFF_ROLE_LABELS[role_key]
        raw = exec_staff.get(role_key)
        is_appointed = bool(
            raw and isinstance(raw, dict) and str(raw.get("name") or "").strip() and not raw.get("is_vacant")
        )
        if is_appointed:
            staff_name = str(raw["name"]).strip()
            person_id = staff_participant_id(role_key, raw)
            roster[role_key] = {
                "role_key": role_key,
                "role_label": role_label,
                "name": staff_name,
                "person_id": person_id,
                "status": "appointed",
                "is_appointed": True,
                "is_default": False,
            }
        else:
            roster[role_key] = {
                "role_key": role_key,
                "role_label": role_label,
                "name": f"{role_label} (Vacant)",
                "person_id": None,
                "status": "vacant",
                "is_appointed": False,
                "is_default": False,
            }

    return roster


def reconcile_staff_relationships(session: Session, state: OwnerClubState) -> None:
    """Archives active staff relationships when a role becomes vacant or is filled by a different person.

    Preserves relationship records and audit history under the former person's participant ID
    so a new appointee never inherits a predecessor's relationship history.
    """
    roster = resolve_club_staff_roster(state)
    active_rows = list(
        session.scalars(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == state.club_id,
                OwnerClubRelationship.status == "active",
            )
        ).all()
    )
    changed = False
    for rel in active_rows:
        should_archive = False
        for p_type, p_id in (
            (rel.participant_a_type, rel.participant_a_id),
            (rel.participant_b_type, rel.participant_b_id),
        ):
            if p_type != "staff":
                continue
            role_key = _extract_staff_role_key(p_id, rel.metadata_json)
            if role_key and role_key in roster:
                slot = roster[role_key]
                if not slot["is_appointed"] or p_id != slot["person_id"]:
                    should_archive = True
                    break
        if should_archive:
            rel.status = "former"
            meta = dict(rel.metadata_json or {})
            meta["archived_world_day"] = int(state.world_day or 1)
            rel.metadata_json = meta
            rel.updated_at = utcnow()
            changed = True

    if changed:
        session.flush()


def normalize_pairing(part_a_id: str, part_b_id: str) -> tuple[str, str]:
    a = str(part_a_id or "").strip()
    b = str(part_b_id or "").strip()
    return (a, b) if a <= b else (b, a)


def pairing_key(club_id: str, part_a_id: str, part_b_id: str) -> str:
    p1, p2 = normalize_pairing(part_a_id, part_b_id)
    return f"{club_id}:{p1}:{p2}"


def deduplicate_club_relationships(session: Session, club_id: str | None = None) -> int:
    """Inspects and reconciles any duplicate or reversed participant relationship pairs while preserving history and latest metrics."""
    stmt = select(OwnerClubRelationship).order_by(
        OwnerClubRelationship.created_at.asc(),
        OwnerClubRelationship.id.asc(),
    )
    if club_id:
        stmt = stmt.where(OwnerClubRelationship.club_id == club_id)

    rows = list(session.scalars(stmt).all())
    seen: dict[tuple[str, str], OwnerClubRelationship] = {}
    latest_ts_by_pair: dict[tuple[str, str], Any] = {}
    removed_count = 0

    for idx, row in enumerate(rows):
        p1, p2 = normalize_pairing(row.participant_a_id, row.participant_b_id)
        canonical_key = f"{row.club_id}:{p1}:{p2}"
        pair_tuple = (row.club_id, canonical_key)
        row_sort_ts = (
            row.updated_at or row.created_at,
            row.created_at,
            idx,
        )

        if pair_tuple not in seen:
            seen[pair_tuple] = row
            latest_ts_by_pair[pair_tuple] = row_sort_ts
            if row.pairing_key != canonical_key or row.participant_a_id != p1:
                if row.participant_a_id != p1:
                    row.participant_a_type, row.participant_b_type = row.participant_b_type, row.participant_a_type
                    row.participant_a_id, row.participant_b_id = row.participant_b_id, row.participant_a_id
                    row.participant_a_name, row.participant_b_name = row.participant_b_name, row.participant_a_name
                row.pairing_key = canonical_key
        else:
            canonical_rel = seen[pair_tuple]
            prev_best_ts = latest_ts_by_pair[pair_tuple]
            # Preserve the authoritative latest relationship metrics when merging duplicate rows
            is_newer = True
            if prev_best_ts[0] is not None and row_sort_ts[0] is not None:
                is_newer = row_sort_ts >= prev_best_ts
            if is_newer:
                canonical_rel.trust = row.trust
                canonical_rel.respect = row.respect
                canonical_rel.affinity = row.affinity
                canonical_rel.tension = row.tension
                if row.updated_at is not None:
                    canonical_rel.updated_at = row.updated_at
                latest_ts_by_pair[pair_tuple] = row_sort_ts

            hist_rows = list(
                session.scalars(
                    select(OwnerClubRelationshipHistory).where(OwnerClubRelationshipHistory.relationship_id == row.id)
                ).all()
            )
            for h in hist_rows:
                h.relationship_id = canonical_rel.id
            session.delete(row)
            removed_count += 1

    if removed_count > 0:
        session.flush()
    return removed_count


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


def _resolve_participant_for_club(
    session: Session,
    club_id: str,
    part_type: str,
    part_id: str,
    part_name: str,
    *,
    roster: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, str, str | None] | None:
    """Resolves a participant reference. Returns (canonical_id, canonical_name, role_key) or None if vacant."""
    clean_id = str(part_id or "").strip()
    clean_name = str(part_name or "").strip()
    if part_type != "staff":
        return clean_id, clean_name, None

    role_key = clean_id.split(":", 1)[0] if ":" in clean_id else clean_id
    if role_key not in STAFF_ROLE_LABELS:
        return clean_id, clean_name, None

    if roster is None:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        if state is not None:
            reconcile_staff_relationships(session, state)
            roster = resolve_club_staff_roster(state)

    if roster is not None:
        slot = roster.get(role_key)
        if not slot or not slot["is_appointed"]:
            return None
        if ":" not in clean_id:
            return str(slot["person_id"]), str(slot["name"]), role_key
        if clean_id == slot["person_id"]:
            return str(slot["person_id"]), str(slot["name"]), role_key

    if ":" not in clean_id:
        if not clean_name or "vacant" in clean_name.lower():
            return None
        return staff_participant_id(role_key, {"name": clean_name}), clean_name, role_key

    return clean_id, clean_name, role_key


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
    metadata: dict[str, Any] | None = None,
) -> OwnerClubRelationship:
    clean_a_id = str(part_a_id or "").strip()
    clean_b_id = str(part_b_id or "").strip()
    key = pairing_key(club_id, clean_a_id, clean_b_id)

    rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == key,
        )
    )
    if rel is not None:
        if rel.status != "active":
            rel.status = "active"
            session.flush()
        return rel

    p1, _ = normalize_pairing(clean_a_id, clean_b_id)
    if p1 == clean_a_id:
        f_type_a, f_id_a, f_name_a = part_a_type, clean_a_id, part_a_name
        f_type_b, f_id_b, f_name_b = part_b_type, clean_b_id, part_b_name
    else:
        f_type_a, f_id_a, f_name_a = part_b_type, clean_b_id, part_b_name
        f_type_b, f_id_b, f_name_b = part_a_type, clean_a_id, part_a_name

    role_b = _extract_staff_role_key(clean_b_id, metadata)
    role_a = _extract_staff_role_key(clean_a_id, metadata)
    staff_role = role_b or role_a
    def_metrics = (
        DEFAULT_STAFF_METRICS.get(staff_role or "")
        or DEFAULT_STAFF_METRICS.get(clean_b_id)
        or DEFAULT_STAFF_METRICS.get(clean_a_id)
        or {}
    )
    t = initial_trust if initial_trust is not None else def_metrics.get("trust", 50)
    r = initial_respect if initial_respect is not None else def_metrics.get("respect", 50)
    a = initial_affinity if initial_affinity is not None else def_metrics.get("affinity", 50)
    ten = initial_tension if initial_tension is not None else def_metrics.get("tension", 20)

    rel_meta = dict(metadata or {})
    if staff_role and "role_key" not in rel_meta:
        rel_meta["role_key"] = staff_role

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
        metadata_json=rel_meta,
    )
    try:
        with session.begin_nested():
            session.add(rel)
            session.flush()
        return rel
    except IntegrityError:
        existing = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == club_id,
                OwnerClubRelationship.pairing_key == key,
            )
        )
        if existing is not None:
            return existing
        raise


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
) -> OwnerClubRelationship | None:
    resolved_a = _resolve_participant_for_club(session, club_id, part_a_type, part_a_id, part_a_name)
    if resolved_a is None:
        return None
    resolved_b = _resolve_participant_for_club(session, club_id, part_b_type, part_b_id, part_b_name)
    if resolved_b is None:
        return None

    canon_a_id, canon_a_name, role_a = resolved_a
    canon_b_id, canon_b_name, role_b = resolved_b
    meta: dict[str, Any] = {}
    if role_b or role_a:
        meta["role_key"] = role_b or role_a

    rel = get_or_create_relationship(
        session,
        club_id,
        part_a_type,
        canon_a_id,
        canon_a_name,
        part_b_type,
        canon_b_id,
        canon_b_name,
        metadata=meta,
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
    """Ensures baseline relationships only for currently appointed staff and the squad captain.

    Vacant positions never receive fabricated employee relationships. Replaced staff members
    have their previous relationship rows archived (`status='former'`) with history intact.
    """
    club_id = state.club_id
    reconcile_staff_relationships(session, state)
    roster = resolve_club_staff_roster(state)

    captain = None
    if squad_players:
        sorted_candidates = sorted(
            squad_players,
            key=lambda p: (int((p.personality_json or {}).get("leadership", 10)), p.rating, p.age),
            reverse=True,
        )
        captain = sorted_candidates[0]

    relationships: list[OwnerClubRelationship] = []

    # 1. Owner <-> Appointed Staff Roles
    for role_key in (
        "first_team_manager",
        "general_manager",
        "head_of_youth_development",
        "medical_director",
        "chief_scout",
    ):
        slot = roster[role_key]
        if not slot["is_appointed"] or not slot["person_id"]:
            continue
        metrics = DEFAULT_STAFF_METRICS[role_key]
        relationships.append(
            get_or_create_relationship(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                slot["person_id"],
                slot["name"],
                initial_trust=metrics["trust"],
                initial_respect=metrics["respect"],
                initial_affinity=metrics["affinity"],
                initial_tension=metrics["tension"],
                metadata={
                    "role_key": role_key,
                    "role_label": slot["role_label"],
                    "is_default": slot["is_default"],
                },
            )
        )

    mgr_slot = roster["first_team_manager"]
    med_slot = roster["medical_director"]
    hoyd_slot = roster["head_of_youth_development"]

    # 2. Manager <-> Medical Director (only if both are appointed)
    if mgr_slot["is_appointed"] and med_slot["is_appointed"]:
        relationships.append(
            get_or_create_relationship(
                session,
                club_id,
                "staff",
                mgr_slot["person_id"],
                mgr_slot["name"],
                "staff",
                med_slot["person_id"],
                med_slot["name"],
                initial_trust=50,
                initial_respect=60,
                initial_affinity=45,
                initial_tension=25,
                metadata={"role_pair": ["first_team_manager", "medical_director"]},
            )
        )

    # 3. Manager <-> Head of Youth Development (only if both are appointed)
    if mgr_slot["is_appointed"] and hoyd_slot["is_appointed"]:
        relationships.append(
            get_or_create_relationship(
                session,
                club_id,
                "staff",
                mgr_slot["person_id"],
                mgr_slot["name"],
                "staff",
                hoyd_slot["person_id"],
                hoyd_slot["name"],
                initial_trust=55,
                initial_respect=55,
                initial_affinity=50,
                initial_tension=20,
                metadata={"role_pair": ["first_team_manager", "head_of_youth_development"]},
            )
        )

    # 4. Owner <-> Captain & Manager <-> Captain
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
                metadata={"player_role": "captain"},
            )
        )
        if mgr_slot["is_appointed"]:
            relationships.append(
                get_or_create_relationship(
                    session,
                    club_id,
                    "staff",
                    mgr_slot["person_id"],
                    mgr_slot["name"],
                    "player",
                    captain.id,
                    f"{captain.name} (C)",
                    initial_trust=65,
                    initial_respect=70,
                    initial_affinity=60,
                    initial_tension=15,
                    metadata={"player_role": "captain", "role_key": "first_team_manager"},
                )
            )

    return relationships


def format_relationship_dict(rel: OwnerClubRelationship) -> dict[str, Any]:
    meta = dict(rel.metadata_json or {})
    role_key = _extract_staff_role_key(rel.participant_b_id, meta) or _extract_staff_role_key(
        rel.participant_a_id, meta
    )
    if role_key and "role_key" not in meta:
        meta["role_key"] = role_key
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
        "role_key": role_key,
        "trust": rel.trust,
        "respect": rel.respect,
        "affinity": rel.affinity,
        "tension": rel.tension,
        "status": rel.status,
        "status_label": compute_relationship_status_label(rel.trust, rel.respect, rel.affinity, rel.tension),
        "metadata": meta,
        "created_at": rel.created_at.isoformat() if rel.created_at else None,
        "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
    }


def get_club_relationships(session: Session, club_id: str) -> list[dict[str, Any]]:
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if state is not None:
        reconcile_staff_relationships(session, state)
    rows = list(
        session.scalars(
            select(OwnerClubRelationship)
            .where(OwnerClubRelationship.club_id == club_id, OwnerClubRelationship.status == "active")
            .order_by(OwnerClubRelationship.created_at.asc())
        ).all()
    )
    return [format_relationship_dict(r) for r in rows]


def get_relationship_for_department(session: Session, club_id: str, department_lead_role: str) -> dict[str, Any] | None:
    state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
    if state is not None:
        reconcile_staff_relationships(session, state)
        roster = resolve_club_staff_roster(state)
        slot = roster.get(department_lead_role)
        if not slot or not slot["is_appointed"] or not slot["person_id"]:
            return None
        key = pairing_key(club_id, "owner", slot["person_id"])
        rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == club_id,
                OwnerClubRelationship.pairing_key == key,
                OwnerClubRelationship.status == "active",
            )
        )
        return format_relationship_dict(rel) if rel else None

    key = pairing_key(club_id, "owner", department_lead_role)
    rel = session.scalar(
        select(OwnerClubRelationship).where(
            OwnerClubRelationship.club_id == club_id,
            OwnerClubRelationship.pairing_key == key,
            OwnerClubRelationship.status == "active",
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


def _capture_directive_baseline_snapshot(
    session: Session,
    state: OwnerClubState,
    squad_players: list[OwnerSquadPlayer],
    roster: dict[str, dict[str, Any]],
    *,
    target_scope: str | None = None,
    target_scope_id: str | None = None,
) -> dict[str, Any]:
    """Captures an authoritative snapshot of club, squad, facility, and ledger state when a directive is issued or evaluated."""
    club_id = state.club_id
    facs = dict(state.facilities_json or {})
    active_players = [p for p in squad_players if p.status == "active"]
    regens = [p for p in active_players if p.is_regen]

    club_cash_gtex = int(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX))
    active_sponsors_count = int(
        session.scalar(
            select(func.count())
            .select_from(OwnerSponsorDeal)
            .where(OwnerSponsorDeal.club_id == club_id, OwnerSponsorDeal.status == "active")
        )
        or 0
    )
    watchlist_count = int(
        session.scalar(
            select(func.count()).select_from(OwnerScoutingWatchlist).where(OwnerScoutingWatchlist.club_id == club_id)
        )
        or 0
    )
    matches_played = int(
        session.scalar(
            select(func.count())
            .select_from(OwnerMatch)
            .where(
                ((OwnerMatch.home_club_id == club_id) | (OwnerMatch.away_club_id == club_id)),
                OwnerMatch.status == "completed",
            )
        )
        or 0
    )

    first_team_regens_count = sum(1 for p in regens if (p.personality_json or {}).get("squad_status") == "first_team")
    improved_youth_contracts_count = sum(
        1
        for p in regens
        if (p.personality_json or {}).get("contract_tier") in ("improved_youth", "scholar_extended", "senior_prospect")
        or int((p.personality_json or {}).get("contract_years", 0)) >= 3
        or int((p.personality_json or {}).get("contract_renewal_talks_opened_day", 0)) > 0
    )
    total_regen_rating = sum(int(p.rating or 0) for p in regens)
    max_regen_rating = max((int(p.rating or 0) for p in regens), default=0)

    injured_count = sum(1 for p in active_players if int(p.injured_days or 0) > 0)
    total_injured_days = sum(int(p.injured_days or 0) for p in active_players)
    fitness_values = [int((p.personality_json or {}).get("fitness", 95)) for p in active_players]
    min_fitness = min(fitness_values, default=95)
    avg_fitness = int(sum(fitness_values) / max(1, len(fitness_values)))
    avg_morale = int(sum(int(p.morale or 70) for p in active_players) / max(1, len(active_players)))
    max_fatigue = max((int((p.personality_json or {}).get("fatigue", 0)) for p in active_players), default=0)

    campus_projects = list(facs.get("_campus_projects") or [])
    completed_campus_stages = sum(int(proj.get("stage_index", 0)) for proj in campus_projects if isinstance(proj, dict))
    decision_history = list(facs.get("_operational_decision_history") or [])

    snapshot: dict[str, Any] = {
        "world_day": int(state.world_day or 1),
        "club_cash_gtex": club_cash_gtex,
        "prestige": int(state.prestige or 0),
        "mentality": str(state.mentality or "balanced"),
        "formation": str(facs.get("_tactical_formation") or "4-3-3"),
        "training_intensity": str(facs.get("_training_intensity") or "standard"),
        "sponsor_review_day": int(facs.get("_treasury_sponsor_review_day") or 0),
        "active_sponsors_count": active_sponsors_count,
        "watchlist_count": watchlist_count,
        "squad_count": len(active_players),
        "regens_count": len(regens),
        "first_team_regens_count": first_team_regens_count,
        "improved_youth_contracts_count": improved_youth_contracts_count,
        "total_regen_rating": total_regen_rating,
        "max_regen_rating": max_regen_rating,
        "injured_count": injured_count,
        "total_injured_days": total_injured_days,
        "min_fitness": min_fitness,
        "avg_fitness": avg_fitness,
        "avg_morale": avg_morale,
        "max_fatigue": max_fatigue,
        "medical_facility_level": int(facs.get("medical", 1)),
        "academy_facility_level": int(facs.get("academy", 1)),
        "training_facility_level": int(facs.get("training", 1)),
        "commercial_facility_level": int(facs.get("commercial", 1)),
        "stadium_facility_level": int(facs.get("stadium", 1)),
        "campus_projects_count": len(campus_projects),
        "completed_campus_stages": completed_campus_stages,
        "appointed_staff_count": sum(1 for s in roster.values() if s.get("is_appointed")),
        "matches_played": matches_played,
        "resolved_decisions_count": len(decision_history),
    }

    if target_scope == "player" and target_scope_id:
        target_player = next((p for p in squad_players if p.id == target_scope_id), None)
        if target_player is not None:
            t_pers = dict(target_player.personality_json or {})
            snapshot["target_player"] = {
                "id": target_player.id,
                "injured_days": int(target_player.injured_days or 0),
                "fitness": int(t_pers.get("fitness", 95)),
                "fatigue": int(t_pers.get("fatigue", 0)),
                "morale": int(target_player.morale or 70),
                "rating": int(target_player.rating or 60),
                "minutes": int(target_player.minutes or 0),
                "squad_status": str(t_pers.get("squad_status") or "squad"),
                "contract_renewal_day": int(t_pers.get("contract_renewal_talks_opened_day", 0)),
            }

    return snapshot


def _evaluate_directive_completion(
    session: Session,
    state: OwnerClubState,
    directive: OwnerClubDirective,
    roster: dict[str, dict[str, Any]],
    squad_players: list[OwnerSquadPlayer],
) -> tuple[bool, int, dict[str, Any]]:
    """Evaluates whether an active departmental directive has genuinely satisfied its authoritative completion conditions.

    Returns (is_fulfilled, progress_pct, evidence_dict).
    Vacant departments never receive automatic completion.
    """
    lead_role_id = DEPARTMENT_TO_ROLE_KEY.get(directive.department, "general_manager")
    lead_slot = roster.get(lead_role_id)

    # Rule: Vacant departments must NEVER receive automatic success
    if not lead_slot or not lead_slot.get("is_appointed") or not lead_slot.get("person_id"):
        return (
            False,
            0,
            {
                "verified": False,
                "reason": "department_lead_vacant",
                "department": directive.department,
                "lead_role": lead_role_id,
                "lead_status": "vacant",
                "matched_checks": [],
            },
        )

    consequences = dict(directive.consequences_json or {})
    baseline = dict(consequences.get("baseline_snapshot") or {})
    if not baseline:
        return (
            False,
            0,
            {
                "verified": False,
                "reason": "missing_baseline_snapshot",
                "department": directive.department,
                "lead_role": lead_role_id,
                "lead_status": "appointed",
                "matched_checks": [],
            },
        )

    current = _capture_directive_baseline_snapshot(
        session,
        state,
        squad_players,
        roster,
        target_scope=directive.target_scope,
        target_scope_id=directive.target_scope_id,
    )

    matched_checks: list[str] = []
    dept = directive.department

    # Target player-specific checks when target_scope == "player"
    base_tp = baseline.get("target_player")
    cur_tp = current.get("target_player")
    if isinstance(base_tp, dict) and isinstance(cur_tp, dict):
        if dept == "medical":
            if cur_tp["injured_days"] < base_tp["injured_days"]:
                matched_checks.append("target_player_injury_reduced")
            if cur_tp["fitness"] > base_tp["fitness"]:
                matched_checks.append("target_player_fitness_improved")
            if base_tp.get("fatigue", 0) > 0 and cur_tp.get("fatigue", 0) < base_tp.get("fatigue", 0):
                matched_checks.append("target_player_fatigue_reduced")
        elif dept == "academy":
            if cur_tp["rating"] > base_tp["rating"]:
                matched_checks.append("target_player_rating_grown")
            if cur_tp["squad_status"] == "first_team" and base_tp.get("squad_status") != "first_team":
                matched_checks.append("target_player_promoted_to_first_team")
            if cur_tp["contract_renewal_day"] > base_tp.get("contract_renewal_day", 0):
                matched_checks.append("target_player_contract_progressed")
        elif dept == "manager":
            if cur_tp["morale"] > base_tp["morale"]:
                matched_checks.append("target_player_morale_improved")
            if cur_tp["minutes"] > base_tp["minutes"]:
                matched_checks.append("target_player_minutes_increased")

    # Department-wide authoritative completion checks
    if dept == "medical":
        if baseline.get("total_injured_days", 0) > 0 and current["total_injured_days"] < baseline["total_injured_days"]:
            matched_checks.append("injury_rehabilitation_days_reduced")
        if baseline.get("injured_count", 0) > 0 and current["injured_count"] < baseline["injured_count"]:
            matched_checks.append("injured_player_cleared_for_training")
        if current["training_intensity"] == "light_recovery" and baseline.get("training_intensity") != "light_recovery":
            matched_checks.append("recovery_workload_protocol_activated")
        if current["medical_facility_level"] > baseline.get("medical_facility_level", 1):
            matched_checks.append("medical_facility_upgraded")
        if current["min_fitness"] > baseline.get("min_fitness", 95) or current["avg_fitness"] > baseline.get(
            "avg_fitness", 95
        ):
            matched_checks.append("squad_conditioning_improved")
        if baseline.get("max_fatigue", 0) > 0 and current["max_fatigue"] < baseline.get("max_fatigue", 0):
            matched_checks.append("squad_fatigue_reduced")

    elif dept == "academy":
        if current["regens_count"] > baseline.get("regens_count", 0):
            matched_checks.append("academy_intake_inducted")
        if current["first_team_regens_count"] > baseline.get("first_team_regens_count", 0):
            matched_checks.append("academy_prospect_promoted")
        if current["improved_youth_contracts_count"] > baseline.get("improved_youth_contracts_count", 0):
            matched_checks.append("youth_contract_extended")
        if current["total_regen_rating"] > baseline.get("total_regen_rating", 0) or current[
            "max_regen_rating"
        ] > baseline.get("max_regen_rating", 0):
            matched_checks.append("regen_rating_developed")
        if current["academy_facility_level"] > baseline.get("academy_facility_level", 1):
            matched_checks.append("academy_facility_upgraded")

    elif dept == "finance":
        if current["active_sponsors_count"] > baseline.get("active_sponsors_count", 0):
            matched_checks.append("commercial_sponsor_signed")
        if current["club_cash_gtex"] > baseline.get("club_cash_gtex", 0):
            matched_checks.append("treasury_balance_increased")
        if current["sponsor_review_day"] >= int(directive.issued_day or 1) and current[
            "sponsor_review_day"
        ] > baseline.get("sponsor_review_day", 0):
            matched_checks.append("commercial_sponsor_review_completed")
        if current["commercial_facility_level"] > baseline.get("commercial_facility_level", 1) or current[
            "stadium_facility_level"
        ] > baseline.get("stadium_facility_level", 1):
            matched_checks.append("revenue_infrastructure_upgraded")

    elif dept == "scouting":
        if current["watchlist_count"] > baseline.get("watchlist_count", 0):
            matched_checks.append("scouting_watchlist_expanded")
        if current["squad_count"] > baseline.get("squad_count", 0):
            matched_checks.append("player_recruited_to_squad")

    elif dept == "manager":
        if current["mentality"] != baseline.get("mentality"):
            matched_checks.append(f"tactical_mentality_updated:{current['mentality']}")
        if current["formation"] != baseline.get("formation"):
            matched_checks.append(f"tactical_formation_updated:{current['formation']}")
        if current["avg_morale"] > baseline.get("avg_morale", 70):
            matched_checks.append("squad_morale_improved")
        if current["matches_played"] > baseline.get("matches_played", 0):
            matched_checks.append("competitive_fixture_completed")
        if current["training_facility_level"] > baseline.get("training_facility_level", 1):
            matched_checks.append("training_facility_upgraded")

    elif dept == "executive":
        if current["campus_projects_count"] > baseline.get("campus_projects_count", 0) or current[
            "completed_campus_stages"
        ] > baseline.get("completed_campus_stages", 0):
            matched_checks.append("campus_infrastructure_advanced")
        if current["prestige"] > baseline.get("prestige", 0):
            matched_checks.append("club_prestige_increased")
        if current["appointed_staff_count"] > baseline.get("appointed_staff_count", 0):
            matched_checks.append("executive_staff_appointed")
        if current["resolved_decisions_count"] > baseline.get("resolved_decisions_count", 0):
            matched_checks.append("operational_decision_executed")

    is_fulfilled = len(matched_checks) > 0
    progress_pct = 100 if is_fulfilled else 0
    evidence = {
        "verified": is_fulfilled,
        "reason": "verified_department_outcome" if is_fulfilled else "awaiting_authoritative_department_outcome",
        "department": dept,
        "lead_role": lead_role_id,
        "lead_person_id": lead_slot["person_id"],
        "lead_name": lead_slot["name"],
        "lead_status": lead_slot["status"],
        "matched_checks": matched_checks,
        "evaluated_at_world_day": int(state.world_day or 1),
    }
    return is_fulfilled, progress_pct, evidence


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
    state = service.require_state(session, club_id, user_id)
    if department not in DIRECTIVE_DEPARTMENTS:
        raise service.OwnerError(
            "invalid_directive_department",
            400,
            f"Invalid department '{department}'. Must be one of {DIRECTIVE_DEPARTMENTS}.",
        )

    squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    ensure_default_relationships(session, state, squad_players)
    roster = resolve_club_staff_roster(state)

    world_day = int(state.world_day or 1)
    deadline_day = (world_day + deadline_days) if deadline_days else None

    lead_role_id = DEPARTMENT_TO_ROLE_KEY[department]
    slot = roster[lead_role_id]
    lead_title = "Executive Directorate" if department == "executive" else slot["role_label"]

    if slot["is_appointed"] and slot["person_id"]:
        lead_name = slot["name"]
        acknowledged_by = f"{lead_name} ({lead_title})"
        rel_key = pairing_key(club_id, "owner", slot["person_id"])
        rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == club_id,
                OwnerClubRelationship.pairing_key == rel_key,
                OwnerClubRelationship.status == "active",
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
                f"Directive acknowledged, Chairman. {lead_name} and the {department} division have scheduled implementation "
                f"with milestone targets for World Day {deadline_day}."
            )
    else:
        lead_name = f"{lead_title} (Vacant)"
        acknowledged_by = f"Vacant ({lead_title} Unappointed)"
        trust = 50
        tension = 20
        ack_text = (
            f"Directive logged with provisional {department} operations desk ({lead_title} position is currently vacant). "
            f"Baseline implementation scheduled for World Day {deadline_day}."
        )

    baseline_snapshot = _capture_directive_baseline_snapshot(
        session,
        state,
        squad_players,
        roster,
        target_scope=target_scope,
        target_scope_id=target_scope_id,
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
        acknowledged_by=acknowledged_by,
        acknowledgement_text=ack_text,
        consequences_json={
            "initial_trust": trust,
            "department": department,
            "target_scope": target_scope,
            "lead_status": slot["status"],
            "progress_pct": 0,
            "verification_status": "pending",
            "reward_granted": False,
            "baseline_snapshot": baseline_snapshot,
        },
    )
    session.add(directive)
    session.flush()

    create_club_event(
        session,
        club_id,
        category="executive",
        event_type="directive_dispatched",
        severity="important",
        title=f"Directive Issued: {title}",
        description=f"Chairman issued departmental directive to {acknowledged_by} ({department}): '{instruction}'. Acknowledged: '{ack_text}'",
        world_day=world_day,
        source_type="staff" if slot["is_appointed"] else "department",
        source_id=slot["person_id"] or lead_role_id,
        participants=[
            {"role": "owner", "name": "Chairman & Owner"},
            {
                "role": department,
                "name": lead_name,
                "title": lead_title,
                "status": slot["status"],
            },
        ],
        consequences={"directive_id": directive.id, "deadline_day": deadline_day, "lead_status": slot["status"]},
        actions=[{"key": "acknowledge", "label": "Acknowledge", "style": "ghost"}],
        idempotency_key=f"evt:{club_id}:{world_day}:dir:{directive.id}",
    )

    if slot["is_appointed"] and slot["person_id"]:
        apply_relationship_delta(
            session,
            club_id,
            "owner",
            "owner",
            "Club Owner",
            "staff",
            slot["person_id"],
            slot["name"],
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
    players = list(
        session.scalars(
            select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id, OwnerSquadPlayer.status == "active")
        ).all()
    )

    ensure_default_relationships(session, state, players)
    roster = resolve_club_staff_roster(state)
    mgr_slot = roster["first_team_manager"]
    gm_slot = roster["general_manager"]
    hoyd_slot = roster["head_of_youth_development"]
    med_slot = roster["medical_director"]

    new_events: list[OwnerClubEvent] = []

    # 1. Executive Cashflow / Treasury Scrutiny
    club_cash = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
    if club_cash < 1_500:
        if gm_slot["is_appointed"]:
            fin_desc = (
                f"Club operational balance has dropped to {int(club_cash):,} GTEX Coin. "
                f"General Manager {gm_slot['name']} recommends securing new commercial sponsors or capital injection."
            )
            fin_participants = [
                {
                    "role": "general_manager",
                    "id": gm_slot["person_id"],
                    "name": gm_slot["name"],
                    "status": "appointed",
                }
            ]
        else:
            fin_desc = (
                f"Club operational balance has dropped to {int(club_cash):,} GTEX Coin. "
                f"With the General Manager position vacant, the provisional finance desk recommends securing new commercial sponsors."
            )
            fin_participants = [
                {
                    "role": "general_manager",
                    "name": gm_slot["name"],
                    "status": "vacant",
                }
            ]

        evt, created = create_club_event(
            session,
            club_id,
            category="financial",
            event_type="treasury_low_reserves",
            severity="critical" if club_cash < 500 else "important",
            title="Treasury Working Capital Low",
            description=fin_desc,
            world_day=world_day,
            source_type="finance",
            source_id="treasury",
            participants=fin_participants,
            consequences={"current_balance": int(club_cash), "gm_status": gm_slot["status"]},
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
        if med_slot["is_appointed"]:
            med_desc = (
                f"{hp.name} has completed full physical rehabilitation at the Medical Centre "
                f"and has been cleared for full squad training by Medical Director {med_slot['name']}."
            )
            med_part = {
                "role": "medical_director",
                "id": med_slot["person_id"],
                "name": med_slot["name"],
                "status": "appointed",
            }
        else:
            med_desc = (
                f"{hp.name} has completed physical rehabilitation at the Medical Centre "
                f"and has been cleared for full squad training by the club rehabilitation unit (Medical Director vacant)."
            )
            med_part = {
                "role": "medical_director",
                "name": med_slot["name"],
                "status": "vacant",
            }

        evt, created = create_club_event(
            session,
            club_id,
            category="medical",
            event_type="player_recovery_cleared",
            severity="important",
            title=f"Medical Clearance: {hp.name}",
            description=med_desc,
            world_day=world_day,
            source_type="player",
            source_id=hp.id,
            participants=[
                {"role": "player", "id": hp.id, "name": hp.name},
                med_part,
            ],
            consequences={
                "fitness": (hp.personality_json or {}).get("fitness", 90),
                "player_id": hp.id,
                "medical_director_status": med_slot["status"],
            },
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
                f"The medical department advises reviewing training workload intensities."
            ),
            world_day=world_day,
            source_type="department",
            source_id="medical",
            participants=[
                {
                    "role": "medical_director",
                    "name": med_slot["name"],
                    "status": med_slot["status"],
                },
                {
                    "role": "first_team_manager",
                    "name": mgr_slot["name"],
                    "status": mgr_slot["status"],
                },
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

    # High Fatigue / Low Conditioning Alert (grounded strictly in stored fitness/fatigue values)
    fatigued_healthy_players = [
        p
        for p in players
        if p.injured_days == 0
        and (
            ("fitness" in (p.personality_json or {}) and int((p.personality_json or {}).get("fitness", 95)) < 70)
            or ("fatigue" in (p.personality_json or {}) and int((p.personality_json or {}).get("fatigue", 0)) >= 70)
        )
    ]
    if fatigued_healthy_players:

        def _fatigue_alert_priority(player_row: OwnerSquadPlayer) -> tuple[int, int]:
            p_pers = dict(player_row.personality_json or {})
            fit_val = int(p_pers.get("fitness", 95))
            fat_val = int(p_pers.get("fatigue", 0))
            low_fit_deficit = max(0, 70 - fit_val) if "fitness" in p_pers and fit_val < 70 else 0
            high_fat_excess = max(0, fat_val - 69) if "fatigue" in p_pers and fat_val >= 70 else 0
            return (max(low_fit_deficit, high_fat_excess), high_fat_excess)

        fatigued = max(fatigued_healthy_players, key=_fatigue_alert_priority)
        f_pers = dict(fatigued.personality_json or {})
        has_low_fitness = "fitness" in f_pers and int(f_pers.get("fitness", 95)) < 70
        has_high_fatigue = "fatigue" in f_pers and int(f_pers.get("fatigue", 0)) >= 70
        cur_fit = int(f_pers.get("fitness", 95))
        cur_fatigue = int(f_pers.get("fatigue", 0))

        if has_high_fatigue and not has_low_fitness:
            trigger_metric = "fatigue"
            fatigue_desc = (
                f"{fatigued.name} ({fatigued.position}) has accumulated a high workload fatigue reading of "
                f"{cur_fatigue}/100 (Conditioning {cur_fit}%). Sports science staff recommend a recovery rest session."
            )
            fatigue_consequences: dict[str, Any] = {
                "player_id": fatigued.id,
                "trigger_metric": "fatigue",
                "fatigue": cur_fatigue,
                "fitness": cur_fit,
            }
        elif has_low_fitness and not has_high_fatigue:
            trigger_metric = "fitness"
            fatigue_desc = (
                f"{fatigued.name} ({fatigued.position}) has dropped to {cur_fit}% match conditioning. "
                f"Sports science staff recommend a recovery rest session."
            )
            fatigue_consequences = {
                "player_id": fatigued.id,
                "trigger_metric": "fitness",
                "fitness": cur_fit,
            }
        else:
            trigger_metric = "fatigue_and_fitness"
            fatigue_desc = (
                f"{fatigued.name} ({fatigued.position}) has accumulated a workload fatigue reading of "
                f"{cur_fatigue}/100 and dropped to {cur_fit}% match conditioning. "
                f"Sports science staff recommend a recovery rest session."
            )
            fatigue_consequences = {
                "player_id": fatigued.id,
                "trigger_metric": trigger_metric,
                "fatigue": cur_fatigue,
                "fitness": cur_fit,
            }

        evt, created = create_club_event(
            session,
            club_id,
            category="medical",
            event_type="high_fatigue_workload_alert",
            severity="important",
            title=f"Workload Fatigue Warning: {fatigued.name}",
            description=fatigue_desc,
            world_day=world_day,
            source_type="player",
            source_id=fatigued.id,
            participants=[
                {"role": "player", "id": fatigued.id, "name": fatigued.name},
                {"role": "medical_director", "name": med_slot["name"], "status": med_slot["status"]},
            ],
            consequences=fatigue_consequences,
            actions=[
                {"key": "rest_player", "label": "Grant Recovery Rest", "style": "primary"},
                {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:med:fatigue:{fatigued.id}",
        )
        if created:
            new_events.append(evt)

    # 3. Academy & Youth Development Events
    promising_regens = [p for p in players if p.is_regen and p.rating >= 62]
    if promising_regens:
        top_regen = max(promising_regens, key=lambda p: p.rating)
        if hoyd_slot["is_appointed"]:
            acad_desc = (
                f"Academy graduate {top_regen.name} ({top_regen.position}, age {top_regen.age}) has reached "
                f"rating {top_regen.rating} (potential {top_regen.potential}). "
                f"Head of Youth Development {hoyd_slot['name']} reports high senior squad readiness."
            )
            hoyd_part = {
                "role": "head_of_youth_development",
                "id": hoyd_slot["person_id"],
                "name": hoyd_slot["name"],
                "status": "appointed",
            }
        else:
            acad_desc = (
                f"Academy graduate {top_regen.name} ({top_regen.position}, age {top_regen.age}) has reached "
                f"rating {top_regen.rating} (potential {top_regen.potential}). "
                f"Academy coaching staff report high senior squad readiness (Head of Youth Development vacant)."
            )
            hoyd_part = {
                "role": "head_of_youth_development",
                "name": hoyd_slot["name"],
                "status": "vacant",
            }

        evt, created = create_club_event(
            session,
            club_id,
            category="academy",
            event_type="regen_prospect_spotlight",
            severity="important",
            title=f"Academy Spotlight: {top_regen.name}",
            description=acad_desc,
            world_day=world_day,
            source_type="player",
            source_id=top_regen.id,
            participants=[
                {"role": "player", "id": top_regen.id, "name": top_regen.name},
                hoyd_part,
            ],
            consequences={
                "player_id": top_regen.id,
                "rating": top_regen.rating,
                "hoyd_status": hoyd_slot["status"],
            },
            actions=[
                {"key": "praise_prospect", "label": "Commend Player & Academy", "style": "primary"},
                {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:acad:spotlight:{top_regen.id}",
        )
        if created:
            new_events.append(evt)

    # Contract Milestone Alert (triggered only when authoritative contract data exists on player record)
    expiring_players = [
        p
        for p in players
        if "contract_months_remaining" in (p.personality_json or {})
        and 0 < int((p.personality_json or {}).get("contract_months_remaining", 12)) <= 6
    ]
    if expiring_players:
        target_p = max(expiring_players, key=lambda p: p.rating)
        months_rem = int((target_p.personality_json or {}).get("contract_months_remaining", 6))
        evt, created = create_club_event(
            session,
            club_id,
            category="executive",
            event_type="contract_expiry_warning",
            severity="important",
            title=f"Contract Milestone: {target_p.name} ({months_rem}m Remaining)",
            description=(
                f"{target_p.name} ({target_p.position}, OVR {target_p.rating}) has entered the final "
                f"{months_rem} months of their current club agreement."
            ),
            world_day=world_day,
            source_type="player",
            source_id=target_p.id,
            participants=[
                {"role": "player", "id": target_p.id, "name": target_p.name},
                {"role": "general_manager", "name": gm_slot["name"], "status": gm_slot["status"]},
            ],
            consequences={"player_id": target_p.id, "contract_months_remaining": months_rem},
            actions=[
                {"key": "open_renewal_talks", "label": "Open Renewal Discussions", "style": "primary"},
                {"key": "acknowledge", "label": "Acknowledge", "style": "ghost"},
            ],
            idempotency_key=f"evt:{club_id}:{world_day}:exec:contract:{target_p.id}",
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
                {"role": "first_team_manager", "name": mgr_slot["name"], "status": mgr_slot["status"]},
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
    if mgr_slot["is_appointed"] and mgr_slot["person_id"]:
        mgr_rel_key = pairing_key(club_id, "owner", mgr_slot["person_id"])
        mgr_rel = session.scalar(
            select(OwnerClubRelationship).where(
                OwnerClubRelationship.club_id == club_id,
                OwnerClubRelationship.pairing_key == mgr_rel_key,
                OwnerClubRelationship.status == "active",
            )
        )
        if mgr_rel and mgr_rel.tension >= 50:
            evt, created = create_club_event(
                session,
                club_id,
                category="tactical",
                event_type="managerial_tension_alert",
                severity="critical",
                title=f"Tactical Friction with {mgr_slot['name']}",
                description=(
                    f"Operational friction with manager {mgr_slot['name']} has escalated "
                    f"(Tension {mgr_rel.tension}/100, Trust {mgr_rel.trust}/100). Tactical office requests board alignment."
                ),
                world_day=world_day,
                source_type="staff",
                source_id=mgr_slot["person_id"],
                participants=[
                    {"role": "first_team_manager", "id": mgr_slot["person_id"], "name": mgr_slot["name"]},
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

    # 6. Evaluate Active Directives Using Authoritative Completion Verification
    active_directives = list(
        session.scalars(
            select(OwnerClubDirective).where(
                OwnerClubDirective.club_id == club_id,
                OwnerClubDirective.status == "active",
            )
        ).all()
    )
    for directive in active_directives:
        is_fulfilled, progress_pct, evidence = _evaluate_directive_completion(
            session, state, directive, roster, players
        )
        dir_consequences = dict(directive.consequences_json or {})
        dir_consequences["progress_pct"] = progress_pct
        dir_consequences["evidence"] = evidence
        dir_consequences["last_evaluated_world_day"] = world_day

        if is_fulfilled:
            lead_role = DEPARTMENT_TO_ROLE_KEY.get(directive.department, "general_manager")
            lead_slot = roster.get(lead_role)
            directive.status = "completed"
            directive.completed_at = utcnow()
            dir_consequences["verification_status"] = "verified_completed"
            dir_consequences["verified_at_world_day"] = world_day

            if (
                not dir_consequences.get("reward_granted")
                and lead_slot
                and lead_slot["is_appointed"]
                and lead_slot["person_id"]
            ):
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    lead_slot["person_id"],
                    lead_slot["name"],
                    delta_trust=6,
                    delta_respect=5,
                    delta_tension=-4,
                    reason=f"Directive '{directive.title}' fulfilled with verified completion evidence.",
                    world_day=world_day,
                )
                dir_consequences["reward_granted"] = True

            directive.consequences_json = dir_consequences
            flag_modified(directive, "consequences_json")
            directive.updated_at = utcnow()

            evt, created = create_club_event(
                session,
                club_id,
                category="executive",
                event_type="directive_completed",
                severity="routine",
                title=f"Directive Completed: {directive.title}",
                description=(
                    f"Department {directive.department} fulfilled Chairman's directive '{directive.instruction}' "
                    f"(verified: {', '.join(evidence.get('matched_checks') or [])})."
                ),
                world_day=world_day,
                source_type="directive",
                source_id=directive.id,
                consequences={
                    "directive_id": directive.id,
                    "status": "completed",
                    "evidence": evidence,
                },
                actions=[{"key": "acknowledge", "label": "Acknowledge", "style": "ghost"}],
                idempotency_key=f"evt:{club_id}:dir_done:{directive.id}",
            )
            if created:
                new_events.append(evt)

        elif directive.deadline_day is not None and world_day >= directive.deadline_day:
            directive.status = "expired"
            dir_consequences["verification_status"] = "expired_unfulfilled"
            dir_consequences["expired_at_world_day"] = world_day
            dir_consequences["reward_granted"] = False
            directive.consequences_json = dir_consequences
            flag_modified(directive, "consequences_json")
            directive.updated_at = utcnow()

            evt, created = create_club_event(
                session,
                club_id,
                category="executive",
                event_type="directive_expired",
                severity="important",
                title=f"Directive Expired Unfulfilled: {directive.title}",
                description=(
                    f"Directive '{directive.title}' assigned to {directive.department} reached its World Day "
                    f"{directive.deadline_day} deadline without verified completion evidence "
                    f"({evidence.get('reason', 'unverified')})."
                ),
                world_day=world_day,
                source_type="directive",
                source_id=directive.id,
                consequences={
                    "directive_id": directive.id,
                    "status": "expired",
                    "evidence": evidence,
                },
                actions=[{"key": "acknowledge", "label": "Acknowledge", "style": "ghost"}],
                idempotency_key=f"evt:{club_id}:dir_expired:{directive.id}",
            )
            if created:
                new_events.append(evt)
        else:
            directive.consequences_json = dir_consequences
            flag_modified(directive, "consequences_json")
            directive.updated_at = utcnow()

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
    state = service.require_state(session, club_id, user_id)

    # Acquire a transaction-safe row lock on the event record and force fresh state from DB
    event = session.scalar(
        select(OwnerClubEvent)
        .where(
            OwnerClubEvent.id == event_id,
            OwnerClubEvent.club_id == club_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if event is None:
        raise service.OwnerError("event_not_found", 404, "Event not found or does not belong to this club.")

    if event.status not in ("active", "awaiting_decision"):
        raise service.OwnerError(
            "event_already_resolved",
            409,
            f"Event cannot be resolved; status is '{event.status}'.",
        )

    clean_action = str(action or "").strip()
    declared_actions = {
        str(item.get("key")).strip(): item
        for item in (event.actions_json or [])
        if isinstance(item, dict) and str(item.get("key") or "").strip()
    }
    if not clean_action or clean_action not in declared_actions:
        raise service.OwnerError(
            "invalid_event_action",
            400,
            f"Action '{action}' is not valid for event '{event.event_type}'. Allowed actions: {sorted(declared_actions.keys())}.",
        )

    supported_for_type = ALLOWED_ACTIONS_BY_EVENT_TYPE.get(event.event_type, set())
    if clean_action not in supported_for_type:
        raise service.OwnerError(
            "unsupported_event_action",
            400,
            f"Action '{clean_action}' is not supported by backend handler for event type '{event.event_type}'.",
        )

    # Atomic conditional state transition to claim the event within this transaction
    claim_result = session.execute(
        update(OwnerClubEvent)
        .where(
            OwnerClubEvent.id == event_id,
            OwnerClubEvent.club_id == club_id,
            OwnerClubEvent.status.in_(["active", "awaiting_decision"]),
        )
        .values(status="resolving", updated_at=utcnow())
    )
    if int(claim_result.rowcount or 0) != 1:
        raise service.OwnerError(
            "event_already_resolved",
            409,
            "Event cannot be resolved; it was already claimed or resolved by a concurrent request.",
        )

    world_day = int(state.world_day or 1)
    roster = resolve_club_staff_roster(state)
    mgr_slot = roster["first_team_manager"]
    gm_slot = roster["general_manager"]
    hoyd_slot = roster["head_of_youth_development"]
    med_slot = roster["medical_director"]

    consequences_applied: dict[str, Any] = {"action_executed": clean_action}

    if clean_action == "acknowledge":
        consequences_applied["acknowledged"] = True
        consequences_applied["acknowledged_world_day"] = world_day

    elif event.event_type == "managerial_tension_alert":
        if clean_action == "back_manager":
            if mgr_slot["is_appointed"] and mgr_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    mgr_slot["person_id"],
                    mgr_slot["name"],
                    delta_trust=10,
                    delta_respect=8,
                    delta_tension=-18,
                    reason="Owner publicly reaffirmed full board backing for manager.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
            if isinstance(state.manager_json, dict) and state.manager_json:
                mgr_dict = dict(state.manager_json)
                mgr_dict["mood"] = int(engine.clamp(int(mgr_dict.get("mood", 70)) + 15, 0, 100))
                state.manager_json = mgr_dict
                flag_modified(state, "manager_json")
            consequences_applied["manager_mood_delta"] = 15
            consequences_applied["tension_delta"] = -18
        elif clean_action == "demand_results":
            if mgr_slot["is_appointed"] and mgr_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    mgr_slot["person_id"],
                    mgr_slot["name"],
                    delta_trust=-6,
                    delta_respect=4,
                    delta_tension=12,
                    reason="Owner issued formal ultimatum demanding immediate tactical improvements.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
            if isinstance(state.manager_json, dict) and state.manager_json:
                mgr_dict = dict(state.manager_json)
                mgr_dict["mood"] = int(engine.clamp(int(mgr_dict.get("mood", 70)) - 10, 0, 100))
                state.manager_json = mgr_dict
                flag_modified(state, "manager_json")
            consequences_applied["manager_mood_delta"] = -10
            consequences_applied["tension_delta"] = 12

    elif event.event_type in ("squad_morale_dip", "player_discontent"):
        player_id = (event.consequences_json or {}).get("player_id") or event.source_id
        player = session.get(OwnerSquadPlayer, player_id) if player_id else None
        if player and player.club_id == club_id:
            if clean_action == "encourage_player":
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
            elif clean_action == "ignore":
                player.morale = engine.clamp(player.morale - 5, 0, 100)
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
                    delta_trust=-4,
                    delta_tension=6,
                    reason="Owner declined morale intervention request.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
                consequences_applied["player_morale"] = player.morale

    elif event.event_type == "player_recovery_cleared":
        if clean_action == "praise_medical":
            player_id = (event.consequences_json or {}).get("player_id") or event.source_id
            player = session.get(OwnerSquadPlayer, player_id) if player_id else None
            if player and player.club_id == club_id:
                player.morale = engine.clamp(player.morale + 4, 0, 100)
                flag_modified(player, "morale")
                consequences_applied["player_morale"] = player.morale
            if med_slot["is_appointed"] and med_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    med_slot["person_id"],
                    med_slot["name"],
                    delta_trust=8,
                    delta_respect=8,
                    delta_affinity=6,
                    delta_tension=-5,
                    reason="Owner commended medical team for timely player recovery clearance.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
                consequences_applied["medical_trust_delta"] = 8
            else:
                consequences_applied["medical_trust_delta"] = 0
            consequences_applied["medical_director_status"] = med_slot["status"]

    elif event.event_type == "injury_crisis_alert":
        if clean_action == "reduce_workload":
            facs = dict(state.facilities_json or {})
            facs["_training_intensity"] = "light_recovery"
            state.facilities_json = facs
            flag_modified(state, "facilities_json")
            active_players = list(
                session.scalars(
                    select(OwnerSquadPlayer).where(
                        OwnerSquadPlayer.club_id == club_id,
                        OwnerSquadPlayer.status == "active",
                        OwnerSquadPlayer.injured_days == 0,
                    )
                ).all()
            )
            for p in active_players:
                pers = dict(p.personality_json or {})
                pers["last_training_workload_tier"] = "light"
                pers["fitness"] = int(engine.clamp(int(pers.get("fitness", 90)) + 4, 0, 100))
                p.personality_json = pers
                flag_modified(p, "personality_json")
            if med_slot["is_appointed"] and med_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    med_slot["person_id"],
                    med_slot["name"],
                    delta_trust=7,
                    delta_respect=6,
                    delta_tension=-8,
                    reason="Owner reduced first-team training intensity on medical advice.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
            consequences_applied["training_intensity"] = "light_recovery"
            consequences_applied["players_adjusted_count"] = len(active_players)
            consequences_applied["medical_director_status"] = med_slot["status"]

    elif event.event_type == "regen_prospect_spotlight":
        if clean_action == "praise_prospect":
            player_id = (event.consequences_json or {}).get("player_id") or event.source_id
            player = session.get(OwnerSquadPlayer, player_id) if player_id else None
            if player and player.club_id == club_id:
                player.morale = engine.clamp(player.morale + 6, 0, 100)
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
                    delta_trust=8,
                    delta_affinity=8,
                    reason="Owner publicly praised academy prospect breakthrough.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
                consequences_applied["player_morale"] = player.morale
            if hoyd_slot["is_appointed"] and hoyd_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    hoyd_slot["person_id"],
                    hoyd_slot["name"],
                    delta_trust=8,
                    delta_respect=8,
                    delta_affinity=8,
                    reason="Owner recognized academy breakthrough prospect.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
                consequences_applied["hoyd_trust_delta"] = 8
            else:
                consequences_applied["hoyd_trust_delta"] = 0
            consequences_applied["hoyd_status"] = hoyd_slot["status"]

    elif event.event_type == "treasury_low_reserves":
        if clean_action == "review_sponsors":
            facs = dict(state.facilities_json or {})
            facs["_treasury_sponsor_review_day"] = world_day
            state.facilities_json = facs
            flag_modified(state, "facilities_json")
            if gm_slot["is_appointed"] and gm_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    gm_slot["person_id"],
                    gm_slot["name"],
                    delta_trust=4,
                    delta_respect=3,
                    delta_tension=-3,
                    reason="Owner initiated commercial sponsor review following treasury alert.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
            consequences_applied["sponsor_review_flagged_day"] = world_day
            consequences_applied["gm_status"] = gm_slot["status"]

    elif event.event_type in ("contract_expiry_warning", "scholar_contract_milestone"):
        if clean_action == "open_renewal_talks":
            player_id = (event.consequences_json or {}).get("player_id") or event.source_id
            player = session.get(OwnerSquadPlayer, player_id) if player_id else None
            if player and player.club_id == club_id:
                player.morale = engine.clamp(player.morale + 8, 0, 100)
                pers = dict(player.personality_json or {})
                pers["contract_renewal_talks_opened_day"] = world_day
                player.personality_json = pers
                flag_modified(player, "morale")
                flag_modified(player, "personality_json")
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "player",
                    player.id,
                    player.name,
                    delta_trust=10,
                    delta_respect=6,
                    delta_tension=-8,
                    reason="Owner opened contract renewal discussions with player.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
                consequences_applied["player_morale"] = player.morale
            consequences_applied["renewal_talks_opened_day"] = world_day

    elif event.event_type == "high_fatigue_workload_alert":
        if clean_action == "rest_player":
            player_id = (event.consequences_json or {}).get("player_id") or event.source_id
            player = session.get(OwnerSquadPlayer, player_id) if player_id else None
            if player and player.club_id == club_id:
                pers = dict(player.personality_json or {})
                new_fit = int(engine.clamp(int(pers.get("fitness", 70)) + 12, 0, 100))
                pers["fitness"] = new_fit
                pers["last_training_workload_tier"] = "rest_recovery"
                if "fatigue" in pers:
                    pers["fatigue"] = max(0, int(pers["fatigue"]) - 20)
                    consequences_applied["fatigue"] = pers["fatigue"]
                player.personality_json = pers
                player.morale = engine.clamp(player.morale + 4, 0, 100)
                flag_modified(player, "personality_json")
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
                    delta_trust=6,
                    delta_affinity=5,
                    delta_tension=-5,
                    reason="Owner authorized recovery rest session.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
                consequences_applied["fitness"] = new_fit
                consequences_applied["player_morale"] = player.morale

    elif event.event_type == "tactical_readiness_briefing":
        if clean_action == "endorse_tactics":
            if mgr_slot["is_appointed"] and mgr_slot["person_id"]:
                apply_relationship_delta(
                    session,
                    club_id,
                    "owner",
                    "owner",
                    "Club Owner",
                    "staff",
                    mgr_slot["person_id"],
                    mgr_slot["name"],
                    delta_trust=5,
                    delta_respect=4,
                    delta_tension=-4,
                    reason="Owner endorsed tactical preparation plan.",
                    source_event_id=event.id,
                    world_day=world_day,
                )
            consequences_applied["tactics_endorsed"] = True

    event.status = "resolved"
    event.resolution_action = clean_action
    event.resolution_note = resolution_note or f"Action '{clean_action}' executed by Chairman."
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
    """Returns a unified, chronological Living Club World timeline aggregating authoritative events, directives, and relationship shifts.

    Enforces club ownership authorization via `service.require_state(session, club_id, user_id)`
    and applies `category`, `severity`, `status`, `offset`, and `limit` consistently across the unified timeline.
    `total_count` (and `total_events_count`) equals the total number of unified timeline items matching the active filters.
    """
    service.require_state(session, club_id, user_id)

    safe_limit = max(1, min(int(limit or 50), 200))
    safe_offset = max(0, int(offset or 0))

    events = list(
        session.scalars(
            select(OwnerClubEvent)
            .where(OwnerClubEvent.club_id == club_id)
            .order_by(OwnerClubEvent.world_day.desc(), OwnerClubEvent.created_at.desc())
        ).all()
    )

    directives = list(
        session.scalars(
            select(OwnerClubDirective)
            .where(OwnerClubDirective.club_id == club_id)
            .order_by(OwnerClubDirective.issued_day.desc(), OwnerClubDirective.created_at.desc())
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
        ).all()
    )

    unified_items: list[dict[str, Any]] = []

    for ev in events:
        unified_items.append(
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
        unified_items.append(
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
        unified_items.append(
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

    filtered_items = [
        item
        for item in unified_items
        if (not category or item["category"] == category)
        and (not severity or item["severity"] == severity)
        and (not status or item["status"] == status)
    ]

    filtered_items.sort(
        key=lambda item: (
            int(item.get("world_day") or 0),
            str(item.get("created_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )

    total_count = len(filtered_items)
    paginated_items = filtered_items[safe_offset : safe_offset + safe_limit]

    return {
        "club_id": club_id,
        "total_count": total_count,
        "total_events_count": total_count,
        "counts_by_kind": {
            "event": sum(1 for item in filtered_items if item["kind"] == "event"),
            "directive": sum(1 for item in filtered_items if item["kind"] == "directive"),
            "relationship_shift": sum(1 for item in filtered_items if item["kind"] == "relationship_shift"),
        },
        "limit": safe_limit,
        "offset": safe_offset,
        "items": paginated_items,
    }
