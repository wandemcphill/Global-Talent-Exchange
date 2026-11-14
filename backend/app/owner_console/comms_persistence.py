from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.club_profile import ClubProfile
from app.models.user import User
from app.owner_console import engine, ledger
from app.owner_console.models import (
    OwnerClubAnnouncement,
    OwnerClubConversation,
    OwnerClubMeeting,
    OwnerClubMessage,
    OwnerClubState,
    OwnerInboxItem,
    OwnerScoutingWatchlist,
    OwnerSquadPlayer,
)
from app.owner_console.service import OwnerError, require_state

STAFF_DIRECTORY: tuple[dict[str, str], ...] = (
    {
        "id": "staff:first_team_manager",
        "role_key": "first_team_manager",
        "name": "First-Team Head Coach",
        "role": "First-Team Manager",
        "department": "First-Team Technical",
        "portrait_url": "/console/img/prestige/10_vip_matchday_lounge.png",
        "route": "/app/lineup",
    },
    {
        "id": "staff:general_manager",
        "role_key": "general_manager",
        "name": "Dayo Adeleke",
        "role": "General Manager",
        "department": "Executive Boardroom",
        "portrait_url": "/console/img/prestige/09_owner_office_executive.png",
        "route": "/app/finance",
    },
    {
        "id": "staff:head_of_youth_development",
        "role_key": "head_of_youth_development",
        "name": "Femi Ogunleye",
        "role": "Head of Youth Development",
        "department": "Academy & Regens",
        "portrait_url": "/console/img/prestige/12_elite_academy_complex.png",
        "route": "/app/academy",
    },
    {
        "id": "staff:chief_scout",
        "role_key": "chief_scout",
        "name": "Kelechi Nwosu",
        "role": "Chief Scout",
        "department": "Recruitment & Scouting",
        "portrait_url": "/console/img/prestige/06_academy_campus_aerial_a.png",
        "route": "/app/transfer-hub",
    },
    {
        "id": "staff:medical_director",
        "role_key": "medical_director",
        "name": "Dr. Amara Okafor",
        "role": "Medical Director",
        "department": "Sports Science & Medical",
        "portrait_url": "/console/img/prestige/11_stadium_expansion_construction.png",
        "route": "/app/squad",
    },
)

STAFF_ALIASES: dict[str, dict[str, str]] = {}
for _member in STAFF_DIRECTORY:
    for _k in (
        _member["id"].lower(),
        _member["role_key"].lower(),
        _member["role"].lower(),
        _member["name"].lower(),
        _member["id"].replace("staff:", "").replace("_", " ").lower(),
    ):
        STAFF_ALIASES[_k] = _member
STAFF_ALIASES["staff:gm"] = STAFF_DIRECTORY[1]
STAFF_ALIASES["staff:manager"] = STAFF_DIRECTORY[0]
STAFF_ALIASES["staff:hoyd"] = STAFF_DIRECTORY[2]
STAFF_ALIASES["staff:scout"] = STAFF_DIRECTORY[3]
STAFF_ALIASES["staff:medical"] = STAFF_DIRECTORY[4]


def _treasury_gtex(session: Session, club_id: str) -> float:
    try:
        return float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX))
    except Exception:
        return 0.0


def _parse_iso_dt(raw: Any, fallback: datetime | None = None) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return fallback or datetime.now(timezone.utc)


def _deterministic_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(f"{prefix}:{seed}".encode("utf-8")).hexdigest()[:32]
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def _publish_owner_comms_realtime(club_id: str, event_type: str, payload: dict[str, Any]) -> None:
    try:
        from app.realtime.service import RealtimeDispatch, get_global_realtime_hub

        hub = get_global_realtime_hub()
        if hub is None:
            return
        hub.publish_direct_sync(
            RealtimeDispatch(
                type=event_type,
                topics=(f"owner_comms:club:{club_id}",),
                data={"club_id": club_id, **payload},
            )
        )
    except Exception:
        return


def _get_or_create_conversation(
    session: Session,
    *,
    club_id: str,
    owner_user_id: str,
    channel_type: str,
    thread_key: str,
    participant_type: str,
    participant_id: str | None,
    participant_name: str,
    participant_role: str,
    subject: str | None = None,
) -> OwnerClubConversation:
    conv = session.scalar(
        select(OwnerClubConversation).where(
            OwnerClubConversation.club_id == club_id,
            OwnerClubConversation.thread_key == thread_key,
        )
    )
    if conv is None:
        conv = OwnerClubConversation(
            club_id=club_id,
            owner_user_id=owner_user_id,
            channel_type=channel_type,
            thread_key=thread_key,
            participant_type=participant_type,
            participant_id=participant_id,
            participant_name=participant_name,
            participant_role=participant_role,
            subject=subject,
            last_message_seq=0,
        )
        session.add(conv)
        session.flush()
    return conv


def _append_message(
    session: Session,
    *,
    conv: OwnerClubConversation,
    sender_user_id: str | None,
    sender_type: str,
    sender_id: str | None,
    sender_name: str,
    sender_role: str,
    topic: str | None,
    body: str,
    source: str,
    priority: str = "normal",
    linked_entity_type: str | None = None,
    linked_entity_id: str | None = None,
    linked_event_key: str | None = None,
    action_payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    is_read: bool = False,
    created_at: datetime | None = None,
) -> OwnerClubMessage:
    if linked_event_key:
        existing = session.scalar(
            select(OwnerClubMessage).where(
                OwnerClubMessage.club_id == conv.club_id,
                OwnerClubMessage.linked_event_key == linked_event_key,
            )
        )
        if existing is not None:
            return existing

    max_seq = int(
        session.scalar(
            select(func.coalesce(func.max(OwnerClubMessage.seq), 0)).where(
                OwnerClubMessage.conversation_id == conv.id
            )
        )
        or 0
    )
    next_seq = max(int(conv.last_message_seq or 0), max_seq) + 1
    now = created_at or datetime.now(timezone.utc)
    msg = OwnerClubMessage(
        id=_deterministic_id("ocm", f"{conv.id}:{next_seq}:{secrets.token_hex(4)}"),
        conversation_id=conv.id,
        club_id=conv.club_id,
        seq=next_seq,
        sender_user_id=sender_user_id,
        sender_type=sender_type,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_role=sender_role,
        topic=topic,
        body=body,
        source=source,
        priority=priority,
        linked_entity_type=linked_entity_type,
        linked_entity_id=linked_entity_id,
        linked_event_key=linked_event_key,
        action_payload_json=dict(action_payload or {}),
        metadata_json=dict(metadata or {}),
        is_read=is_read,
        read_at=now if is_read else None,
        created_at=now,
    )
    session.add(msg)
    conv.last_message_seq = next_seq
    conv.last_message_at = now
    conv.updated_at = now
    session.flush()
    return msg


