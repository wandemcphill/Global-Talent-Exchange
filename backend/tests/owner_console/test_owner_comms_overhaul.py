from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.core.database import load_model_modules
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.community_social import CommunityPost
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.models.world_clock import WorldClockState
from app.owner_console import comms_persistence, engine as owner_engine, ledger
from app.owner_console.models import (
    OwnerClubAnnouncement,
    OwnerClubConversation,
    OwnerClubMeeting,
    OwnerClubMessage,
    OwnerClubState,
    OwnerInboxItem,
    OwnerSquadPlayer,
)
from app.owner_console.router import router as owner_router
from app.services.world_clock_service import DEFAULT_CLOCK_ID

WORLD_NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def _setup_session() -> tuple[Session, dict[str, str], TestClient]:
    load_model_modules()
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
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
    owner = User(
        id="owner-u1",
        email="owner1@gtex.test",
        username="owner_u1",
        display_name="Chief Owner Ade",
        password_hash="x",
        role=UserRole.USER,
        account_type=PublicAccountType.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    intruder = User(
        id="intruder-u2",
        email="intruder2@gtex.test",
        username="intruder_u2",
        display_name="Rival Owner",
        password_hash="x",
        role=UserRole.USER,
        account_type=PublicAccountType.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    club = ClubProfile(
        id="club-o1",
        owner_user_id=owner.id,
        club_name="Eko Royals FC",
        short_name="ERFC",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug="eko-royals-fc",
        primary_color="#00C991",
        secondary_color="#0E1A2C",
        accent_color="#E5B63F",
        country_code="NG",
        visibility="public",
    )
    club2 = ClubProfile(
        id="club-o2",
        owner_user_id=owner.id,
        club_name="Kano Pillars United",
        short_name="KPU",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug="kano-pillars-united",
        primary_color="#E5B63F",
        secondary_color="#111827",
        accent_color="#00C991",
        country_code="NG",
        visibility="public",
    )
    session.add_all([owner, intruder, club, club2])
    session.flush()
    for cid, name in (("club-o1", "Eko Royals FC"), ("club-o2", "Kano Pillars United")):
        session.add(
            OwnerClubState(
                club_id=cid,
                owner_user_id=owner.id,
                club_name=name,
                stage="active",
                prestige=68,
                manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
                facilities_json={"training": 2, "academy": 3, "medical": 2, "stadium": 2, "commercial": 2},
                world_day=15,
                last_tick_at=WORLD_NOW,
                last_world_tick_date=WORLD_NOW.date(),
                value_history_json=[],
            )
        )
        ledger.record(
            session,
            event_type="club_launch_grant",
            source=ledger.WORLD_CLUBS,
            destination=ledger.club_account(cid),
            currency=ledger.GTEX,
            gross=Decimal(50_000),
            club_id=cid,
            user_id=owner.id,
            memo="Seed grant",
        )
    session.commit()

    actor_state = {"id": owner.id}
    app = FastAPI()
    app.include_router(owner_router)

    def _override_session() -> Iterator[Session]:
        yield session

    def _override_user() -> User:
        u = session.get(User, actor_state["id"])
        assert u is not None
        return u

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user] = _override_user
    client = TestClient(app)
    return session, actor_state, client


def test_legacy_facilities_json_backfill_is_idempotent_and_untruncated() -> None:
    session, _, _ = _setup_session()
    try:
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == "club-o1"))
        assert state is not None
        legacy_msgs = [
            {
                "id": f"old_m_{i}",
                "sender_name": "Club Owner" if i % 2 == 0 else "General Manager",
                "sender_role": "Club Owner" if i % 2 == 0 else "General Manager",
                "topic": "Legacy Operations",
                "body": f"Legacy durable message #{i}",
                "created_at": WORLD_NOW.isoformat(),
            }
            for i in range(55)
        ]
        facs = dict(state.facilities_json or {})
        facs["_club_threads"] = {
            "staff:general_manager": {
                "thread_id": "staff:general_manager",
                "participant_type": "staff",
                "participant_id": "staff:general_manager",
                "participant_name": "Dayo Adeleke",
                "participant_role": "General Manager",
                "messages": legacy_msgs,
            }
        }
        facs["_club_meetings"] = [
            {
                "meeting_id": "mtg_legacy_1",
                "title": "Legacy Boardroom Session",
                "status": "completed",
                "minutes": [
                    {"speaker": "GM", "role": "General Manager", "summary": "Item 1"},
                    {"speaker": "Coach", "role": "First-Team Manager", "summary": "Item 2"},
                    {"speaker": "HOYD", "role": "Head of Youth Development", "summary": "Item 3"},
                ],
                "outcome_summary": "Ratified legacy agenda.",
                "created_at": WORLD_NOW.isoformat(),
            }
        ]
        facs["_club_announcements"] = [
            {
                "announcement_id": "ann_legacy_1",
                "title": "Legacy Academy Charter",
                "body": "Preserved legacy communiqué.",
                "audience": "all_club",
                "world_day": 14,
                "created_at": WORLD_NOW.isoformat(),
            }
        ]
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.commit()

        migrated_first = comms_persistence.backfill_legacy_club_communications(session, state)
        session.commit()
        assert migrated_first >= 57

        # Re-running must insert zero duplicates
        conv = session.scalar(
            select(OwnerClubConversation).where(
                OwnerClubConversation.club_id == "club-o1",
                OwnerClubConversation.thread_key == "staff:general_manager",
            )
        )
        assert conv is not None
        count_before = session.query(OwnerClubMessage).filter(OwnerClubMessage.conversation_id == conv.id).count()
        assert count_before == 55

        comms_persistence.backfill_legacy_club_communications(session, state)
        session.commit()
        count_after = session.query(OwnerClubMessage).filter(OwnerClubMessage.conversation_id == conv.id).count()
        assert count_after == 55
        assert session.query(OwnerClubMeeting).filter(OwnerClubMeeting.club_id == "club-o1").count() == 1
        assert session.query(OwnerClubAnnouncement).filter(OwnerClubAnnouncement.club_id == "club-o1").count() == 1
    finally:
        session.close()


