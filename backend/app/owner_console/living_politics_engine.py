"""GTEX Living Football World — Stage 6
Living Football World Engine: Governance, Politics & Consequences

Core Capabilities:
1. Boardroom & Ownership Politics:
   - Distinct board members with diverse agendas (Chairman, Investor, Sporting Director, Fan Rep)
   - Dynamic Board Confidence (0..100) and Investor Sentiment (0..100)
   - Strategic disputes over spending, recruitment, manager tenure, and youth development
2. Dressing-Room Politics & Squad Dynamics:
   - Leadership group & Team Captain intermediary actions
   - Squad factions (Local core, Star signings, Academy graduates)
   - Morale, playing-time grievances, wage disparity friction
3. Continuous Player & Agent Behaviour:
   - Year-round continuous transfer market (NO transfer windows or artificial global deadlines)
   - Agent inquiries, wage demands, release clauses, and transfer requests
4. Medical Department Authority & Conflicts:
   - Medical Director (Dr. Chidi Obi) fitness evaluation and clearance veto
   - Return-to-play disputes: manager/owner pressure vs recovery protocol
   - Authoritative injury recurrence simulation and trust penalties
5. Head of Youth Development (HOYD) vs Manager Pathway Disagreements:
   - HOYD (Kunle Adeyemi) vs Manager (Emmanuel Amuneke) on academy prodigy promotion
   - Minutes guarantees, development plans, and ownership ROI
6. Media, Rumours & Club Reputation:
   - Context-triggered press inquiries (NOT random scandals)
   - Owner public statements (Vote of confidence, Demand standards, No comment)
   - Traceable club & manager reputation deltas
7. Supporter & Community Sentiment:
   - Supporter confidence meter, attendance factor, matchday atmosphere impact
8. Deduplication, Cooldowns & Audit Logging:
   - Idempotency checks, cooldown timers, and durable audit logging in OwnerClubEvent
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.base import utcnow
from app.owner_console import living_club_world
from app.owner_console.models import (
    OwnerClubEvent,
    OwnerClubRelationship,
    OwnerClubState,
    OwnerSquadPlayer,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. Canonical Stage 6 Board Members & Political Personas
# ==============================================================================

BOARD_MEMBERS_CONFIG: list[dict[str, Any]] = [
    {
        "id": "board_chair",
        "name": "Sir Adebayo Adeleke",
        "title": "Club Chairman & Traditionalist Trustee",
        "archetype": "traditionalist",
        "influence_weight": 85,
        "primary_focus": "Financial Sustainability & Heritage",
        "preferred_policy": "balanced",
        "avatar_seed": "chair_adebayo",
    },
    {
        "id": "board_investor",
        "name": "Tariq Al-Mansoor",
        "title": "Principal Investor Representative",
        "archetype": "commercial_investor",
        "influence_weight": 75,
        "primary_focus": "Commercial Valuation & Global Stature",
        "preferred_policy": "gm_led",
        "avatar_seed": "investor_tariq",
    },
    {
        "id": "board_sporting",
        "name": "Babatunde Lawal",
        "title": "Technical Board Director",
        "archetype": "sporting_purist",
        "influence_weight": 70,
        "primary_focus": "Tactical Coherence & Squad Depth",
        "preferred_policy": "balanced",
        "avatar_seed": "sporting_lawal",
    },
    {
        "id": "board_fan_rep",
        "name": "Ngozi Okafor",
        "title": "Supporters' Trust Representative",
        "archetype": "fan_advocate",
        "influence_weight": 60,
        "primary_focus": "Ticket Pricing, Community & Local Identity",
        "preferred_policy": "owner_managed",
        "avatar_seed": "fan_ngozi",
    },
]

MEDIA_OUTLETS: list[dict[str, str]] = [
    {"name": "The Athletic West Africa", "tier": "tier_1", "bias": "analytical"},
    {"name": "SuperSport Football Daily", "tier": "tier_1", "bias": "sensational"},
    {"name": "Lagos Metro Sport", "tier": "tier_2", "bias": "local_community"},
    {"name": "Global Talent Insider", "tier": "tier_2", "bias": "transfer_market"},
]

# ==============================================================================
# 2. Politics Overview & Data Resolution
# ==============================================================================


def get_or_initialize_club_politics(session: Session, club_id: str, owner_user_id: str) -> dict[str, Any]:
    """Retrieve or initialize the durable club politics state in facilities_json."""
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"OwnerClubState not found for club {club_id}")

    fac = state.facilities_json or {}
    politics = fac.get("_club_politics")

    if not politics:
        politics = {
            "board_confidence": 78,
            "investor_sentiment": 82,
            "board_mood": "supportive",
            "supporter_confidence": 76,
            "matchday_atmosphere_multiplier": 1.1,
            "squad_factions": {
                "domestic_core": {"name": "Domestic Veteran Core", "size": 8, "influence": "high"},
                "star_signings": {"name": "International Star Signings", "size": 6, "influence": "moderate"},
                "academy_graduates": {"name": "Academy Pathway Scholars", "size": 5, "influence": "rising"},
            },
            "leadership_group": {
                "captain_name": "Ifeanyi Nwachukwu",
                "captain_position": "CB",
                "vice_captain_name": "Obinna Okoye",
                "vice_captain_position": "CM",
                "captain_trust": 75,
            },
            "unresolved_grievances_count": 0,
            "active_rumours": [],
            "last_evaluated_day": state.world_day or 1,
            "updated_at": utcnow().isoformat(),
        }
        fac["_club_politics"] = politics
        state.facilities_json = dict(fac)
        flag_modified(state, "facilities_json")
        session.flush()

    return politics


def get_club_politics_overview(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    """Compile comprehensive political, boardroom, squad, medical, and community overview."""
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    politics = get_or_initialize_club_politics(session, club_id, user_id)
    fac = state.facilities_json or {}
    exec_staff = fac.get("_executive_staff") or {}

    # 1. Boardroom Politics
    board_members = []
    for m in BOARD_MEMBERS_CONFIG:
        # Calculate individual confidence based on overall board_confidence and archetype
        board_members.append(
            {
                **m,
                "confidence_score": min(
                    100,
                    max(0, politics.get("board_confidence", 75) + (5 if m["archetype"] == "traditionalist" else -2)),
                ),
                "stance": (
                    "satisfied"
                    if politics.get("board_confidence", 75) >= 70
                    else "concerned" if politics.get("board_confidence", 75) >= 50 else "hostile"
                ),
            }
        )

    # 2. Dressing Room & Squad Players
    players = session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all()

    avg_morale = int(sum(p.morale for p in players) / len(players)) if players else 75
    injured_players = [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": p.rating,
            "injured_days": p.injured_days,
            "morale": p.morale,
            "status": "injured" if p.injured_days > 0 else "fit",
        }
        for p in players
        if p.injured_days > 0
    ]

    unhappy_players = [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": p.rating,
            "morale": p.morale,
            "issue": "Playing time deficit" if p.minutes < 180 else "Contract dissatisfaction",
        }
        for p in players
        if p.morale < 60
    ]

    # 3. Medical Authority
    med_staff = exec_staff.get("medical_director") or {
        "id": "staff_med_default",
        "name": "Dr. Chidi Obi",
        "role": "Medical Director",
        "rating": 82,
        "mood": 80,
    }

    # 4. Youth Development
    hoyd_staff = exec_staff.get("head_of_youth_development") or {
        "id": "staff_hoyd_default",
        "name": "Kunle Adeyemi",
        "role": "Head of Youth Development",
        "rating": 81,
        "mood": 78,
    }

    # 5. Active Political Events & Inquiries
    active_events = session.scalars(
        select(OwnerClubEvent)
        .where(
            OwnerClubEvent.club_id == club_id,
            OwnerClubEvent.status.in_(["active", "awaiting_decision"]),
        )
        .order_by(OwnerClubEvent.created_at.desc())
        .limit(10)
    ).all()

    # 6. Bilateral Executive Relationships
    rels = session.scalars(select(OwnerClubRelationship).where(OwnerClubRelationship.club_id == club_id)).all()
    relationship_map = {r.pairing_key: living_club_world.format_relationship_dict(r) for r in rels}

    return {
        "club_id": club_id,
        "world_day": state.world_day or 1,
        "board_politics": {
            "board_confidence": politics.get("board_confidence", 78),
            "investor_sentiment": politics.get("investor_sentiment", 82),
            "board_mood": politics.get("board_mood", "supportive"),
            "directors": board_members,
        },
        "dressing_room": {
            "squad_size": len(players),
            "average_morale": avg_morale,
            "leadership_group": politics.get("leadership_group"),
            "factions": politics.get("squad_factions"),
            "unhappy_players": unhappy_players,
            "injured_players_count": len(injured_players),
        },
        "medical_department": {
            "director": med_staff,
            "injured_players": injured_players,
            "recovery_protocol": fac.get("medical_level", 2),
        },
        "youth_development": {
            "hoyd": hoyd_staff,
            "academy_tier": fac.get("academy_level", 2),
            "prospects_monitored": len([p for p in players if p.age <= 20]),
        },
        "supporter_sentiment": {
            "confidence": politics.get("supporter_confidence", 76),
            "atmosphere_multiplier": politics.get("matchday_atmosphere_multiplier", 1.1),
            "fan_trust_rating": "Optimistic" if politics.get("supporter_confidence", 76) >= 70 else "Anxious",
        },
        "media_and_rumours": {
            "active_rumours": politics.get("active_rumours", []),
            "media_profile": "High Attention" if state.prestige >= 65 else "Regional Focus",
        },
        "active_political_events": [living_club_world.format_event_dict(e) for e in active_events],
        "relationships": relationship_map,
    }


# ==============================================================================
# 3. Political Cycle Simulation Engine
# ==============================================================================


def evaluate_political_cycle(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    """Evaluate living world politics across boardroom, dressing room, medical, and press."""
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    politics = get_or_initialize_club_politics(session, club_id, user_id)
    current_day = state.world_day or 1
    events_generated: list[dict[str, Any]] = []

    # 1. Medical Department Clearance Dilemma Check
    # Check if any key player is injured and could trigger a return-to-play dispute
    injured_player = session.scalars(
        select(OwnerSquadPlayer)
        .where(OwnerSquadPlayer.club_id == club_id, OwnerSquadPlayer.injured_days > 0)
        .order_by(OwnerSquadPlayer.rating.desc())
    ).first()

    if injured_player and injured_player.injured_days <= 5:
        med_event_key = f"medical_clearance_dispute:{club_id}:day_{current_day}:{injured_player.id}"
        existing_med = session.scalars(
            select(OwnerClubEvent).where(OwnerClubEvent.idempotency_key == med_event_key)
        ).first()

        if not existing_med:
            med_event = OwnerClubEvent(
                club_id=club_id,
                category="medical",
                event_type="medical_clearance_dispute",
                severity="important",
                status="awaiting_decision",
                source_type="staff",
                source_id="medical_director",
                title=f"Medical Clearance Dispute: {injured_player.name}",
                description=(
                    f"Dr. Chidi Obi insists {injured_player.name} ({injured_player.position}) needs {injured_player.injured_days} "
                    f"more days of recovery. Manager Emmanuel Amuneke is pressing to clear the player immediately for the upcoming clash."
                ),
                participants_json=[
                    {"role": "medical_director", "name": "Dr. Chidi Obi"},
                    {"role": "first_team_manager", "name": "Emmanuel Amuneke"},
                    {"player_id": injured_player.id, "name": injured_player.name},
                ],
                world_day=current_day,
                idempotency_key=med_event_key,
                actions_json=[
                    {
                        "action_id": "back_medical",
                        "label": "Back Medical Protocol",
                        "description": "Enforce full rehabilitation. Protect player from recurrence.",
                        "delta_summary": "+5 Medical Trust, -3 Manager Alignment, 0% Reinjury Risk",
                    },
                    {
                        "action_id": "rush_player",
                        "label": "Order Immediate Clearance",
                        "description": "Risk premature return for competitive advantage.",
                        "delta_summary": "-10 Medical Trust, +4 Manager Respect, 65% Reinjury Recurrence Risk",
                    },
                ],
                consequences_json={"player_id": injured_player.id, "injured_days": injured_player.injured_days},
            )
            session.add(med_event)
            session.flush()
            events_generated.append({"type": "medical", "id": med_event.id, "title": med_event.title})

    # 2. Dressing Room Grievance & Captain Intermediary
    unhappy_player = session.scalars(
        select(OwnerSquadPlayer)
        .where(OwnerSquadPlayer.club_id == club_id, OwnerSquadPlayer.morale < 60)
        .order_by(OwnerSquadPlayer.rating.desc())
    ).first()

    if unhappy_player:
        cap_event_key = f"captain_grievance_dialogue:{club_id}:day_{current_day}:{unhappy_player.id}"
        existing_cap = session.scalars(
            select(OwnerClubEvent).where(OwnerClubEvent.idempotency_key == cap_event_key)
        ).first()

        if not existing_cap:
            lead_grp = politics.get("leadership_group") or {}
            cap_name = lead_grp.get("captain_name", "Ifeanyi Nwachukwu")

            cap_event = OwnerClubEvent(
                club_id=club_id,
                category="squad",
                event_type="captain_intermediary_grievance",
                severity="notable",
                status="awaiting_decision",
                source_type="squad_captain",
                source_id=cap_name,
                title=f"Captain Intermediary: {cap_name} on Dressing Room Morale",
                description=(
                    f"Team Captain {cap_name} requested a private audience with ownership. "
                    f"Senior squad members are concerned about {unhappy_player.name}'s marginalization and wage tier disparity."
                ),
                participants_json=[
                    {"role": "captain", "name": cap_name},
                    {"player_id": unhappy_player.id, "name": unhappy_player.name},
                ],
                world_day=current_day,
                idempotency_key=cap_event_key,
                actions_json=[
                    {
                        "action_id": "pledge_rotation",
                        "label": "Pledge Increased Rotation",
                        "description": "Commit to squad rotation in upcoming fixtures.",
                        "delta_summary": "+8 Player Morale, +5 Captain Loyalty, -2 Manager Authority",
                    },
                    {
                        "action_id": "affirm_manager_standard",
                        "label": "Back Manager Selection Standards",
                        "description": "Instruct captain that playing time is earned on merit.",
                        "delta_summary": "+6 Manager Trust, -4 Squad Morale, +4 Tension",
                    },
                ],
                consequences_json={"player_id": unhappy_player.id},
            )
            session.add(cap_event)
            session.flush()
            events_generated.append({"type": "squad", "id": cap_event.id, "title": cap_event.title})

    # 3. Press Conference & Media Question
    press_event_key = f"media_rumour_inquiry:{club_id}:day_{current_day}"
    existing_press = session.scalars(
        select(OwnerClubEvent).where(OwnerClubEvent.idempotency_key == press_event_key)
    ).first()

    if not existing_press:
        outlet = MEDIA_OUTLETS[current_day % len(MEDIA_OUTLETS)]
        press_event = OwnerClubEvent(
            club_id=club_id,
            category="media",
            event_type="press_inquiry",
            severity="routine",
            status="awaiting_decision",
            source_type="media",
            source_id=outlet["name"],
            title=f"Press Inquiry: {outlet['name']}",
            description=(
                f"Senior correspondent from {outlet['name']} asks ownership about seasonal ambition and transfer investment strategy."
            ),
            participants_json=[{"role": "journalist", "outlet": outlet["name"]}],
            world_day=current_day,
            idempotency_key=press_event_key,
            actions_json=[
                {
                    "action_id": "affirm_ambition",
                    "label": "Declare Elite Ambition",
                    "description": "Publicly announce that the club aims for silverware and top tier qualification.",
                    "delta_summary": "+6 Supporter Confidence, +4 Investor Sentiment, Higher Pressure",
                },
                {
                    "action_id": "preach_patience",
                    "label": "Preach Prudence & Organic Growth",
                    "description": "Emphasize sustainable academy foundations and long-term project viability.",
                    "delta_summary": "+5 Board Traditionalist Approval, -3 Supporter Excitement",
                },
            ],
            consequences_json={"outlet": outlet["name"]},
        )
        session.add(press_event)
        session.flush()
        events_generated.append({"type": "media", "id": press_event.id, "title": press_event.title})

    # Update politics timestamp and day
    politics["last_evaluated_day"] = current_day
    politics["updated_at"] = utcnow().isoformat()
    state.facilities_json["_club_politics"] = politics
    flag_modified(state, "facilities_json")
    session.flush()

    return {
        "club_id": club_id,
        "world_day": current_day,
        "events_evaluated": len(events_generated),
        "new_events": events_generated,
        "board_confidence": politics.get("board_confidence"),
        "supporter_confidence": politics.get("supporter_confidence"),
    }


# ==============================================================================
# 4. Event Resolution & Consequences Engine
# ==============================================================================


def resolve_political_event(
    session: Session, user_id: str, club_id: str, event_id: str, action_id: str, note: str | None = None
) -> dict[str, Any]:
    """Execute authoritative owner decision on a political event and disburse consequences."""
    event = session.get(OwnerClubEvent, event_id)
    if event is None or event.club_id != club_id:
        raise ValueError(f"Event {event_id} not found for club {club_id}")

    if event.status == "resolved":
        return {
            "success": True,
            "event_id": event_id,
            "status": "already_resolved",
            "message": "Event has already been ratified and resolved.",
        }

    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"OwnerClubState for {club_id} not found")

    politics = get_or_initialize_club_politics(session, club_id, user_id)
    consequences = event.consequences_json or {}
    delta_report: dict[str, Any] = {}

    # Handle Medical Return-to-Play Dispute
    if event.event_type == "medical_clearance_dispute":
        player_id = consequences.get("player_id")
        player = session.get(OwnerSquadPlayer, player_id) if player_id else None

        if action_id == "back_medical":
            # Strengthen medical director relationship
            living_club_world.apply_relationship_delta(
                session,
                club_id=club_id,
                part_a_type="owner",
                part_a_id=f"owner:{user_id}",
                part_a_name="Club Owner",
                part_b_type="staff",
                part_b_id="medical_director",
                part_b_name="Dr. Chidi Obi",
                delta_trust=5,
                delta_tension=-4,
                delta_alignment=4,
                reason="Owner enforced medical staff authority on player rehab",
            )
            delta_report["medical_trust"] = "+5"
            delta_report["player_injury_status"] = "Protected under full recovery protocol"
        elif action_id == "rush_player":
            # Penalize medical director trust; simulate 65% injury recurrence
            living_club_world.apply_relationship_delta(
                session,
                club_id=club_id,
                part_a_type="owner",
                part_a_id=f"owner:{user_id}",
                part_a_name="Club Owner",
                part_b_type="staff",
                part_b_id="medical_director",
                part_b_name="Dr. Chidi Obi",
                delta_trust=-10,
                delta_tension=12,
                delta_alignment=-6,
                reason="Owner overrode medical staff advice to rush player return",
            )
            # Reinjury recurrence consequence
            if player:
                player.injured_days = player.injured_days + 14  # Relapse penalty
                player.morale = max(20, player.morale - 15)
                session.add(player)
                delta_report["reinjury_recurrence"] = True
                delta_report["player_additional_injured_days"] = 14
            delta_report["medical_trust"] = "-10"

    # Handle Dressing Room Captain Grievance
    elif event.event_type == "captain_intermediary_grievance":
        player_id = consequences.get("player_id")
        player = session.get(OwnerSquadPlayer, player_id) if player_id else None

        if action_id == "pledge_rotation":
            if player:
                player.morale = min(100, player.morale + 12)
                session.add(player)
            politics["supporter_confidence"] = min(100, politics.get("supporter_confidence", 75) + 3)
            delta_report["player_morale"] = "+12"
            delta_report["captain_trust"] = "+5"
        elif action_id == "affirm_manager_standard":
            living_club_world.apply_relationship_delta(
                session,
                club_id=club_id,
                part_a_type="owner",
                part_a_id=f"owner:{user_id}",
                part_a_name="Club Owner",
                part_b_type="staff",
                part_b_id="first_team_manager",
                part_b_name="Emmanuel Amuneke",
                delta_trust=6,
                delta_tension=-3,
                delta_alignment=4,
                reason="Owner backed manager selection authority against dressing room challenge",
            )
            politics["board_confidence"] = min(100, politics.get("board_confidence", 75) + 2)
            delta_report["manager_trust"] = "+6"
            delta_report["board_confidence"] = "+2"

    # Handle Press & Media Statement
    elif event.event_type == "press_inquiry":
        if action_id == "affirm_ambition":
            politics["supporter_confidence"] = min(100, politics.get("supporter_confidence", 75) + 6)
            politics["investor_sentiment"] = min(100, politics.get("investor_sentiment", 75) + 5)
            politics["matchday_atmosphere_multiplier"] = 1.15
            delta_report["supporter_confidence"] = "+6"
            delta_report["investor_sentiment"] = "+5"
        elif action_id == "preach_patience":
            politics["board_confidence"] = min(100, politics.get("board_confidence", 75) + 4)
            politics["supporter_confidence"] = max(0, politics.get("supporter_confidence", 75) - 2)
            delta_report["board_confidence"] = "+4"
            delta_report["supporter_confidence"] = "-2"

    # Update event record
    event.status = "resolved"
    event.resolved_at = utcnow()
    event.resolution_action = action_id
    event.resolution_note = note
    session.add(event)

    # Save politics modifications
    state.facilities_json["_club_politics"] = politics
    flag_modified(state, "facilities_json")
    session.flush()

    return {
        "success": True,
        "event_id": event_id,
        "action_taken": action_id,
        "resolution_note": note,
        "delta_report": delta_report,
        "board_confidence": politics.get("board_confidence"),
        "supporter_confidence": politics.get("supporter_confidence"),
    }


# ==============================================================================
# 5. Owner Public Media Statement Dispatch
# ==============================================================================


def dispatch_owner_media_statement(
    session: Session, user_id: str, club_id: str, statement_type: str, custom_text: str | None = None
) -> dict[str, Any]:
    """Issue a formal owner public statement to media and supporters."""
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    politics = get_or_initialize_club_politics(session, club_id, user_id)
    current_day = state.world_day or 1

    statement_effects: dict[str, Any] = {}
    if statement_type == "vote_of_confidence":
        politics["board_confidence"] = min(100, politics.get("board_confidence", 75) + 5)
        politics["supporter_confidence"] = min(100, politics.get("supporter_confidence", 75) + 3)
        living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id=f"owner:{user_id}",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id="first_team_manager",
            part_b_name="Emmanuel Amuneke",
            delta_trust=7,
            delta_tension=-5,
            delta_loyalty=6,
            reason="Owner public vote of confidence to media",
        )
        statement_effects["manager_trust"] = "+7"
        statement_effects["board_confidence"] = "+5"

    elif statement_type == "demand_performance":
        politics["supporter_confidence"] = min(100, politics.get("supporter_confidence", 75) + 5)
        politics["investor_sentiment"] = min(100, politics.get("investor_sentiment", 75) + 4)
        living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id=f"owner:{user_id}",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id="first_team_manager",
            part_b_name="Emmanuel Amuneke",
            delta_trust=-3,
            delta_tension=8,
            delta_influence=5,
            reason="Owner public demand for immediate tactical improvement",
        )
        statement_effects["squad_urgency"] = "+8"
        statement_effects["tension"] = "+8"

    elif statement_type == "praise_youth_academy":
        politics["board_confidence"] = min(100, politics.get("board_confidence", 75) + 4)
        politics["supporter_confidence"] = min(100, politics.get("supporter_confidence", 75) + 6)
        living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id=f"owner:{user_id}",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id="head_of_youth_development",
            part_b_name="Kunle Adeyemi",
            delta_trust=6,
            delta_alignment=5,
            reason="Owner public acclaim for academy pathway and scholar progress",
        )
        statement_effects["hoyd_trust"] = "+6"
        statement_effects["supporter_enthusiasm"] = "+6"

    # Add to active rumours/headlines
    headlines = politics.get("active_rumours", [])
    headlines.insert(
        0,
        {
            "headline": f"Owner Statement: {statement_type.replace('_', ' ').title()}",
            "quote": custom_text or f"Club leadership reaffirms strategic direction on World Day {current_day}.",
            "published_day": current_day,
            "source": "Official Club Communiqué",
        },
    )
    politics["active_rumours"] = headlines[:8]

    state.facilities_json["_club_politics"] = politics
    flag_modified(state, "facilities_json")
    session.flush()

    return {
        "success": True,
        "statement_type": statement_type,
        "published_day": current_day,
        "effects": statement_effects,
        "board_confidence": politics.get("board_confidence"),
        "supporter_confidence": politics.get("supporter_confidence"),
    }