def backfill_legacy_club_communications(session: Session, state: OwnerClubState) -> int:
    """Idempotently migrate legacy facilities_json communications into durable SQL tables."""
    facs = dict(state.facilities_json or {})
    legacy_threads = facs.get("_club_threads")
    legacy_staff = list(facs.get("_staff_room_feed") or [])
    legacy_squad = list(facs.get("_squad_room_feed") or [])
    legacy_meetings = list(facs.get("_club_meetings") or [])
    legacy_announcements = list(facs.get("_club_announcements") or [])

    thread_items: list[dict[str, Any]] = []
    if isinstance(legacy_threads, dict):
        thread_items = list(legacy_threads.values())
    elif isinstance(legacy_threads, list):
        thread_items = list(legacy_threads)

    if not any((thread_items, legacy_staff, legacy_squad, legacy_meetings, legacy_announcements)):
        return 0

    migrated = 0
    staff_conv = _get_or_create_conversation(
        session,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        channel_type="staff_room",
        thread_key="room:staff",
        participant_type="room",
        participant_id="room:staff",
        participant_name="Staff Technical Room",
        participant_role="Executive & Technical Staff",
        subject="Technical, Medical, Academy & Recruitment Briefing",
    )
    squad_conv = _get_or_create_conversation(
        session,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        channel_type="squad_room",
        thread_key="room:squad",
        participant_type="room",
        participant_id="room:squad",
        participant_name="Dressing Room",
        participant_role="First-Team & Academy Squad",
        subject="Squad Morale, Matchday Preparation & Dressing Room",
    )

    for idx, th in enumerate(thread_items):
        if not isinstance(th, dict):
            continue
        p_id = str(th.get("participant_id") or th.get("thread_id") or f"legacy_{idx}")
        p_type = str(th.get("participant_type") or "staff")
        p_role = str(th.get("participant_role") or "First-Team Manager")
        p_name = str(th.get("participant_name") or p_role)
        t_key = str(th.get("thread_id") or f"direct:{p_type}:{p_id}")
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key=t_key,
            participant_type=p_type,
            participant_id=p_id,
            participant_name=p_name,
            participant_role=p_role,
            subject=f"Direct with {p_name}",
        )
        for m_idx, raw_m in enumerate(list(th.get("messages") or [])):
            if not isinstance(raw_m, dict):
                continue
            legacy_mid = str(raw_m.get("id") or f"{t_key}:{m_idx}")
            body = str(raw_m.get("body") or "").strip()
            if not body:
                continue
            s_role = str(raw_m.get("sender_role") or p_role)
            is_owner_msg = s_role.lower() in {"owner", "club owner"}
            _append_message(
                session,
                conv=conv,
                sender_user_id=state.owner_user_id if is_owner_msg else None,
                sender_type="owner" if is_owner_msg else p_type,
                sender_id=None if is_owner_msg else p_id,
                sender_name=str(raw_m.get("sender_name") or ("Club Owner" if is_owner_msg else p_name)),
                sender_role=s_role,
                topic=raw_m.get("topic"),
                body=body,
                source="owner" if is_owner_msg else ("player_reply" if p_type == "player" else "staff_reply"),
                linked_event_key=f"legacy:direct:{state.club_id}:{legacy_mid}",
                metadata={"legacy_id": legacy_mid, "migrated_from_json": True},
                is_read=is_owner_msg,
                created_at=_parse_iso_dt(raw_m.get("created_at")),
            )
            migrated += 1

    for conv_target, legacy_feed, room_tag in (
        (staff_conv, legacy_staff, "staff_room"),
        (squad_conv, legacy_squad, "squad_room"),
    ):
        for r_idx, raw_m in enumerate(reversed(legacy_feed)):
            if not isinstance(raw_m, dict):
                continue
            legacy_mid = str(raw_m.get("id") or f"{room_tag}:{r_idx}")
            body = str(raw_m.get("body") or "").strip()
            if not body:
                continue
            s_role = str(raw_m.get("sender_role") or "Club Staff")
            is_owner_msg = s_role.lower() in {"owner", "club owner"}
            _append_message(
                session,
                conv=conv_target,
                sender_user_id=state.owner_user_id if is_owner_msg else None,
                sender_type="owner" if is_owner_msg else ("player" if room_tag == "squad_room" else "staff"),
                sender_id=None,
                sender_name=str(raw_m.get("sender_name") or s_role),
                sender_role=s_role,
                topic=raw_m.get("tag") or raw_m.get("topic"),
                body=body,
                source="owner" if is_owner_msg else ("player_reply" if room_tag == "squad_room" else "staff_reply"),
                linked_event_key=f"legacy:{room_tag}:{state.club_id}:{legacy_mid}",
                metadata={"legacy_id": legacy_mid, "migrated_from_json": True},
                is_read=True,
                created_at=_parse_iso_dt(raw_m.get("created_at")),
            )
            migrated += 1

    for m_idx, raw_mtg in enumerate(reversed(legacy_meetings)):
        if not isinstance(raw_mtg, dict):
            continue
        legacy_id = str(raw_mtg.get("meeting_id") or raw_mtg.get("id") or f"mtg_{m_idx}")
        det_id = _deterministic_id("mtg", f"{state.club_id}:{legacy_id}")
        if session.get(OwnerClubMeeting, det_id) is None:
            raw_minutes = raw_mtg.get("minutes")
            minutes_list = list(raw_minutes) if isinstance(raw_minutes, list) else []
            raw_summary = raw_mtg.get("outcome_summary") or raw_mtg.get("minutes_summary") or (
                raw_minutes if isinstance(raw_minutes, str) else ""
            )
            session.add(
                OwnerClubMeeting(
                    id=det_id,
                    club_id=state.club_id,
                    owner_user_id=state.owner_user_id,
                    title=str(raw_mtg.get("title") or "Executive Club Briefing"),
                    agenda=str(raw_mtg.get("agenda") or ""),
                    meeting_type=str(raw_mtg.get("meeting_type") or "boardroom"),
                    world_day=raw_mtg.get("world_day") or state.world_day,
                    status=str(raw_mtg.get("status") or "scheduled"),
                    attendees_json=list(raw_mtg.get("participants") or raw_mtg.get("attendees") or []),
                    minutes_summary=str(raw_summary or ""),
                    decisions_json=list(raw_mtg.get("decisions") or []),
                    created_by_user_id=state.owner_user_id,
                    metadata_json={
                        "legacy_id": legacy_id,
                        "migrated_from_json": True,
                        "minutes": minutes_list,
                        "morale_boost_applied": bool(raw_mtg.get("morale_boost_applied")),
                    },
                    created_at=_parse_iso_dt(raw_mtg.get("created_at")),
                    updated_at=_parse_iso_dt(raw_mtg.get("created_at")),
                )
            )
            migrated += 1

    for a_idx, raw_ann in enumerate(reversed(legacy_announcements)):
        if not isinstance(raw_ann, dict):
            continue
        legacy_id = str(raw_ann.get("announcement_id") or raw_ann.get("id") or f"ann_{a_idx}")
        det_id = _deterministic_id("ann", f"{state.club_id}:{legacy_id}")
        if session.get(OwnerClubAnnouncement, det_id) is None:
            session.add(
                OwnerClubAnnouncement(
                    id=det_id,
                    club_id=state.club_id,
                    owner_user_id=state.owner_user_id,
                    title=str(raw_ann.get("title") or "Club Announcement"),
                    body=str(raw_ann.get("body") or ""),
                    audience=str(raw_ann.get("audience") or "all_club"),
                    priority=str(raw_ann.get("priority") or "normal"),
                    published_world_day=raw_ann.get("world_day") or raw_ann.get("published_world_day") or state.world_day,
                    published_by_user_id=state.owner_user_id,
                    metadata_json={"legacy_id": legacy_id, "migrated_from_json": True},
                    created_at=_parse_iso_dt(raw_ann.get("created_at")),
                    updated_at=_parse_iso_dt(raw_ann.get("created_at")),
                )
            )
            migrated += 1

    session.flush()
    return migrated


def _staff_seed_message(
    *,
    role_key: str,
    club_name: str,
    prestige: int,
    treasury: int,
    squad_count: int,
    regen_count: int,
    injured_count: int,
    world_day: int,
) -> tuple[str, str, dict[str, Any]]:
    if role_key == "first_team_manager":
        return (
            "Matchday Preparation",
            f"Tactical desk for {club_name} is monitoring {squad_count} registered players ahead of World Day {world_day} competition fixtures.",
            {"action_type": "open_route", "route": "/app/lineup", "label": "Inspect Lineup"},
        )
    if role_key == "general_manager":
        return (
            "Club Budget & Operations",
            f"Executive report for {club_name}: treasury stands at {treasury} GTX with Prestige {prestige}. Ready for boardroom directives.",
            {"action_type": "open_route", "route": "/app/finance", "label": "Open Finance"},
        )
    if role_key == "head_of_youth_development":
        return (
            "Academy & Regen Pipeline",
            f"Academy development tracks {regen_count} regen prospects at {club_name}. Ready to coordinate senior training pathways.",
            {"action_type": "open_route", "route": "/app/academy", "label": "Open Academy"},
        )
    if role_key == "chief_scout":
        return (
            "Scouting & Transfer Desk",
            f"Recruitment cell has indexed the {squad_count}-player squad profile and {treasury} GTX capacity for upcoming market windows.",
            {"action_type": "open_route", "route": "/app/transfer-hub", "label": "Open Transfers"},
        )
    return (
        "Medical & Workload Report",
        f"Sports science unit reports {injured_count} active injury case(s) across {squad_count} squad players on World Day {world_day}.",
        {"action_type": "open_route", "route": "/app/squad", "label": "Open Squad"},
    )


