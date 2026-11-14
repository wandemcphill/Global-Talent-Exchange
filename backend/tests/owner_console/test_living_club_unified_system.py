"""End-to-end integration tests unifying Autonomous Staff & Living Club with Supporters, Media & Institutional History."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool

from app.admin_engine.service import AdminEngineService
from app.auth.dependencies import get_current_user, get_session
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.world_clock import WorldClockState
from app.owner_console import (
    autonomous_staff_engine,
    comms_persistence,
    competitions as comps,
    delegation_service,
    engine as owner_engine,
    ledger,
    living_institution,
    service,
)
from app.owner_console.institutional_models import (
    OwnerClubAcademyGraduate,
    OwnerClubHistoryEntry,
    OwnerClubManagerialTenure,
    OwnerClubTransferRecord,
    OwnerMediaStory,
    OwnerSupporterEvent,
    OwnerSupporterProfile,
)
from app.owner_console.models import (
    ClubDelegatedDecision,
    OwnerClubConversation,
    OwnerClubEvent,
    OwnerClubMeeting,
    OwnerClubMessage,
    OwnerClubRelationship,
    OwnerClubState,
    OwnerInboxItem,
    OwnerRecruitmentAssignment,
    OwnerSquadPlayer,
    OwnerStaffDecisionRecord,
)
from app.owner_console.router import router as owner_router
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)

_SHARED_ENGINE = None


def _get_shared_engine():
    global _SHARED_ENGINE
    if _SHARED_ENGINE is None:
        load_model_modules()
        _SHARED_ENGINE = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(_SHARED_ENGINE)
    return _SHARED_ENGINE


def _setup_unified_test_env(*, city: str = "Lagos", club_name: str | None = None) -> tuple[Session, TestClient, OwnerClubState]:
    eng = _get_shared_engine()
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    session = factory()

    if session.get(WorldClockState, DEFAULT_CLOCK_ID) is None:
        session.add(
            WorldClockState(
                id=DEFAULT_CLOCK_ID,
                epoch_real_utc=WORLD_NOW,
                virtual_start_time=WORLD_NOW,
                progression_rate=1.0,
                is_paused=False,
                officially_started=True,
            )
        )
        session.flush()

    AdminEngineService(session).seed_defaults()

    uid = uuid4().hex[:8]
    owner_id = f"owner-{uid}"
    club_id = f"club-{uid}"
    owner = User(
        id=owner_id,
        email=f"owner-{uid}@gtex.test",
        username=f"owner_{uid}",
        display_name="Club Owner",
        password_hash="not-used-in-test",
        role=UserRole.USER,
        kyc_status=KycStatus.VERIFIED,
        account_type=PublicAccountType.USER,
        nationality="Nigeria",
        is_active=True,
    )
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner.id,
        club_name=club_name or f"Atlantic United {uid}",
        short_name="AUFC",
        slug=f"atlantic-united-{uid}",
        club_type=ClubType.PROFESSIONAL,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#10B981",
        secondary_color="#0F172A",
        accent_color="#F59E0B",
        country_code="NG",
        visibility="public",
    )
    state = OwnerClubState(
        club_id=club.id,
        owner_user_id=owner.id,
        club_name=club.club_name,
        stage="active",
        world_day=10,
        prestige=74,
        fans=18000,
        mentality="balanced",
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 3, "academy": 4, "medical": 3, "stadium": 3, "commercial": 3},
    )
    session.add_all([owner, club, state])
    session.flush()

    ledger.record(
        session,
        event_type="test_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club.id),
        currency=ledger.GTEX,
        gross=850000,
        balance_class="deposited",
        club_id=club.id,
        user_id=owner.id,
        memo="Initial club treasury",
    )
    ledger.record(
        session,
        event_type="test_fan_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.user_account(owner.id),
        currency=ledger.FAN,
        gross=50000,
        club_id=club.id,
        user_id=owner.id,
        memo="Initial fan coin",
    )

    squad_spec = [
        ("p-gk-1", "Emeka Obi", "Goalkeeper", 28, 79, 80, False),
        ("p-gk-2", "Tariq Bello", "Goalkeeper", 21, 71, 79, False),
        ("p-def-1", "Chidi Nwachukwu", "CB", 29, 80, 80, False),
        ("p-def-2", "Kofi Mensah", "CB", 27, 78, 79, False),
        ("p-def-3", "Seyi Balogun", "LB", 25, 77, 80, False),
        ("p-def-4", "Ibrahim Diallo", "RB", 26, 77, 79, False),
        ("p-def-5", "Dapo Afolabi", "CB", 22, 73, 81, False),
        ("p-mid-1", "Yusuf Lawal", "CM", 28, 81, 82, False),
        ("p-mid-2", "Nuno Silva", "CDM", 30, 79, 79, False),
        ("p-mid-3", "Tobi Ojo", "CAM", 24, 78, 83, False),
        ("p-mid-4", "Chuka Eze", "CM", 22, 76, 81, False),
        ("p-mid-5", "Akin Cole", "RM", 26, 76, 78, False),
        ("p-fwd-1", "Victor Okafor", "ST", 29, 82, 82, False),
        ("p-fwd-2", "Samuel Kalu", "LW", 27, 78, 79, False),
        ("p-fwd-3", "Musa Danjuma", "RW", 26, 77, 79, False),
        ("p-gk-3", "Kunle Ade", "Goalkeeper", 26, 74, 76, False),
        ("p-def-6", "Bola Musa", "LB", 25, 75, 77, False),
        ("p-def-7", "Sadiq Umar", "RB", 26, 75, 77, False),
        ("p-mid-6", "Femi Ajayi", "CDM", 27, 76, 78, False),
        ("p-mid-7", "Oluwatobi Dada", "CM", 25, 75, 78, False),
        ("p-fwd-4", "Kelechi Osuji", "ST", 25, 76, 79, False),
        ("p-acad-st-16", "Lucas Vance", "ST", 16, 67, 89, True),
    ]
    for pid_base, name, pos, age, rtg, pot, is_regen in squad_spec:
        session.add(
            OwnerSquadPlayer(
                id=f"{club.id}:{pid_base}",
                club_id=club.id,
                name=name,
                position=pos,
                age=age,
                rating=rtg,
                potential=pot,
                value_coin=Decimal(str(rtg * 15)),
                morale=80,
                minutes=180 if not is_regen else 15,
                injured_days=0,
                is_regen=is_regen,
                personality_json={"fitness": 94, "is_academy": is_regen, "ambition": 16, "professionalism": 15},
                status="active",
                acquired_via="academy" if is_regen else "market",
            )
        )

    living_institution.ensure_club_institutional_ecosystem(session, state)
    comms_persistence.ensure_club_conversations_seeded(session, state)
    session.commit()

    app = FastAPI()
    app.include_router(owner_router)

    def _override_session() -> Iterator[Session]:
        yield session

    def _override_user() -> User:
        return session.get(User, owner_id)

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    client = TestClient(app)
    return session, client, state


def _assign_manager_archetype(session: Session, state: OwnerClubState, archetype_key: str) -> dict:
    mgr_template = dict(autonomous_staff_engine.MANAGER_ARCHETYPES[archetype_key])
    names = {
        "youth_development_visionary": "Marco Bellini",
        "veteran_pragmatist": "Viktor Krall",
        "balanced_collaborator": "Julian Vance",
        "high_pressing_autocrat": "Lukas Richter",
        "possession_architect": "Mateo Alcaraz",
    }
    mgr_name = names.get(archetype_key, mgr_template["archetype_label"])
    mgr_json = {
        "id": f"mgr_{archetype_key}",
        "manager_id": f"mgr_{archetype_key}",
        "name": mgr_name,
        "display_name": mgr_name,
        "archetype_key": archetype_key,
        "mood": 78,
        "loyalty": mgr_template["loyalty"] // 5,
        "youth_development": max(5, mgr_template["youth_development_commitment"] // 5),
        "tactical_flexibility": max(5, mgr_template["tactical_flexibility"] // 5),
        "personality_profile": dict(mgr_template),
    }
    state.manager_json = mgr_json
    flag_modified(state, "manager_json")
    fac = dict(state.facilities_json or {})
    fac.pop("_manager_matchday_commitments", None)
    fac.pop("_manager_matchday_rejections", None)
    state.facilities_json = fac
    flag_modified(state, "facilities_json")
    session.commit()
    return mgr_json


def _seed_second_club(session: Session) -> OwnerClubState:
    uid = uuid4().hex[:8]
    opp_owner = User(
        id=f"opp-owner-{uid}",
        email=f"opp-owner-{uid}@gtex.test",
        username=f"opp_owner_{uid}",
        display_name="Opponent Club Owner",
        password_hash="not-used-in-test",
        role=UserRole.USER,
        kyc_status=KycStatus.VERIFIED,
        account_type=PublicAccountType.USER,
        nationality="Nigeria",
        is_active=True,
    )
    opp_id = f"opp-{uid}"
    opp_club = ClubProfile(
        id=opp_id,
        owner_user_id=opp_owner.id,
        club_name=f"Kano Rivals {uid}",
        short_name="KRFC",
        slug=f"kano-rivals-{uid}",
        club_type=ClubType.PROFESSIONAL,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        primary_color="#EF4444",
        secondary_color="#111827",
        accent_color="#FBBF24",
        country_code="NG",
        visibility="public",
    )
    opp_state = OwnerClubState(
        club_id=opp_club.id,
        owner_user_id=opp_owner.id,
        club_name=opp_club.club_name,
        stage="active",
        world_day=10,
        prestige=70,
        fans=14000,
        mentality="balanced",
        manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
        facilities_json={"training": 3, "academy": 3, "medical": 3, "stadium": 3, "commercial": 3},
    )
    session.add_all([opp_owner, opp_club, opp_state])
    session.flush()
    positions = [
        "Goalkeeper", "Goalkeeper", "Goalkeeper",
        "CB", "CB", "CB", "CB", "LB", "LB", "RB", "RB",
        "CM", "CM", "CDM", "CDM", "CAM", "RM", "LM",
        "ST", "ST", "LW", "RW",
    ]
    for i, pos in enumerate(positions, start=1):
        session.add(
            OwnerSquadPlayer(
                id=f"{opp_id}:p-{i}",
                club_id=opp_id,
                name=f"Opponent Player {i}",
                position=pos,
                age=25,
                rating=74,
                potential=78,
                value_coin=Decimal("800"),
                morale=76,
                minutes=180,
                injured_days=0,
                is_regen=False,
                personality_json={"fitness": 90, "is_academy": False},
                status="active",
                acquired_via="market",
            )
        )
    living_institution.ensure_club_institutional_ecosystem(session, opp_state)
    session.commit()
    return opp_state


def test_single_authoritative_world_clock_ordering_and_idempotency() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        # Inject active supporter protest before the tick so same-tick staff intelligence reacts to reconciled sentiment
        prof = session.scalar(select(OwnerSupporterProfile).where(OwnerSupporterProfile.club_id == state.club_id))
        assert prof is not None
        prof.overall_sentiment = 29
        prof.accumulated_frustration = 44
        prof.active_protest_stage = "banner_protest"
        prof.matchday_experience_rating = 42
        session.commit()

        prev_day = int(state.world_day or 0)
        res = service.tick_club(session, state, use_ai=False)
        session.commit()

        assert res["world_day"] == prev_day + 1
        assert "living_world" in res
        assert "institutional_ecosystem" in res
        assert "reputation_dimensions" in res

        # Idempotent replay guard on institutional world tick for the exact same world_day
        replay = living_institution.process_world_day_institutional_tick(session, state)
        session.commit()
        assert replay.get("already_reconciled") is True

        # Same-tick proactive staff communication reacts to supporter banner protest
        staff_msgs = list(
            session.scalars(
                select(OwnerClubMessage).where(OwnerClubMessage.club_id == state.club_id)
            ).all()
        )
        assert any(
            "protest" in (m.topic or "").lower()
            or "supporter" in (m.topic or "").lower()
            or "protest" in (m.body or "").lower()
            for m in staff_msgs
        )

        # Unified pulse endpoint reflects reconciled clock + sentiment + reputation dimensions
        pulse_res = client.get(f"/owner/clubs/{state.club_id}/institutional-pulse")
        assert pulse_res.status_code == 200, pulse_res.text
        pulse = pulse_res.json()
        assert pulse["club_id"] == state.club_id
        assert len(pulse["reputation_dimensions"]) >= 9
        assert pulse["supporters"]["active_protest_stage"] in ("banner_protest", "organised_boycott")
    finally:
        session.close()


def test_confidentiality_boundaries_and_delayed_public_youth_scrutiny() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        owner = session.get(User, state.owner_user_id)
        assert owner is not None
        opp = _seed_second_club(session)

        # Direct confidentiality enforcement on supporter reaction and media publication
        private_sup = living_institution.apply_supporter_reaction(
            session,
            state,
            event_type="internal_tactical_dispute",
            trigger_source_type="staff_chat",
            trigger_source_id="priv-1",
            headline="Private internal tactical talk",
            summary="Should never leak without public signal.",
            driver_Impacts={"results": 0.0},
            visibility_classification=living_institution.VISIBILITY_PRIVATE_INTERNAL,
            has_public_signal=False,
            is_official_disclosure=False,
            idempotency_key="priv-sup-guard-1",
        )
        restricted_media = living_institution.publish_media_story(
            session,
            state,
            outlet_key="local_club_chronicle",
            story_type="boardroom_note",
            classification="verified_event",
            headline="Restricted executive note",
            subheadline="Internal executive only",
            body="Should remain strictly confidential.",
            source_type="boardroom",
            source_id="priv-media-1",
            visibility_classification=living_institution.VISIBILITY_RESTRICTED_EXECUTIVE,
            has_public_signal=False,
            is_official_disclosure=False,
            idempotency_key="priv-media-guard-1",
            enforce_grounding=False,
        )
        assert private_sup is None
        assert restricted_media is None

        # Conservative manager declines playing 16yo Lucas Vance in private staff conversation
        _assign_manager_archetype(session, state, "veteran_pragmatist")
        res = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:first_team_manager",
                "message": "Give 16-year-old academy striker Lucas Vance his debut in the next match.",
                "topic": "Academy Opportunity",
            },
        )
        assert res.status_code == 200, res.text
        assert res.json()["decision_record"]["decision_outcome"] == "declined"

        # Immediately after the private disagreement: canonical event must be private_internal, and ZERO public leak!
        all_club_events = list(
            session.scalars(select(OwnerClubEvent).where(OwnerClubEvent.club_id == state.club_id)).all()
        )
        private_events = [
            ev
            for ev in all_club_events
            if (ev.consequences_json or {}).get("visibility_classification") == "private_internal"
        ]
        assert len(private_events) >= 1

        leaked_sup = list(
            session.scalars(
                select(OwnerSupporterEvent).where(
                    OwnerSupporterEvent.club_id == state.club_id,
                    OwnerSupporterEvent.event_type == "youth_pathway_neglect",
                )
            ).all()
        )
        leaked_media = list(
            session.scalars(
                select(OwnerMediaStory).where(
                    OwnerMediaStory.club_id == state.club_id,
                    OwnerMediaStory.outlet_key == "tactical_youth_observer",
                )
            ).all()
        )
        assert leaked_sup == []
        assert leaked_media == []

        # Play an official match with zero academy appearances -> public team-sheet signal now surfaces scrutiny
        comp = comps.host_competition(
            session,
            state.owner_user_id,
            {
                "name": "National Cup Showcase",
                "format": "league",
                "max_clubs": 2,
                "contribution": 0,
                "winner_prize": 0,
                "club_id": state.club_id,
            },
        )
        comps.enter_competition(session, state.owner_user_id, comp.id, state.club_id)
        comps.enter_competition(session, opp.owner_user_id, comp.id, opp.club_id)
        comps.play_next(session, state.owner_user_id, comp.id, state.club_id, "balanced", "strongest")
        session.commit()

        youth_neglect_events = list(
            session.scalars(
                select(OwnerSupporterEvent).where(
                    OwnerSupporterEvent.club_id == state.club_id,
                    OwnerSupporterEvent.event_type == "youth_pathway_neglect",
                )
            ).all()
        )
        youth_opinion_stories = list(
            session.scalars(
                select(OwnerMediaStory).where(
                    OwnerMediaStory.club_id == state.club_id,
                    OwnerMediaStory.outlet_key == "tactical_youth_observer",
                )
            ).all()
        )
        assert len(youth_neglect_events) >= 1
        assert len(youth_opinion_stories) >= 1
        # Media story must comment only on public matchday omission, never private staff chat text
        assert "Give 16-year-old academy striker Lucas Vance" not in youth_opinion_stories[0].body
    finally:
        session.close()


def test_manager_resignation_single_canonical_event_and_projections() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        _assign_manager_archetype(session, state, "high_pressing_autocrat")

        # Baseline resignation count before owner interference
        initial_resign = list(
            session.scalars(
                select(OwnerClubEvent).where(
                    OwnerClubEvent.club_id == state.club_id,
                    OwnerClubEvent.event_type.in_(["staff_resigned", "manager_resignation"]),
                )
            ).all()
        )
        assert initial_resign == []

        prompts = [
            "Drop Victor Okafor and start Lucas Vance right now for the next match.",
            "I insist you start Lucas Vance up front instead of Okafor immediately.",
            "Override your tactical plan and play Lucas Vance from kick-off.",
            "As owner I order you to start Lucas Vance regardless of your objections.",
            "Change your starting eleven immediately and start Lucas Vance up front.",
            "Refuse my lineup instruction at your peril: Lucas Vance must start next match.",
            "Put Lucas Vance in the starting XI right now over your senior strikers.",
        ]
        resigned = False
        for i, msg in enumerate(prompts, start=1):
            r = client.post(
                f"/owner/clubs/{state.club_id}/communications/messages",
                json={"thread_id": "staff:first_team_manager", "message": msg, "topic": f"Lineup Mandate {i}"},
            )
            assert r.status_code == 200, r.text
            payload = r.json()
            if (
                payload.get("resignation_notice_served")
                or (payload.get("decision_record") or {}).get("decision_outcome") == "resignation_notice"
                or (payload.get("relationship") or {}).get("resignation_notice_served")
            ):
                resigned = True
                break

        assert resigned is True

        # Must create ONE canonical resignation event linked cleanly across tenure, supporter, media & history
        resign_events = list(
            session.scalars(
                select(OwnerClubEvent).where(
                    OwnerClubEvent.club_id == state.club_id,
                    OwnerClubEvent.event_type.in_(["manager_resigned", "staff_resigned", "manager_resignation"]),
                )
            ).all()
        )
        assert len(resign_events) == 1
        canonical = resign_events[0]

        tenures = list(
            session.scalars(
                select(OwnerClubManagerialTenure).where(
                    OwnerClubManagerialTenure.club_id == state.club_id,
                    OwnerClubManagerialTenure.role == "first_team_manager",
                )
            ).all()
        )
        assert len(tenures) >= 2
        assert any(t.departure_reason and "resign" in t.departure_reason.lower() for t in tenures)

        projections = list((canonical.consequences_json or {}).get("projections_applied") or [])
        sup_projs = [p for p in projections if p.get("subsystem") == "supporters"]
        media_projs = [p for p in projections if p.get("subsystem") == "media"]
        hist_projs = [
            p for p in projections if p.get("subsystem") == "club_history" and p.get("record_type") == "OwnerClubHistoryEntry"
        ]
        assert len(sup_projs) == 1
        assert len(media_projs) == 1
        assert len(hist_projs) == 1
        assert session.get(OwnerSupporterEvent, sup_projs[0]["record_id"]) is not None
        assert session.get(OwnerMediaStory, media_projs[0]["record_id"]) is not None
        assert session.get(OwnerClubHistoryEntry, hist_projs[0]["record_id"]) is not None

        # Proportional reaction: single managerial exit should not jump directly to organised_boycott from healthy baseline
        prof = session.scalar(select(OwnerSupporterProfile).where(OwnerSupporterProfile.club_id == state.club_id))
        assert prof is not None
        assert prof.active_protest_stage != "organised_boycott"

        # Unified pulse & story timeline correlate the projections under the canonical event
        pulse = client.get(f"/owner/clubs/{state.club_id}/institutional-pulse").json()
        assert any(item["canonical_event_id"] == canonical.id for item in pulse["unified_timeline"])
    finally:
        session.close()


def test_supporter_protest_triggers_staff_alerts_and_conditional_boardroom_resolution() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        # 1. Baseline calm club boardroom meeting preserves standard 3 resolutions
        calm_mtg = autonomous_staff_engine.simulate_boardroom_meeting_negotiation(
            session,
            state,
            title="Routine Technical Alignment",
            agenda="Review squad balance for the month ahead.",
            meeting_type="general_strategy",
        )
        assert len(calm_mtg["proposed_resolutions"]) == 3

        # 2. Active ticket/protest pressure injects supporter intelligence + conditional boardroom reset option
        prof = session.scalar(select(OwnerSupporterProfile).where(OwnerSupporterProfile.club_id == state.club_id))
        assert prof is not None
        prof.overall_sentiment = 26
        prof.accumulated_frustration = 52
        prof.active_protest_stage = "banner_protest"
        prof.ticket_price_tier = "exploitative"
        session.commit()

        initiatives = autonomous_staff_engine.generate_proactive_staff_initiatives(
            session,
            state,
            owner_user_id=state.owner_user_id,
            trigger_reason="world_tick_check",
        )
        session.commit()

        initiative_topics = [str(item.get("topic") or "").lower() for item in initiatives]
        assert any("supporter" in t or "protest" in t or "ticket" in t for t in initiative_topics)

        crisis_mtg = autonomous_staff_engine.simulate_boardroom_meeting_negotiation(
            session,
            state,
            title="Emergency Supporter & Matchday Trust Summit",
            agenda="Address banner protests and matchday ticket unrest across the fanbase.",
            meeting_type="supporter_crisis",
        )
        res_ids = [r["resolution_id"] for r in crisis_mtg["proposed_resolutions"]]
        assert "supporter_trust_and_pricing_reset" in res_ids

        meeting_row = OwnerClubMeeting(
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            title="Emergency Supporter & Matchday Trust Summit",
            agenda="Address banner protests and matchday ticket unrest across the fanbase.",
            meeting_type="supporter_crisis",
            world_day=state.world_day,
            status="open",
            metadata_json={"proposed_resolutions": crisis_mtg["proposed_resolutions"]},
        )
        session.add(meeting_row)
        session.flush()

        outcome = autonomous_staff_engine.resolve_boardroom_meeting_decision(
            session,
            state,
            meeting_row,
            resolution_id="supporter_trust_and_pricing_reset",
            owner_note="Restore affordable matchday access immediately.",
        )
        session.commit()

        assert outcome["chosen_resolution"]["resolution_id"] == "supporter_trust_and_pricing_reset"
        session.refresh(prof)
        assert prof.ticket_price_tier != "exploitative"

        boardroom_events = [
            ev
            for ev in session.scalars(select(OwnerClubEvent).where(OwnerClubEvent.club_id == state.club_id)).all()
            if (ev.consequences_json or {}).get("visibility_classification") == "restricted_executive"
        ]
        assert len(boardroom_events) >= 1
    finally:
        session.close()


def test_complete_recruitment_signing_and_insufficient_funds_block() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        # Hire GM and Chief Scout so recruitment workflow uses persistent executives
        service.hire_executive_staff(session, state.owner_user_id, state.club_id, "gm_grassroots_dayo", role="general_manager")
        service.hire_executive_staff(session, state.owner_user_id, state.club_id, "scout_kelechi_nwosu", role="chief_scout")
        session.commit()

        workflow = autonomous_staff_engine.execute_inter_staff_recruitment_workflow(
            session,
            state,
            initiated_by_role="general_manager",
            initiated_by_name="Dayo Adeleke",
            target_position="CM",
            min_gsi=75,
            max_gsi=84,
            gm_verdict="approved",
            estimated_fee=25000,
            estimated_weekly_wage=320,
        )
        session.commit()
        assignment_id = workflow.id
        assignment = session.get(OwnerRecruitmentAssignment, assignment_id)
        assert assignment is not None

        # Drain club treasury below fee to test insufficient funds block (no phantom signing or ledger corruption)
        bal = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
        if bal > 5000:
            ledger.record(
                session,
                event_type="test_escrow_hold",
                source=ledger.club_account(state.club_id),
                destination=ledger.WORLD_CLUBS,
                currency=ledger.GTEX,
                gross=bal - Decimal("5000"),
                club_id=state.club_id,
                user_id=state.owner_user_id,
                memo="Temporarily reduce liquid funds",
            )
            session.commit()

        initial_squad_count = len(
            list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all())
        )
        blocked_res = client.post(
            f"/owner/clubs/{state.club_id}/recruitment/{assignment_id}/execute",
            json={},
        )
        session.refresh(assignment)
        if blocked_res.status_code == 200:
            assert blocked_res.json().get("executed") is False
        else:
            assert blocked_res.status_code in (400, 409)
        assert assignment.gm_evaluation_status == "failed_insufficient_funds"
        assert (
            len(list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()))
            == initial_squad_count
        )

        # Replenish treasury and complete signing via Owner Delegated Decision approval
        ledger.record(
            session,
            event_type="owner_capital_injection",
            source=ledger.WORLD_CLUBS,
            destination=ledger.club_account(state.club_id),
            currency=ledger.GTEX,
            gross=200000,
            balance_class="deposited",
            club_id=state.club_id,
            user_id=state.owner_user_id,
            memo="Replenish transfer funds",
        )
        assignment.gm_evaluation_status = "shortlisted"
        decision = ClubDelegatedDecision(
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            activity_key="recruitment_signing",
            domain="recruitment",
            proposed_by_role="general_manager",
            proposed_by_staff_name="Dayo Adeleke",
            title="Approve Shortlisted Midfield Signing",
            summary="Authorize signing of Chief Scout shortlist candidate.",
            financial_amount_gtex=Decimal("25000"),
            requires_owner_approval=True,
            status="pending_approval",
            payload_json={"assignment_id": assignment_id},
        )
        session.add(decision)
        session.flush()
        assignment.delegated_decision_id = decision.id
        session.commit()

        bal_before = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
        resolved = delegation_service.resolve_delegated_decision(
            session,
            state.club_id,
            state.owner_user_id,
            decision.id,
            "approve",
            "Complete the midfield signing.",
        )
        session.commit()
        session.refresh(assignment)

        assert resolved.status == "approved"
        assert resolved.execution_status == "executed"
        assert assignment.gm_evaluation_status == "signed_to_first_team"
        bal_after = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
        assert bal_after < bal_before

        squad_after = list(
            session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
        )
        assert len(squad_after) == initial_squad_count + 1

        transfers = list(
            session.scalars(
                select(OwnerClubTransferRecord).where(
                    OwnerClubTransferRecord.club_id == state.club_id,
                    OwnerClubTransferRecord.direction == "arrival",
                )
            ).all()
        )
        assert len(transfers) >= 1
    finally:
        session.close()


def test_academy_bench_substitute_debut_and_minutes() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        owner = session.get(User, state.owner_user_id)
        assert owner is not None
        opp = _seed_second_club(session)

        _assign_manager_archetype(session, state, "balanced_collaborator")
        acad = session.get(OwnerSquadPlayer, f"{state.club_id}:p-acad-st-16")
        assert acad is not None
        acad.minutes = 0
        session.commit()

        res = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:first_team_manager",
                "message": "I want our 16-year-old academy striker Lucas Vance to start the next match and lead the attack.",
                "topic": "Academy Sub Appearance",
            },
        )
        assert res.status_code == 200, res.text
        assert res.json()["decision_record"]["decision_outcome"] == "partially_accepted"

        squad = list(
            session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
        )
        strength = owner_engine.club_strength(
            [service.player_dict(p) for p in squad],
            state.manager_json or {},
            state.facilities_json or {},
        )
        assert acad.id in strength["promised_sub_ids"]

        comp = comps.host_competition(
            session,
            state.owner_user_id,
            {
                "name": "Academy Bench Debut League",
                "format": "league",
                "max_clubs": 2,
                "contribution": 0,
                "winner_prize": 0,
                "club_id": state.club_id,
            },
        )
        comps.enter_competition(session, state.owner_user_id, comp.id, state.club_id)
        comps.enter_competition(session, opp.owner_user_id, comp.id, opp.club_id)
        comps.play_next(session, state.owner_user_id, comp.id, state.club_id, "balanced", "strongest")
        session.commit()

        session.refresh(acad)
        assert acad.minutes == 25

        grads = list(
            session.scalars(
                select(OwnerClubAcademyGraduate).where(
                    OwnerClubAcademyGraduate.club_id == state.club_id,
                    OwnerClubAcademyGraduate.player_id == acad.id,
                )
            ).all()
        )
        assert len(grads) >= 1
        assert grads[0].first_team_appearances >= 1
    finally:
        session.close()


def test_reputation_reconciliation_press_conference_and_staff_thread_rotation() -> None:
    session, client, state = _setup_unified_test_env()
    try:
        # 1. Nine-dimension reputation reconciliation + press conference unified propagation
        pc_res = service.conduct_press_conference(
            session,
            state.owner_user_id,
            state.club_id,
            "ambitious",
            "We are committed to championship standards and sustainable academy integration.",
        )
        session.commit()
        assert pc_res["club_id"] == state.club_id
        assert pc_res["tone"] == "flex_ambition"

        pc_canonical = list(
            session.scalars(
                select(OwnerClubEvent).where(
                    OwnerClubEvent.club_id == state.club_id,
                    OwnerClubEvent.event_type == "press_conference",
                )
            ).all()
        )
        assert len(pc_canonical) >= 1
        assert any(
            s.source_id == pc_canonical[-1].id
            for s in session.scalars(select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)).all()
        )

        pulse = client.get(f"/owner/clubs/{state.club_id}/institutional-pulse").json()
        assert len(pulse["reputation_dimensions"]) >= 9
        story = client.get(f"/owner/clubs/{state.club_id}/story").json()
        assert len(story["reputation_dimensions"]) >= 9
        assert "unified_timeline" in story

        # 2. Executive & Manager hire/dismissal tracks tenures and rotates direct threads cleanly
        service.hire_executive_staff(session, state.owner_user_id, state.club_id, "gm_grassroots_dayo", role="general_manager")
        session.commit()
        msg_1 = client.post(
            f"/owner/clubs/{state.club_id}/communications/messages",
            json={
                "thread_id": "staff:general_manager",
                "message": "CONFIDENTIAL LEGACY NOTE FOR DAYO ONLY: focus on domestic gems.",
                "topic": "GM Strategy",
            },
        )
        assert msg_1.status_code == 200, msg_1.text

        service.fire_executive_staff(session, state.owner_user_id, state.club_id, "general_manager")
        service.hire_executive_staff(session, state.owner_user_id, state.club_id, "gm_paul_mitchell", role="general_manager")
        session.commit()

        gm_tenures = list(
            session.scalars(
                select(OwnerClubManagerialTenure).where(
                    OwnerClubManagerialTenure.club_id == state.club_id,
                    OwnerClubManagerialTenure.role == "general_manager",
                )
            ).all()
        )
        assert len(gm_tenures) == 2
        assert sum(1 for t in gm_tenures if t.status == "active") == 1

        # Fresh active GM conversation thread must not expose predecessor's private messages
        comms = client.get(f"/owner/clubs/{state.club_id}/communications").json()
        gm_threads = [
            t
            for t in comms["direct_threads"]
            if t.get("participant_role") == "general_manager" or t.get("thread_key") == "staff:general_manager"
        ]
        assert len(gm_threads) == 1
        assert gm_threads[0]["participant_name"] == "Paul Mitchell"
        assert all("CONFIDENTIAL LEGACY NOTE FOR DAYO ONLY" not in m["body"] for m in gm_threads[0]["messages"])
    finally:
        session.close()