def test_server_enforced_owner_identity_and_non_owner_isolation() -> None:
    session, actor_state, client = _setup_session()
    try:
        # Spoofing sender_role='manager' over HTTP still records verified Club Owner identity
        res = client.post(
            "/owner/clubs/club-o1/communications/messages",
            json={
                "thread_id": "staff:general_manager",
                "message": "Review ticket pricing ahead of the weekend home game.",
                "sender_role": "manager",
                "topic": "Operations",
                "priority": "high",
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["communications"]["owner_authority"]["verified_role"] == "Club Owner"
        assert body["communications"]["owner_authority"]["can_speak_as_staff"] is False
        sent_msg = body["message"]
        assert sent_msg["sender_type"] == "owner"
        assert sent_msg["sender_role"] == "Club Owner"
        assert sent_msg["sender_user_id"] == "owner-u1"

        conv_id = body["thread_id"]

        # Intruder is rejected across all private communications endpoints
        actor_state["id"] = "intruder-u2"
        for fn in (
            lambda: client.get("/owner/clubs/club-o1/communications"),
            lambda: client.get(f"/owner/clubs/club-o1/communications/threads/{conv_id}/messages"),
            lambda: client.post(f"/owner/clubs/club-o1/communications/threads/{conv_id}/read"),
            lambda: client.post(f"/owner/clubs/club-o1/communications/threads/{conv_id}/archive?archived=true"),
            lambda: client.post(
                "/owner/clubs/club-o1/communications/messages",
                json={"thread_id": "staff:general_manager", "message": "Hijack attempt"},
            ),
            lambda: client.post(
                "/owner/clubs/club-o1/communications/meetings",
                json={"title": "Unauthorized Briefing", "meeting_type": "boardroom"},
            ),
            lambda: client.post(
                "/owner/clubs/club-o1/communications/announcements",
                json={"title": "Unauthorized", "body": "Spoofed notice", "audience": "all_club"},
            ),
        ):
            r = fn()
            assert r.status_code in (403, 404), r.text
    finally:
        session.close()


def test_living_comms_pagination_read_archive_search_and_summary() -> None:
    session, _, client = _setup_session()
    try:
        injured = OwnerSquadPlayer(
            id="sq-p1",
            club_id="club-o1",
            name="Chinedu Okafor",
            position="ST",
            age=22,
            rating=76,
            potential=83,
            morale=38,
            injured_days=6,
            is_regen=True,
            minutes=45,
        )
        decision = OwnerInboxItem(
            user_id="owner-u1",
            club_id="club-o1",
            kind="facility_request",
            category="staff_recommendations",
            priority="high",
            sender="General Manager",
            title="Approve Sports Science Wing",
            what="Allocate budget for telemetry suite.",
            why="Reduce hamstring recurrences.",
            body="Requesting boardroom sign-off.",
            is_decision=True,
            status="open",
        )
        session.add_all([injured, decision])
        session.commit()

        hub = client.get("/owner/clubs/club-o1/communications").json()
        threads_by_key = {t["thread_key"]: t for t in hub["direct_threads"]}
        assert "staff:medical_director" in threads_by_key
        assert "staff:head_of_youth_development" in threads_by_key
        assert "staff:general_manager" in threads_by_key
        assert "player:sq-p1" in threads_by_key

        med_thread = threads_by_key["staff:medical_director"]
        assert any("Chinedu Okafor" in m["body"] for m in med_thread["messages"])
        assert med_thread["unread_count"] >= 1

        # Re-fetching does NOT duplicate living event messages
        hub2 = client.get("/owner/clubs/club-o1/communications").json()
        med_thread2 = {t["thread_key"]: t for t in hub2["direct_threads"]}["staff:medical_director"]
        assert len(med_thread2["messages"]) == len(med_thread["messages"])

        # Mark read zeroes unread count
        conv_id = med_thread["thread_id"]
        mark_res = client.post(f"/owner/clubs/club-o1/communications/threads/{conv_id}/read")
        assert mark_res.status_code == 200
        assert mark_res.json()["marked_count"] >= 1

        # Pagination: post 5 extra messages and page with before_seq & limit=2
        for idx in range(5):
            r = client.post(
                "/owner/clubs/club-o1/communications/messages",
                json={"thread_id": conv_id, "message": f"Follow-up medical check #{idx}", "request_reply": False},
            )
            assert r.status_code == 200
        p1 = client.get(f"/owner/clubs/club-o1/communications/threads/{conv_id}/messages?limit=2").json()
        assert len(p1["messages"]) == 2
        assert p1["has_more"] is True
        p2 = client.get(
            f"/owner/clubs/club-o1/communications/threads/{conv_id}/messages?limit=2&before_seq={p1['next_before_seq']}"
        ).json()
        assert len(p2["messages"]) == 2
        assert p2["messages"][-1]["seq"] < p1["messages"][0]["seq"]

        # Search across persisted club comms
        search_hub = client.get("/owner/clubs/club-o1/communications?search=telemetry").json()
        assert isinstance(search_hub["search_results"], list)
        med_search = client.get("/owner/clubs/club-o1/communications?search=Follow-up").json()
        assert len(med_search["search_results"]) >= 1

        # Archive & unarchive direct thread
        arch = client.post(f"/owner/clubs/club-o1/communications/threads/{conv_id}/archive?archived=true")
        assert arch.status_code == 200
        assert arch.json()["archived_at"] is not None
        hub_no_arch = client.get("/owner/clubs/club-o1/communications").json()
        assert all(t["thread_id"] != conv_id for t in hub_no_arch["direct_threads"])
        hub_with_arch = client.get("/owner/clubs/club-o1/communications?include_archived=true").json()
        assert any(t["thread_id"] == conv_id for t in hub_with_arch["direct_threads"])

        # Multi-club summary
        summary = client.get("/owner/communications/summary").json()
        assert len(summary["clubs"]) == 2
        assert summary["total_unread_comms"] >= 1

        # Explicit opt-in public announcement creates a CommunityPost while private DMs stay out of Community
        ann_res = client.post(
            "/owner/clubs/club-o1/communications/announcements",
            json={
                "title": "Public Supporter Open Day",
                "body": "Eko Royals FC welcomes all GTEX supporters to our stadium showcase.",
                "audience": "all_club",
                "publish_to_newsroom": False,
                "also_post_to_community": True,
            },
        )
        assert ann_res.status_code == 200, ann_res.text
        post_id = ann_res.json()["community_post_id"]
        assert post_id is not None
        post = session.get(CommunityPost, post_id)
        assert post is not None
        assert post.club_id == "club-o1"
        assert session.query(CommunityPost).count() == 1
    finally:
        session.close()