def ensure_club_conversations_seeded(session: Session, state: OwnerClubState) -> None:
    backfill_legacy_club_communications(session, state)

    squad = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))
    treasury = int(_treasury_gtex(session, state.club_id))
    world_day = int(state.world_day or 1)
    regen_count = sum(1 for p in squad if p.is_regen)
    injured_count = sum(1 for p in squad if int(p.injured_days or 0) > 0)

    for member in STAFF_DIRECTORY:
        rk = member["role_key"]
        resolved_name = (
            mgr.get("name", member["name"])
            if rk == "first_team_manager"
            else (exec_staff.get(rk) or {}).get("name", member["name"])
        )
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key=member["id"],
            participant_type="staff",
            participant_id=member["id"],
            participant_name=resolved_name,
            participant_role=member["role"],
            subject=f"{member['department']} · {resolved_name}",
        )
        if conv.last_message_seq == 0:
            topic, body, action_payload = _staff_seed_message(
                role_key=rk,
                club_name=state.club_name,
                prestige=int(state.prestige or 0),
                treasury=treasury,
                squad_count=len(squad),
                regen_count=regen_count,
                injured_count=injured_count,
                world_day=world_day,
            )
            _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="staff",
                sender_id=member["id"],
                sender_name=resolved_name,
                sender_role=member["role"],
                topic=topic,
                body=body,
                source="staff_event",
                linked_event_key=f"seed:direct:{member['id']}:{state.club_id}",
                action_payload=action_payload,
                is_read=False,
            )

    staff_conv = _get_or_create_conversation(
        session,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        channel_type="staff_room",
        thread_key="room:staff",
        participant_type="room",
        participant_id="room:staff",
        participant_name="Staff Technical Room",
        participant_role="Executive & Technical Staff",
        subject="Technical, Medical, Academy & Recruitment Briefing",
    )
    squad_conv = _get_or_create_conversation(
        session,
        club_id=state.club_id,
        owner_user_id=state.owner_user_id,
        channel_type="squad_room",
        thread_key="room:squad",
        participant_type="room",
        participant_id="room:squad",
        participant_name="Dressing Room",
        participant_role="First-Team & Academy Squad",
        subject="Squad Morale, Matchday Preparation & Dressing Room",
    )
    if staff_conv.last_message_seq == 0:
        gm_name = (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke")
        mgr_name = mgr.get("name", "First-Team Head Coach")
        _append_message(
            session,
            conv=staff_conv,
            sender_user_id=None,
            sender_type="staff",
            sender_id="staff:general_manager",
            sender_name=gm_name,
            sender_role="General Manager",
            topic="Boardroom Alignment",
            body=f"Staff technical desk is live for {state.club_name}. Treasury stands at {treasury} GTX on World Day {world_day}.",
            source="staff_event",
            linked_event_key=f"seed:staff_room:1:{state.club_id}",
            action_payload={"action_type": "open_route", "route": "/app/finance", "label": "Open Finance"},
            is_read=False,
        )
        _append_message(
            session,
            conv=staff_conv,
            sender_user_id=None,
            sender_type="staff",
            sender_id="staff:first_team_manager",
            sender_name=mgr_name,
            sender_role="First-Team Manager",
            topic="Tactical Readiness",
            body=f"Technical staff confirms {len(squad)} players on pitch schedule ({regen_count} academy prospects tracked).",
            source="staff_event",
            linked_event_key=f"seed:staff_room:2:{state.club_id}",
            action_payload={"action_type": "open_route", "route": "/app/lineup", "label": "Check Lineup"},
            is_read=False,
        )
    if squad_conv.last_message_seq == 0:
        captain_name = squad[0].name if squad else "First-Team Captain"
        _append_message(
            session,
            conv=squad_conv,
            sender_user_id=None,
            sender_type="player",
            sender_id="squad:captain",
            sender_name=captain_name,
            sender_role="Squad Captain",
            topic="Training Intensity",
            body=f"Squad dressing room is active for {state.club_name}. Focus is locked ahead of upcoming fixtures.",
            source="player_event",
            linked_event_key=f"seed:squad_room:1:{state.club_id}",
            action_payload={"action_type": "open_route", "route": "/app/squad", "label": "Inspect Squad"},
            is_read=False,
        )
        _append_message(
            session,
            conv=squad_conv,
            sender_user_id=None,
            sender_type="player",
            sender_id="squad:vice_captain",
            sender_name=squad[1].name if len(squad) > 1 else "Squad Vice-Captain",
            sender_role="Dressing Room Leadership",
            topic="Fixture Focus",
            body=f"Training group ({len(squad)} players) completed conditioning on campus ahead of World Day {world_day}.",
            source="player_event",
            linked_event_key=f"seed:squad_room:2:{state.club_id}",
            action_payload={"action_type": "open_route", "route": "/app/campus", "label": "Open Campus"},
            is_read=False,
        )

    existing_mtg_count = int(
        session.scalar(select(func.count(OwnerClubMeeting.id)).where(OwnerClubMeeting.club_id == state.club_id)) or 0
    )
    if existing_mtg_count == 0:
        gm_name = (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke")
        mgr_name = mgr.get("name", "First-Team Head Coach")
        hoyd_name = (exec_staff.get("head_of_youth_development") or {}).get("name", "Femi Ogunleye")
        seed_minutes = [
            {
                "speaker": gm_name,
                "role": "General Manager",
                "summary": f"Validated {state.club_name} treasury ({treasury} GTX) and operational targets.",
            },
            {
                "speaker": mgr_name,
                "role": "First-Team Manager",
                "summary": f"Outlined tactical rotation across {len(squad)} squad players.",
            },
            {
                "speaker": hoyd_name,
                "role": "Head of Youth Development",
                "summary": f"Reviewed progression pathways for {regen_count} academy prospects.",
            },
        ]
        session.add(
            OwnerClubMeeting(
                id=_deterministic_id("mtg_seed", f"{state.club_id}:1"),
                club_id=state.club_id,
                owner_user_id=state.owner_user_id,
                title="Executive Pre-Matchday Operations Briefing",
                agenda="Align first-team readiness, financial headroom, and academy progression.",
                meeting_type="boardroom",
                world_day=world_day,
                status="completed",
                attendees_json=["Club Owner", gm_name, mgr_name, hoyd_name],
                minutes_summary=f"Completed executive briefing at {state.club_name} ({treasury} GTX treasury, {len(squad)} players).",
                decisions_json=[],
                created_by_user_id=state.owner_user_id,
                metadata_json={"minutes": seed_minutes, "seeded": True},
            )
        )
        session.add(
            OwnerClubMeeting(
                id=_deterministic_id("mtg_seed", f"{state.club_id}:2"),
                club_id=state.club_id,
                owner_user_id=state.owner_user_id,
                title="Upcoming Technical & Medical Workload Review",
                agenda="Monitor recovery load, training sharpness, and transfer shortlist.",
                meeting_type="tactical",
                world_day=world_day + 1,
                status="scheduled",
                attendees_json=["Club Owner", mgr_name, "Dr. Amara Okafor", "Kelechi Nwosu"],
                minutes_summary=f"Scheduled for World Day {world_day + 1} with technical and medical leads.",
                decisions_json=[],
                created_by_user_id=state.owner_user_id,
                metadata_json={"minutes": [], "seeded": True},
            )
        )
        session.flush()

    sync_living_club_communications(session, state)


def sync_living_club_communications(session: Session, state: OwnerClubState) -> list[OwnerClubMessage]:
    """Generate idempotent event-driven inbound staff & player messages grounded in real club state."""
    created: list[OwnerClubMessage] = []
    squad = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
    regens = [p for p in squad if p.is_regen]
    injured = [p for p in squad if int(p.injured_days or 0) > 0]
    low_morale = sorted([p for p in squad if int(p.morale or 50) <= 45], key=lambda item: int(item.morale or 50))
    pending_inbox = int(
        session.scalar(
            select(func.count(OwnerInboxItem.id)).where(
                OwnerInboxItem.club_id == state.club_id,
                OwnerInboxItem.status == "open",
                OwnerInboxItem.is_decision.is_(True),
            )
        )
        or 0
    )
    watchlist_count = int(
        session.scalar(
            select(func.count(OwnerScoutingWatchlist.id)).where(OwnerScoutingWatchlist.club_id == state.club_id)
        )
        or 0
    )
    treasury = int(_treasury_gtex(session, state.club_id))

    if injured:
        lead = injured[0]
        names = ", ".join(f"{p.name} ({p.injured_days}d)" for p in injured[:3])
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key="staff:medical_director",
            participant_type="staff",
            participant_id="staff:medical_director",
            participant_name="Dr. Amara Okafor",
            participant_role="Medical Director",
            subject="Medical & Injury Availability",
        )
        ev_key = f"living:medical:{state.club_id}:day:{int(state.world_day or 1)}:{lead.id}:{int(lead.injured_days or 0)}"
        created.append(
            _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="staff",
                sender_id="staff:medical_director",
                sender_name="Dr. Amara Okafor",
                sender_role="Medical Director",
                topic="Injury Assessment",
                body=f"Medical bulletin: {len(injured)} squad player(s) injured — {names}. Recommend load management before next selection.",
                source="staff_event",
                priority="high",
                linked_entity_type="player",
                linked_entity_id=lead.id,
                linked_event_key=ev_key,
                action_payload={"action_type": "open_route", "route": "/app/squad", "label": "Review Injured Players", "player_id": lead.id},
            )
        )

    if regens:
        top_regen = max(regens, key=lambda item: int(item.potential or item.rating or 0))
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key="staff:head_of_youth_development",
            participant_type="staff",
            participant_id="staff:head_of_youth_development",
            participant_name="Femi Ogunleye",
            participant_role="Head of Youth Development",
            subject="Academy Prospect & Regen Pathway",
        )
        ev_key = f"living:hoyd:{state.club_id}:{top_regen.id}:rtg:{int(top_regen.rating or 0)}"
        created.append(
            _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="staff",
                sender_id="staff:head_of_youth_development",
                sender_name="Femi Ogunleye",
                sender_role="Head of Youth Development",
                topic="Academy Standout",
                body=f"{top_regen.name} ({top_regen.position}, age {top_regen.age}) leads the academy at OVR {top_regen.rating} / POT {top_regen.potential}. Consider structured senior minutes.",
                source="staff_event",
                priority="normal",
                linked_entity_type="player",
                linked_entity_id=top_regen.id,
                linked_event_key=ev_key,
                action_payload={"action_type": "open_route", "route": "/app/academy", "label": "Inspect Academy", "player_id": top_regen.id},
            )
        )

    if len(squad) < 18 or watchlist_count > 0:
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key="staff:chief_scout",
            participant_type="staff",
            participant_id="staff:chief_scout",
            participant_name="Kelechi Nwosu",
            participant_role="Chief Scout",
            subject="Recruitment & Watchlist Dossier",
        )
        ev_key = f"living:scout:{state.club_id}:sq:{len(squad)}:wl:{watchlist_count}"
        created.append(
            _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="staff",
                sender_id="staff:chief_scout",
                sender_name="Kelechi Nwosu",
                sender_role="Chief Scout",
                topic="Recruitment Readiness",
                body=f"Scouting desk logs {len(squad)} registered players and {watchlist_count} tracked prospect(s). Ready to propose targets matching treasury ({treasury} GTX).",
                source="staff_event",
                priority="normal",
                linked_entity_type="scouting",
                linked_entity_id=state.club_id,
                linked_event_key=ev_key,
                action_payload={"action_type": "open_route", "route": "/app/transfer-hub", "label": "Open Transfer Hub"},
            )
        )

    if pending_inbox > 0:
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key="staff:general_manager",
            participant_type="staff",
            participant_id="staff:general_manager",
            participant_name="Dayo Adeleke",
            participant_role="General Manager",
            subject="Executive Boardroom & Pending Decisions",
        )
        ev_key = f"living:gm:{state.club_id}:pending:{pending_inbox}:day:{int(state.world_day or 1)}"
        created.append(
            _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="staff",
                sender_id="staff:general_manager",
                sender_name="Dayo Adeleke",
                sender_role="General Manager",
                topic="Pending Approvals",
                body=f"You have {pending_inbox} open executive decision(s) awaiting sign-off. Treasury balance stands at {treasury} GTX.",
                source="staff_event",
                priority="high" if pending_inbox >= 3 else "normal",
                linked_entity_type="inbox_item",
                linked_entity_id=state.club_id,
                linked_event_key=ev_key,
                action_payload={"action_type": "open_tab", "tab": "decisions", "label": "Review Decisions"},
            )
        )

    if low_morale:
        player = low_morale[0]
        conv = _get_or_create_conversation(
            session,
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key=f"player:{player.id}",
            participant_type="player",
            participant_id=player.id,
            participant_name=player.name,
            participant_role=f"{player.position} · {'Academy Regen' if player.is_regen else 'First Team'}",
            subject=f"Player Check-In · {player.name}",
        )
        ev_key = f"living:player:{state.club_id}:{player.id}:morale:{int(player.morale or 0)}"
        created.append(
            _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="player",
                sender_id=player.id,
                sender_name=player.name,
                sender_role=f"{player.position} · First Team",
                topic="Playing Time & Morale",
                body=f"Boss, my current morale sits at {player.morale}/100 (OVR {player.rating}, {player.minutes} mins played). I want clarity on my role going into the next fixture.",
                source="player_event",
                priority="high",
                linked_entity_type="player",
                linked_entity_id=player.id,
                linked_event_key=ev_key,
                action_payload={"action_type": "open_route", "route": "/app/lineup", "label": "Check Matchday Lineup", "player_id": player.id},
            )
        )
    return created


def _contextual_npc_reply(
    session: Session,
    *,
    state: OwnerClubState,
    conv: OwnerClubConversation,
    owner_body: str,
    topic: str | None,
) -> tuple[str | None, dict[str, Any]]:
    recent = list(
        session.scalars(
            select(OwnerClubMessage)
            .where(OwnerClubMessage.conversation_id == conv.id)
            .order_by(OwnerClubMessage.seq.desc())
            .limit(4)
        ).all()
    )
    now = datetime.now(timezone.utc)
    if len(recent) >= 2:
        last_npc = next((m for m in recent if m.sender_type != "owner"), None)
        if last_npc is not None:
            last_dt = last_npc.created_at if last_npc.created_at.tzinfo else last_npc.created_at.replace(tzinfo=timezone.utc)
            if (now - last_dt) < timedelta(seconds=20) and len(owner_body.strip()) < 24:
                return None, {}

    lower_body = owner_body.lower()
    squad = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
    treasury = int(_treasury_gtex(session, state.club_id))
    prestige = int(state.prestige or 0)

    if conv.participant_type == "player" and conv.participant_id:
        player = session.get(OwnerSquadPlayer, conv.participant_id) or next(
            (p for p in squad if p.id == conv.participant_id), None
        )
        if player is not None:
            fit_val = max(45, 100 - int(player.injured_days or 0) * 6)
            if any(w in lower_body for w in ("start", "lineup", "minutes", "play", "pitch", "training")):
                return (
                    f"Appreciate the clarity at {state.club_name}, Boss. Sitting at {player.morale}/100 morale, Fitness {fit_val}%, and OVR {player.rating}, I'm ready at {player.position} when called on.",
                    {"action_type": "open_route", "route": "/app/lineup", "label": "Adjust Lineup", "player_id": player.id},
                )
            if any(w in lower_body for w in ("rest", "recover", "injury", "medical", "fitness")):
                return (
                    f"Understood for {state.club_name}. Injury counter shows {player.injured_days}d remaining (Fitness {fit_val}%, OVR {player.rating}); I'll stick closely to the rehab plan.",
                    {"action_type": "open_route", "route": "/app/squad", "label": "Check Fitness", "player_id": player.id},
                )
            return (
                f"Message received on '{topic or 'first-team standards'}' at {state.club_name}. My Fitness is {fit_val}% and rating stands at OVR {player.rating} ahead of World Day {int(state.world_day or 1)}.",
                {},
            )

    p_id = (conv.participant_id or "").lower()
    if "medical" in p_id:
        injured = [p for p in squad if int(p.injured_days or 0) > 0]
        if injured:
            return (
                f"Medical unit is tracking {len(injured)} injured player(s), led by {injured[0].name} ({injured[0].injured_days}d remaining).",
                {"action_type": "open_route", "route": "/app/squad", "label": "Medical Bay"},
            )
        return (
            f"Full clearance across all {len(squad)} registered players right now.",
            {"action_type": "open_route", "route": "/app/squad", "label": "Medical Bay"},
        )
    if "youth" in p_id or "hoyd" in p_id:
        regens = [p for p in squad if p.is_regen]
        if regens:
            best = max(regens, key=lambda p: int(p.potential or p.rating or 0))
            return (
                f"Academy tracks {len(regens)} regens, highlighted by {best.name} (OVR {best.rating} / POT {best.potential}).",
                {"action_type": "open_route", "route": "/app/academy", "label": "Academy Pipeline"},
            )
        return ("Academy development cycle is running; next intake window is tracked on campus.", {})
    if "scout" in p_id:
        wl = int(
            session.scalar(
                select(func.count(OwnerScoutingWatchlist.id)).where(OwnerScoutingWatchlist.club_id == state.club_id)
            )
            or 0
        )
        return (
            f"Scouting holds {wl} shortlisted prospect(s) for our {len(squad)}-player roster ({treasury} GTX treasury).",
            {"action_type": "open_route", "route": "/app/transfer-hub", "label": "Scouting Desk"},
        )
    if "general_manager" in p_id or "gm" in p_id:
        return (
            f"Logged for executive operations. Treasury is {treasury} GTX with Prestige {prestige}.",
            {"action_type": "open_route", "route": "/app/finance", "label": "Club Finance"},
        )
    avg_morale = round(sum(int(p.morale or 50) for p in squad) / len(squad), 1) if squad else 70
    return (
        f"Tactical desk acknowledges '{topic or 'match preparation'}' across {len(squad)} players (avg morale {avg_morale}/100).",
        {"action_type": "open_route", "route": "/app/lineup", "label": "Tactical Lineup"},
    )


def _message_dict(msg: OwnerClubMessage) -> dict[str, Any]:
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "club_id": msg.club_id,
        "seq": int(msg.seq or 0),
        "sender_user_id": msg.sender_user_id,
        "sender_type": msg.sender_type,
        "sender_id": msg.sender_id,
        "sender_name": msg.sender_name,
        "sender_role": msg.sender_role,
        "tag": msg.topic,
        "topic": msg.topic,
        "body": msg.body,
        "source": msg.source,
        "priority": msg.priority,
        "linked_entity_type": msg.linked_entity_type,
        "linked_entity_id": msg.linked_entity_id,
        "action_payload": dict(msg.action_payload_json or {}),
        "is_read": bool(msg.is_read),
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def _thread_dict(session: Session, conv: OwnerClubConversation, *, limit: int = 40, before_seq: int | None = None) -> dict[str, Any]:
    q = select(OwnerClubMessage).where(OwnerClubMessage.conversation_id == conv.id)
    if before_seq is not None:
        q = q.where(OwnerClubMessage.seq < before_seq)
    rows_desc = list(session.scalars(q.order_by(OwnerClubMessage.seq.desc()).limit(limit + 1)).all())
    has_more = len(rows_desc) > limit
    rows = list(reversed(rows_desc[:limit]))
    unread_count = int(
        session.scalar(
            select(func.count(OwnerClubMessage.id)).where(
                OwnerClubMessage.conversation_id == conv.id,
                OwnerClubMessage.is_read.is_(False),
            )
        )
        or 0
    )
    staff_meta = STAFF_ALIASES.get((conv.participant_id or "").lower()) or STAFF_ALIASES.get(conv.participant_role.lower())
    return {
        "thread_id": conv.id,
        "thread_key": conv.thread_key,
        "club_id": conv.club_id,
        "channel_type": conv.channel_type,
        "participant_type": conv.participant_type,
        "participant_id": conv.participant_id,
        "participant_name": conv.participant_name,
        "participant_role": conv.participant_role,
        "portrait_url": staff_meta["portrait_url"] if staff_meta else None,
        "subject": conv.subject,
        "archived_at": conv.archived_at.isoformat() if conv.archived_at else None,
        "unread_count": unread_count,
        "last_message_seq": int(conv.last_message_seq or 0),
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "has_more": has_more,
        "next_before_seq": int(rows[0].seq) if has_more and rows else None,
        "messages": [_message_dict(m) for m in rows],
    }


def _meeting_dict(mtg: OwnerClubMeeting) -> dict[str, Any]:
    meta = dict(mtg.metadata_json or {})
    minutes_items = list(meta.get("minutes") or [])
    return {
        "id": mtg.id,
        "meeting_id": mtg.id,
        "club_id": mtg.club_id,
        "title": mtg.title,
        "agenda": mtg.agenda,
        "meeting_type": mtg.meeting_type,
        "world_day": mtg.world_day,
        "scheduled_for": mtg.scheduled_for.isoformat() if mtg.scheduled_for else None,
        "status": mtg.status,
        "participants": list(mtg.attendees_json or []),
        "attendees": list(mtg.attendees_json or []),
        "outcome_summary": mtg.minutes_summary,
        "minutes": minutes_items,
        "minutes_summary": mtg.minutes_summary,
        "decisions": list(mtg.decisions_json or []),
        "morale_boost_applied": bool(meta.get("morale_boost_applied")),
        "created_at": mtg.created_at.isoformat() if mtg.created_at else None,
    }


def _announcement_dict(ann: OwnerClubAnnouncement) -> dict[str, Any]:
    return {
        "id": ann.id,
        "announcement_id": ann.id,
        "club_id": ann.club_id,
        "title": ann.title,
        "body": ann.body,
        "audience": ann.audience,
        "priority": ann.priority,
        "author": "Office of the Club Owner",
        "world_day": ann.published_world_day,
        "published_world_day": ann.published_world_day,
        "created_at": ann.created_at.isoformat() if ann.created_at else None,
    }


def get_club_communications_durable(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    search: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    from app.owner_console import service, storytelling

    state = require_state(session, club_id, user_id)
    ensure_club_conversations_seeded(session, state)

    squad_players = list(
        session.scalars(
            select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).order_by(OwnerSquadPlayer.rating.desc())
        ).all()
    )
    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))

    convs_all = list(
        session.scalars(
            select(OwnerClubConversation)
            .where(OwnerClubConversation.club_id == club_id)
            .order_by(OwnerClubConversation.last_message_at.desc().nullslast())
        ).all()
    )
    conv_by_key = {c.thread_key: c for c in convs_all}

    staff_contacts: list[dict[str, Any]] = []
    for member in STAFF_DIRECTORY:
        rk = member["role_key"]
        resolved_name = (
            mgr.get("name", member["name"])
            if rk == "first_team_manager"
            else (exec_staff.get(rk) or {}).get("name", member["name"])
        )
        conv = conv_by_key.get(member["id"])
        staff_contacts.append(
            {
                "contact_id": member["id"],
                "role_key": rk,
                "name": resolved_name,
                "title": member["role"],
                "department": member["department"],
                "mood": int((mgr if rk == "first_team_manager" else exec_staff.get(rk) or {}).get("mood", 78)),
                "loyalty": int((mgr if rk == "first_team_manager" else exec_staff.get(rk) or {}).get("loyalty", 14)),
                "portrait_url": member["portrait_url"],
                "route": member["route"],
                "thread_id": conv.id if conv else None,
            }
        )

    player_contacts: list[dict[str, Any]] = []
    for p in squad_players:
        conv = conv_by_key.get(f"player:{p.id}")
        player_contacts.append(
            {
                "contact_id": f"player:{p.id}",
                "player_id": p.id,
                "name": p.name,
                "position": p.position,
                "rating": int(p.rating or 60),
                "morale": int(p.morale or 70),
                "injured_days": int(p.injured_days or 0),
                "fitness": max(45, 100 - int(p.injured_days or 0) * 6),
                "is_regen": bool(p.is_regen),
                "squad_status": "academy" if p.is_regen else "senior",
                "portrait_url": storytelling.resolve_player_portrait_url(session, p.id, p.name),
                "thread_id": conv.id if conv else None,
            }
        )

    direct_convs = [c for c in convs_all if c.channel_type == "direct" and (include_archived or c.archived_at is None)]
    direct_threads = [_thread_dict(session, c) for c in direct_convs]
    for t in direct_threads:
        if t["participant_type"] == "player" and t["participant_id"]:
            t["portrait_url"] = storytelling.resolve_player_portrait_url(
                session, str(t["participant_id"]), str(t["participant_name"])
            )

    staff_conv = conv_by_key.get("room:staff") or _get_or_create_conversation(
        session,
        club_id=club_id,
        owner_user_id=state.owner_user_id,
        channel_type="staff_room",
        thread_key="room:staff",
        participant_type="room",
        participant_id="room:staff",
        participant_name="Staff Technical Room",
        participant_role="Executive & Technical Staff",
    )
    squad_conv = conv_by_key.get("room:squad") or _get_or_create_conversation(
        session,
        club_id=club_id,
        owner_user_id=state.owner_user_id,
        channel_type="squad_room",
        thread_key="room:squad",
        participant_type="room",
        participant_id="room:squad",
        participant_name="Dressing Room",
        participant_role="First-Team & Academy Squad",
    )
    staff_room_meta = _thread_dict(session, staff_conv)
    squad_room_meta = _thread_dict(session, squad_conv)

    meetings = [
        _meeting_dict(m)
        for m in session.scalars(
            select(OwnerClubMeeting)
            .where(OwnerClubMeeting.club_id == club_id)
            .order_by(OwnerClubMeeting.created_at.desc())
            .limit(40)
        ).all()
    ]
    announcements = [
        _announcement_dict(a)
        for a in session.scalars(
            select(OwnerClubAnnouncement)
            .where(OwnerClubAnnouncement.club_id == club_id)
            .order_by(OwnerClubAnnouncement.created_at.desc())
            .limit(40)
        ).all()
    ]

    inbox_rows = list(
        session.scalars(
            select(OwnerInboxItem)
            .where(OwnerInboxItem.club_id == club_id, OwnerInboxItem.user_id == user_id)
            .order_by(OwnerInboxItem.created_at.desc())
            .limit(60)
        ).all()
    )
    inbox_items = [service.inbox_dict(i) for i in inbox_rows if i.archived_at is None]
    archived_items = [service.inbox_dict(i) for i in inbox_rows if i.archived_at is not None or i.status == "resolved"]
    open_decisions = [i for i in inbox_items if i.get("is_decision") and i.get("status") == "open"]
    briefing = storytelling.get_daily_briefing(session, user_id, club_id, force_refresh=False)
    dilemma = briefing.get("boardroom_dilemma")

    unread_inbox = sum(1 for i in inbox_items if not i.get("is_read"))
    unread_comms = int(
        session.scalar(
            select(func.count(OwnerClubMessage.id)).where(
                OwnerClubMessage.club_id == club_id,
                OwnerClubMessage.is_read.is_(False),
            )
        )
        or 0
    )

    search_results: list[dict[str, Any]] = []
    clean_q = (search or "").strip()
    if clean_q:
        like_term = f"%{clean_q}%"
        matched = list(
            session.scalars(
                select(OwnerClubMessage)
                .where(
                    OwnerClubMessage.club_id == club_id,
                    or_(
                        OwnerClubMessage.body.ilike(like_term),
                        OwnerClubMessage.topic.ilike(like_term),
                        OwnerClubMessage.sender_name.ilike(like_term),
                        OwnerClubMessage.sender_role.ilike(like_term),
                    ),
                )
                .order_by(OwnerClubMessage.created_at.desc())
                .limit(50)
            ).all()
        )
        search_results = [_message_dict(m) for m in matched]

    user = session.get(User, user_id)
    verified_name = (user.display_name or user.full_name or user.username) if user else "Club Owner"

    return {
        "club_id": club_id,
        "club_name": state.club_name,
        "world_day": int(state.world_day or 1),
        "owner_authority": {
            "user_id": user_id,
            "verified_role": "Club Owner",
            "verified_name": verified_name,
            "can_speak_as_staff": False,
        },
        "permissions": {
            "actor_role": "club_owner",
            "can_message_staff": True,
            "can_message_players": True,
            "can_approve_budget_decisions": True,
            "can_publish_announcements": True,
            "can_schedule_meetings": True,
        },
        "counts": {
            "inbox_unread": unread_inbox,
            "direct_unread": unread_comms,
            "open_decisions": len(open_decisions) + (1 if dilemma and dilemma.get("status") == "open" else 0),
            "scheduled_meetings": sum(1 for m in meetings if m.get("status") == "scheduled"),
            "announcements": len(announcements),
            "archived": len(archived_items),
        },
        "inbox": inbox_items,
        "direct_threads": direct_threads,
        "threads": direct_threads,
        "staff_contacts": staff_contacts,
        "player_contacts": player_contacts,
        "staff_room": list(reversed(staff_room_meta["messages"])),
        "squad_room": list(reversed(squad_room_meta["messages"])),
        "staff_room_meta": staff_room_meta,
        "squad_room_meta": squad_room_meta,
        "meetings": meetings,
        "requests_decisions": {
            "inbox_decisions": open_decisions,
            "boardroom_dilemma": dilemma,
        },
        "announcements": announcements,
        "archive": archived_items,
        "search_results": search_results,
    }


def get_thread_messages_page(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    conversation_id: str,
    before_seq: int | None = None,
    limit: int = 30,
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    conv = session.get(OwnerClubConversation, conversation_id)
    if conv is None or conv.club_id != state.club_id:
        raise OwnerError("conversation_not_found", 404, "Club conversation not found.")
    return _thread_dict(session, conv, limit=limit, before_seq=before_seq)


def mark_conversation_read(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    conversation_id: str,
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    conv = session.get(OwnerClubConversation, conversation_id)
    if conv is None or conv.club_id != state.club_id:
        raise OwnerError("conversation_not_found", 404, "Club conversation not found.")
    now = datetime.now(timezone.utc)
    unread_msgs = list(
        session.scalars(
            select(OwnerClubMessage).where(
                OwnerClubMessage.conversation_id == conv.id,
                OwnerClubMessage.is_read.is_(False),
            )
        ).all()
    )
    for msg in unread_msgs:
        msg.is_read = True
        msg.read_at = now
    session.flush()
    return {"conversation_id": conv.id, "marked_count": len(unread_msgs), "read_at": now.isoformat()}


def archive_conversation(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    conversation_id: str,
    archived: bool = True,
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    conv = session.get(OwnerClubConversation, conversation_id)
    if conv is None or conv.club_id != state.club_id:
        raise OwnerError("conversation_not_found", 404, "Club conversation not found.")
    if conv.channel_type != "direct":
        raise OwnerError("invalid_operation", 400, "Staff Room and Dressing Room cannot be archived.")
    conv.archived_at = datetime.now(timezone.utc) if archived else None
    conv.updated_at = datetime.now(timezone.utc)
    session.flush()
    return {"conversation_id": conv.id, "archived_at": conv.archived_at.isoformat() if conv.archived_at else None}


def send_club_message_durable(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    thread_id: str,
    message: str,
    topic: str = "general",
    priority: str = "normal",
    request_reply: bool = True,
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    ensure_club_conversations_seeded(session, state)
    clean_body = (message or "").strip()
    if not clean_body:
        raise OwnerError("empty_message", 400, "Message body cannot be empty.")

    user = session.get(User, user_id)
    verified_owner_name = (user.display_name or user.full_name or user.username) if user else "Club Owner"

    conv = session.get(OwnerClubConversation, thread_id)
    if conv is not None and conv.club_id == club_id:
        pass
    elif thread_id == "room:staff":
        conv = _get_or_create_conversation(
            session,
            club_id=club_id,
            owner_user_id=state.owner_user_id,
            channel_type="staff_room",
            thread_key="room:staff",
            participant_type="room",
            participant_id="room:staff",
            participant_name="Staff Technical Room",
            participant_role="Executive & Technical Staff",
        )
    elif thread_id == "room:squad":
        conv = _get_or_create_conversation(
            session,
            club_id=club_id,
            owner_user_id=state.owner_user_id,
            channel_type="squad_room",
            thread_key="room:squad",
            participant_type="room",
            participant_id="room:squad",
            participant_name="Dressing Room",
            participant_role="First-Team & Academy Squad",
        )
    elif thread_id.startswith("player:"):
        player_id = thread_id.split("player:", maxsplit=1)[1].strip()
        player = session.get(OwnerSquadPlayer, player_id)
        if player is None or player.club_id != club_id:
            raise OwnerError("player_not_found", 404, "Selected squad player does not belong to this club.")
        conv = _get_or_create_conversation(
            session,
            club_id=club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key=f"player:{player.id}",
            participant_type="player",
            participant_id=player.id,
            participant_name=player.name,
            participant_role=f"{player.position} · {'Academy Regen' if player.is_regen else 'First Team'}",
            subject=f"Direct with {player.name}",
        )
    else:
        staff_meta = STAFF_ALIASES.get(thread_id.strip().lower(), STAFF_DIRECTORY[0])
        conv = _get_or_create_conversation(
            session,
            club_id=club_id,
            owner_user_id=state.owner_user_id,
            channel_type="direct",
            thread_key=staff_meta["id"],
            participant_type="staff",
            participant_id=staff_meta["id"],
            participant_name=staff_meta["name"],
            participant_role=staff_meta["role"],
            subject=f"Direct with {staff_meta['name']}",
        )

    conv.archived_at = None
    world_day = int(state.world_day or 1)
    is_substantive = len(clean_body) >= 8
    facs = dict(state.facilities_json or {})
    boost_log = dict(facs.get("_comms_boost_log") or {})
    morale_boost_applied = False
    morale_delta = 0

    if conv.channel_type == "direct" and conv.participant_type == "player" and conv.participant_id:
        plr = session.get(OwnerSquadPlayer, conv.participant_id)
        if plr is not None and plr.club_id == club_id:
            boost_key = f"day:{world_day}:player:{plr.id}"
            if is_substantive and not boost_log.get(boost_key):
                old_m = int(plr.morale or 50)
                plr.morale = int(engine.clamp(old_m + 4, 0, 100))
                morale_delta = int(plr.morale) - old_m
                morale_boost_applied = morale_delta > 0
                boost_log[boost_key] = True
                facs["_comms_boost_log"] = boost_log
                state.facilities_json = facs
                flag_modified(state, "facilities_json")
    elif conv.channel_type == "squad_room":
        boost_key = f"day:{world_day}:squad_room"
        if is_substantive and not boost_log.get(boost_key):
            squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
            for p in squad_players:
                p.morale = int(engine.clamp(int(p.morale or 50) + 2, 0, 100))
            morale_delta = 2 if squad_players else 0
            morale_boost_applied = bool(squad_players)
            boost_log[boost_key] = True
            facs["_comms_boost_log"] = boost_log
            state.facilities_json = facs
            flag_modified(state, "facilities_json")

    # Server-enforced verified owner sender identity (client sender_role cannot spoof staff/players)
    owner_msg = _append_message(
        session,
        conv=conv,
        sender_user_id=user_id,
        sender_type="owner",
        sender_id=user_id,
        sender_name=verified_owner_name,
        sender_role="Club Owner",
        topic=(topic or "").strip() or None,
        body=clean_body,
        source="owner",
        priority=priority if priority in {"low", "normal", "high", "urgent"} else "normal",
        is_read=True,
    )

    reply_msg: OwnerClubMessage | None = None
    if conv.channel_type == "direct" and request_reply:
        reply_text, action_payload = _contextual_npc_reply(
            session, state=state, conv=conv, owner_body=clean_body, topic=topic
        )
        if reply_text:
            reply_msg = _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type=conv.participant_type,
                sender_id=conv.participant_id,
                sender_name=conv.participant_name,
                sender_role=conv.participant_role,
                topic=(topic or "").strip() or conv.subject,
                body=reply_text,
                source="player_reply" if conv.participant_type == "player" else "staff_reply",
                linked_entity_type="player" if conv.participant_type == "player" else "club",
                linked_entity_id=conv.participant_id if conv.participant_type == "player" else club_id,
                action_payload=action_payload,
                is_read=True,
            )
    elif conv.channel_type == "staff_room" and request_reply and ("?" in clean_body or "@" in clean_body):
        reply_text, action_payload = _contextual_npc_reply(
            session, state=state, conv=conv, owner_body=clean_body, topic=topic
        )
        if reply_text:
            reply_msg = _append_message(
                session,
                conv=conv,
                sender_user_id=None,
                sender_type="staff",
                sender_id="staff:first_team_manager",
                sender_name="First-Team Head Coach",
                sender_role="First-Team Manager",
                topic=(topic or "").strip() or "Staff Response",
                body=reply_text,
                source="staff_reply",
                action_payload=action_payload,
                is_read=True,
            )

    if conv.channel_type == "direct":
        from app.owner_console import living_club_world

        if conv.participant_type == "player" and conv.participant_id:
            living_club_world.apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "player",
                str(conv.participant_id),
                conv.participant_name,
                delta_trust=2,
                delta_affinity=2,
                delta_tension=-1,
                reason=f"Direct conversation on {topic or 'club affairs'}",
                world_day=world_day,
            )
        elif conv.participant_type == "staff":
            staff_key = str(conv.participant_id or "general_manager").replace("staff:", "")
            living_club_world.apply_relationship_delta(
                session,
                club_id,
                "owner",
                "owner",
                "Club Owner",
                "staff",
                staff_key,
                conv.participant_name,
                delta_trust=2,
                delta_respect=2,
                delta_tension=-1,
                reason=f"Direct staff consultation on {topic or 'club operations'}",
                world_day=world_day,
            )

    session.flush()
    _publish_owner_comms_realtime(
        club_id,
        "owner_comms_message",
        {
            "conversation_id": conv.id,
            "channel_type": conv.channel_type,
            "message": _message_dict(owner_msg),
            "reply": _message_dict(reply_msg) if reply_msg else None,
        },
    )
    thread_payload = _thread_dict(session, conv)
    return {
        "status": "sent",
        "thread_id": conv.id,
        "thread": thread_payload,
        "channel_type": conv.channel_type,
        "message": _message_dict(owner_msg),
        "user_message": _message_dict(owner_msg),
        "reply": _message_dict(reply_msg) if reply_msg else None,
        "reply_message": _message_dict(reply_msg) if reply_msg else None,
        "morale_boost_applied": morale_boost_applied,
        "morale_delta": morale_delta,
        "communications": get_club_communications_durable(session, user_id=user_id, club_id=club_id),
    }


def schedule_club_meeting_durable(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    title: str,
    meeting_type: str = "boardroom",
    participants: list[str] | None = None,
    agenda: str = "",
    convene_now: bool = True,
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    ensure_club_conversations_seeded(session, state)
    clean_title = (title or "").strip()
    if len(clean_title) < 2:
        raise OwnerError("invalid_meeting", 400, "Meeting title is required.")

    facs = dict(state.facilities_json or {})
    exec_staff = dict(facs.get("_executive_staff") or {})
    gm_name = (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke")
    mgr_name = (state.manager_json or {}).get("name", "First-Team Head Coach")
    hoyd_name = (exec_staff.get("head_of_youth_development") or {}).get("name", "Femi Ogunleye")
    boost_log = dict(facs.get("_comms_boost_log") or {})
    world_day = int(state.world_day or 1)

    roster = list(participants or []) or [
        "Club Owner",
        gm_name,
        mgr_name,
        hoyd_name,
    ]
    squad = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    avg_morale = round(sum(int(p.morale or 50) for p in squad) / len(squad), 1) if squad else 70
    treasury = int(_treasury_gtex(session, club_id))

    morale_applied = False
    minutes_list: list[dict[str, str]] = []
    outcome_summary = (
        f"Scheduled '{clean_title}' for World Day {world_day} at {state.club_name} "
        f"with {', '.join(roster)}."
    )
    if convene_now:
        boost_key = f"day:{world_day}:meeting"
        if not boost_log.get(boost_key):
            for p in squad:
                p.morale = int(engine.clamp(int(p.morale or 50) + 3, 0, 100))
            mgr = dict(state.manager_json or {})
            mgr["mood"] = int(engine.clamp(int(mgr.get("mood", 72)) + 5, 0, 100))
            state.manager_json = mgr
            flag_modified(state, "manager_json")
            boost_log[boost_key] = True
            facs["_comms_boost_log"] = boost_log
            state.facilities_json = facs
            flag_modified(state, "facilities_json")
            morale_applied = True
        minutes_list = [
            {
                "speaker": gm_name,
                "role": "General Manager",
                "summary": f"Reviewed {state.club_name} treasury ({treasury} GTX) and operational alignment.",
            },
            {
                "speaker": mgr_name,
                "role": "First-Team Manager",
                "summary": f"Confirmed tactical readiness across {len(squad)} registered players (avg morale {avg_morale}/100).",
            },
            {
                "speaker": hoyd_name,
                "role": "Head of Youth Development",
                "summary": f"Reported on {sum(1 for p in squad if p.is_regen)} academy regen prospects on campus.",
            },
        ]
        outcome_summary = (
            f"Meeting convened on World Day {world_day} at {state.club_name} ({treasury} GTX treasury). "
            f"Action items ratified across {len(roster)} participants. Agenda: {agenda.strip() or 'Operational alignment'}."
        )
        session.add(
            OwnerInboxItem(
                user_id=user_id,
                club_id=club_id,
                kind="meeting_minutes",
                category="archive",
                priority="normal",
                sender="Boardroom Secretariat",
                title=f"Meeting Minutes: {clean_title}",
                what=outcome_summary,
                why=agenda.strip() or "Executive boardroom alignment.",
                payload_json={"participants": roster, "minutes": minutes_list, "morale_boost_applied": morale_applied},
                is_decision=False,
                is_read=True,
                status="resolved",
                resolution="convened",
            )
        )

    meeting = OwnerClubMeeting(
        club_id=club_id,
        owner_user_id=state.owner_user_id,
        title=clean_title,
        agenda=(agenda or "").strip(),
        meeting_type=meeting_type if meeting_type in {"boardroom", "tactical", "medical", "academy", "squad", "emergency"} else "boardroom",
        world_day=world_day,
        status="completed" if convene_now else "scheduled",
        attendees_json=roster,
        minutes_summary=outcome_summary,
        decisions_json=[],
        created_by_user_id=user_id,
        metadata_json={"minutes": minutes_list, "morale_boost_applied": morale_applied},
    )
    session.add(meeting)
    session.flush()

    staff_conv = _get_or_create_conversation(
        session,
        club_id=club_id,
        owner_user_id=state.owner_user_id,
        channel_type="staff_room",
        thread_key="room:staff",
        participant_type="room",
        participant_id="room:staff",
        participant_name="Staff Technical Room",
        participant_role="Executive & Technical Staff",
    )
    _append_message(
        session,
        conv=staff_conv,
        sender_user_id=user_id,
        sender_type="owner",
        sender_id=user_id,
        sender_name="Club Owner",
        sender_role="Club Owner",
        topic=f"Meeting: {clean_title}",
        body=outcome_summary,
        source="owner",
        linked_entity_type="meeting",
        linked_entity_id=meeting.id,
        is_read=True,
    )
    session.flush()
    _publish_owner_comms_realtime(club_id, "owner_comms_meeting", {"meeting": _meeting_dict(meeting)})
    return {
        "status": "scheduled" if not convene_now else "completed",
        "meeting": _meeting_dict(meeting),
        "morale_boost_applied": morale_applied,
        "communications": get_club_communications_durable(session, user_id=user_id, club_id=club_id),
    }


def publish_club_announcement_durable(
    session: Session,
    *,
    user_id: str,
    club_id: str,
    title: str,
    body: str,
    audience: str = "all_club",
    publish_to_newsroom: bool = False,
    also_post_to_community: bool = False,
) -> dict[str, Any]:
    from app.owner_console import storytelling
    from app.owner_console.models import OwnerNewsroomArticle

    clean_title = (title or "").strip()
    clean_body = (body or "").strip()
    if not clean_title or not clean_body:
        raise OwnerError("invalid_announcement", 400, "Announcement title and body are required.")

    state = require_state(session, club_id, user_id)
    ensure_club_conversations_seeded(session, state)
    world_day = int(state.world_day or 1)

    ann = OwnerClubAnnouncement(
        club_id=club_id,
        owner_user_id=state.owner_user_id,
        title=clean_title,
        body=clean_body,
        audience=audience or "all_club",
        priority="normal",
        published_world_day=world_day,
        published_by_user_id=user_id,
        metadata_json={"publish_to_newsroom": bool(publish_to_newsroom), "also_post_to_community": bool(also_post_to_community)},
    )
    session.add(ann)
    session.flush()

    if audience in {"all_club", "staff", "academy"}:
        staff_conv = _get_or_create_conversation(
            session,
            club_id=club_id,
            owner_user_id=state.owner_user_id,
            channel_type="staff_room",
            thread_key="room:staff",
            participant_type="room",
            participant_id="room:staff",
            participant_name="Staff Technical Room",
            participant_role="Executive & Technical Staff",
        )
        _append_message(
            session,
            conv=staff_conv,
            sender_user_id=user_id,
            sender_type="owner",
            sender_id=user_id,
            sender_name="Club Owner",
            sender_role="Club Owner",
            topic=f"Club Announcement · {clean_title}",
            body=clean_body,
            source="owner",
            linked_entity_type="announcement",
            linked_entity_id=ann.id,
            is_read=True,
        )
    if audience in {"all_club", "squad"}:
        squad_conv = _get_or_create_conversation(
            session,
            club_id=club_id,
            owner_user_id=state.owner_user_id,
            channel_type="squad_room",
            thread_key="room:squad",
            participant_type="room",
            participant_id="room:squad",
            participant_name="Dressing Room",
            participant_role="First-Team & Academy Squad",
        )
        _append_message(
            session,
            conv=squad_conv,
            sender_user_id=user_id,
            sender_type="owner",
            sender_id=user_id,
            sender_name="Club Owner",
            sender_role="Club Owner",
            topic=f"Club Announcement · {clean_title}",
            body=clean_body,
            source="owner",
            linked_entity_type="announcement",
            linked_entity_id=ann.id,
            is_read=True,
        )

    news_article = None
    if publish_to_newsroom:
        save_ctx = storytelling.resolve_save_context_id(session, club_id)
        crest_url = storytelling.resolve_club_crest_url(session, club_id, state.club_name)
        facts = {
            "event_type": "official_club_communique",
            "club_name": state.club_name,
            "world_day": world_day,
            "audience": audience,
        }
        grounding = storytelling.validate_article_grounding(facts, clean_body)
        if not grounding["valid"]:
            for num in grounding["unverified_numbers"]:
                facts[f"stated_figure_{num}"] = num
            grounding = storytelling.validate_article_grounding(facts, clean_body)
        art = OwnerNewsroomArticle(
            save_context_id=save_ctx,
            club_id=club_id,
            visibility="global",
            category="club_announcement",
            headline=f"Official Communiqué · {state.club_name}: {clean_title}",
            subheadline=f"Released by the Office of the Club Owner on World Day {world_day}.",
            hero_image_url="/console/img/prestige/06_academy_campus_aerial_a.png",
            club_crest_url=crest_url,
            established_facts_json=facts,
            editorial_narration=clean_body,
            grounding_report_json=grounding,
            source_event_id=ann.id,
            status="published",
            idempotency_key=f"news:ann:{ann.id}",
        )
        session.add(art)
        session.flush()
        news_article = storytelling.newsroom_dict(art)

    community_post_id: str | None = None
    if also_post_to_community:
        from app.models.community_social import CommunityPost

        if session.get(ClubProfile, club_id) is not None:
            post = CommunityPost(
                author_user_id=user_id,
                post_type="club_announcement",
                title=clean_title,
                body=clean_body,
                channel_slug="club-showcase",
                club_id=club_id,
                tags_json=["club-announcement"],
                is_official=False,
                metadata_json={"source": "owner_announcement", "announcement_id": ann.id},
            )
            session.add(post)
            session.flush()
            community_post_id = post.id

    session.flush()
    _publish_owner_comms_realtime(
        club_id,
        "owner_comms_announcement",
        {"announcement": _announcement_dict(ann), "community_post_id": community_post_id},
    )
    return {
        "status": "published",
        "announcement": _announcement_dict(ann),
        "newsroom_article": news_article,
        "community_post_id": community_post_id,
        "communications": get_club_communications_durable(session, user_id=user_id, club_id=club_id),
    }


def list_all_clubs_communications_summary(session: Session, *, user_id: str) -> dict[str, Any]:
    states = list(
        session.scalars(
            select(OwnerClubState).where(OwnerClubState.owner_user_id == user_id).order_by(OwnerClubState.club_name.asc())
        ).all()
    )
    clubs_summary: list[dict[str, Any]] = []
    total_unread_inbox = 0
    total_unread_comms = 0
    for st in states:
        ensure_club_conversations_seeded(session, st)
        unread_inbox = int(
            session.scalar(
                select(func.count(OwnerInboxItem.id)).where(
                    OwnerInboxItem.club_id == st.club_id,
                    OwnerInboxItem.user_id == user_id,
                    OwnerInboxItem.archived_at.is_(None),
                    OwnerInboxItem.is_read.is_(False),
                )
            )
            or 0
        )
        unread_comms = int(
            session.scalar(
                select(func.count(OwnerClubMessage.id)).where(
                    OwnerClubMessage.club_id == st.club_id,
                    OwnerClubMessage.is_read.is_(False),
                )
            )
            or 0
        )
        pending_decisions = int(
            session.scalar(
                select(func.count(OwnerInboxItem.id)).where(
                    OwnerInboxItem.club_id == st.club_id,
                    OwnerInboxItem.user_id == user_id,
                    OwnerInboxItem.status == "open",
                    OwnerInboxItem.is_decision.is_(True),
                )
            )
            or 0
        )
        total_unread_inbox += unread_inbox
        total_unread_comms += unread_comms
        clubs_summary.append(
            {
                "club_id": st.club_id,
                "club_name": st.club_name,
                "world_day": int(st.world_day or 1),
                "unread_inbox": unread_inbox,
                "unread_comms": unread_comms,
                "pending_decisions": pending_decisions,
            }
        )
    return {
        "total_unread_inbox": total_unread_inbox,
        "total_unread_comms": total_unread_comms,
        "total_unread": total_unread_inbox + total_unread_comms,
        "clubs": clubs_summary,
    }


__all__ = [
    "archive_conversation",
    "backfill_legacy_club_communications",
    "ensure_club_conversations_seeded",
    "get_club_communications_durable",
    "get_thread_messages_page",
    "list_all_clubs_communications_summary",
    "mark_conversation_read",
    "publish_club_announcement_durable",
    "schedule_club_meeting_durable",
    "send_club_message_durable",
    "sync_living_club_communications",
]
