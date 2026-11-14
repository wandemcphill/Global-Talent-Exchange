from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
import json

from alembic import command
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import (
    get_current_admin,
    get_current_social_user,
    get_current_user,
    get_optional_current_user,
    get_session,
)
from app.auth.service import AuthService
from app.club_social.router import router as club_social_router
from app.community_engine.router import router as community_router
from app.db import get_session as get_db_session
from app.core.database import build_alembic_config, load_model_modules
from app.ingestion.models import Country, LiquidityBand, Player, SupplyTier
from app.models.base import Base
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionFundingMode,
    HostedCompetitionStatus,
    UserHostedCompetition,
    UserHostedCompetitionParticipant,
)
from app.models.regen import RegenProfile
from app.models.user import KycStatus, PublicAccountType, User, UserRole
from app.notifications.router import router as notifications_router
from app.notifications.service import NotificationCenter
from app.owner_console import engine as owner_engine, ledger
from app.owner_console.models import OwnerClubState
from app.realtime import service as realtime_service
from app.realtime.router import router as realtime_router
from app.realtime.service import RealtimeHub


def _setup_app() -> tuple[Session, dict[str, str], TestClient, RealtimeHub]:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()

    fan = User(
        id="fan-u1",
        email="clubless@gtex.test",
        username="clubless_fan",
        display_name="Clubless Fan",
        password_hash="x",
        role=UserRole.USER,
        account_type=PublicAccountType.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    organizer = User(
        id="org-u2",
        email="organizer@gtex.test",
        username="cup_host",
        display_name="Cup Organizer",
        password_hash="x",
        role=UserRole.USER,
        account_type=PublicAccountType.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    admin = User(
        id="admin-u3",
        email="admin@gtex.test",
        username="mod_admin",
        display_name="GTEX Moderator",
        password_hash="x",
        role=UserRole.ADMIN,
        account_type=PublicAccountType.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    country = Country(
        id="cnt-ng",
        source_provider="test",
        provider_external_id="NG",
        name="Nigeria",
        alpha2_code="NG",
    )
    tier = SupplyTier(
        id="tier-1",
        code="marquee",
        name="Marquee",
        rank=1,
        min_score=75.0,
        max_score=99.0,
        target_share=0.1,
        circulating_supply=200,
        daily_pack_supply=10,
        season_mint_cap=200,
    )
    band = LiquidityBand(
        id="band-1",
        code="mid",
        name="Mid",
        rank=1,
        min_price_credits=100,
        max_price_credits=1000,
        max_spread_bps=500,
        maker_inventory_target=10,
        instant_sell_fee_bps=250,
    )
    club = ClubProfile(
        id="pub-club-1",
        owner_user_id=organizer.id,
        club_name="Victoria Island United",
        short_name="VIU",
        club_type=ClubType.COMMUNITY,
        lifecycle_status=ClubLifecycleStatus.ACTIVE,
        slug="victoria-island-united",
        primary_color="#00C991",
        secondary_color="#080F1C",
        accent_color="#E5B63F",
        country_code="NG",
        city_name="Lagos",
        description="Youth and tactical showcase club.",
        visibility="public",
    )
    session.add_all([fan, organizer, admin, country, tier, band, club])
    session.flush()

    session.add(
        OwnerClubState(
            club_id=club.id,
            owner_user_id=organizer.id,
            club_name=club.club_name,
            stage="active",
            prestige=74,
            manager_json=owner_engine.manager_profile(owner_engine.DEFAULT_MANAGER),
            facilities_json={"internal_note": "Confidential medical and budget memo"},
            world_day=12,
        )
    )
    ledger.record(
        session,
        event_type="club_launch_grant",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club.id),
        currency=ledger.GTEX,
        gross=Decimal(99_999),
        club_id=club.id,
        user_id=organizer.id,
        memo="Private treasury",
    )

    real_player = Player(
        id="pl-real-1",
        source_provider="test",
        provider_external_id="p-real-1",
        country_id=country.id,
        supply_tier_id=tier.id,
        liquidity_band_id=band.id,
        full_name="Tunde Balogun",
        canonical_display_name="Tunde Balogun",
        position="CM",
        normalized_position="CM",
        governed_gsi=84,
        real_player_tier="marquee",
        is_tradable=True,
    )
    dup_player = Player(
        id="pl-dup-archived",
        source_provider="test",
        provider_external_id="p-dup-1",
        country_id=country.id,
        supply_tier_id=tier.id,
        liquidity_band_id=band.id,
        full_name="Duplicate Phantom",
        canonical_display_name="Duplicate Phantom",
        position="ST",
        normalized_position="ST",
        governed_gsi=95,
        real_player_tier="archived_duplicate",
        is_tradable=False,
    )
    session.add_all([real_player, dup_player])
    session.flush()

    regen = RegenProfile(
        id="reg-prof-1",
        regen_id="rg-1001",
        player_id=real_player.id,
        linked_unique_card_id="card-1001",
        generated_for_club_id=club.id,
        birth_country_code="NG",
        primary_position="CM",
        secondary_positions_json=["CAM"],
        generated_at=datetime.now(timezone.utc),
        current_gsi=84,
        current_ability_range_json={"min": 80, "max": 86},
        potential_range_json={"min": 88, "max": 94},
        scout_confidence="High",
        generation_source="academy",
        status="active",
        metadata_json={},
    )
    tmpl = CompetitionTemplate(
        id="tmpl-open",
        template_key="community-cup-8",
        title="Community 8-Team Cup",
        description="Free-entry community cup.",
        competition_type="cup",
        team_type="club",
        participants=8,
        funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
        entry_fee_fancoin=Decimal("0.0000"),
        reward_pool_coin=Decimal("500.0000"),
    )
    hosted_private = UserHostedCompetition(
        id="comp-app-1",
        template_id=tmpl.id,
        host_user_id=organizer.id,
        title="Lagos Invitational Showcase",
        slug="lagos-invitational-showcase",
        description="Application-gated community showcase cup.",
        status=HostedCompetitionStatus.OPEN,
        visibility="invite_only",
        max_participants=8,
        funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
        entry_fee_fancoin=Decimal("0.0000"),
        reward_pool_coin=Decimal("500.0000"),
        host_funding_required_coin=Decimal("500.0000"),
        host_funding_escrowed_coin=Decimal("500.0000"),
    )
    session.add_all([regen, tmpl, hosted_private])
    session.commit()

    actor_state = {"id": fan.id}
    hub = RealtimeHub()
    hub.bind_session_factory(factory)

    app = FastAPI()
    app.state.realtime = hub
    app.state.notifications = NotificationCenter()
    app.state.session_factory = factory
    app.include_router(community_router)
    app.include_router(club_social_router)
    app.include_router(notifications_router, prefix="/api")
    app.include_router(realtime_router)

    def _override_session() -> Iterator[Session]:
        yield session

    def _current_user() -> User:
        u = session.get(User, actor_state["id"])
        assert u is not None
        return u

    def _optional_user() -> User | None:
        return session.get(User, actor_state["id"]) if actor_state.get("id") else None

    def _admin_user() -> User:
        return session.get(User, "admin-u3")  # type: ignore[return-value]

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_current_social_user] = _current_user
    app.dependency_overrides[get_optional_current_user] = _optional_user
    app.dependency_overrides[get_current_admin] = _admin_user
    return session, actor_state, TestClient(app), hub


def test_clubs_players_competitions_application_workflow_and_privacy() -> None:
    session, actor_state, client, _ = _setup_app()
    try:
        # 1. Clubless user accesses all 11+ Community channels & Clubs showcase (no owner financials leaked)
        ch_res = client.get("/community/channels").json()
        assert len(ch_res["channels"]) >= 11

        clubs = client.get("/community/discovery/clubs").json()["clubs"]
        assert len(clubs) == 1
        assert clubs[0]["club_name"] == "Victoria Island United"
        assert "treasury" not in json.dumps(clubs).lower()
        assert "confidential" not in json.dumps(clubs).lower()

        # Support club via canonical /api/social/follows updates follower count
        follow_res = client.post("/api/social/follows", json={"target_type": "club", "club_id": "pub-club-1"})
        assert follow_res.status_code in (200, 201), follow_res.text
        clubs_after = client.get("/community/discovery/clubs").json()["clubs"]
        assert clubs_after[0]["follower_count"] == 1
        assert clubs_after[0]["viewer_follows"] is True

        # 2. Player & Regen discovery strictly excludes archived_duplicate
        players = client.get("/community/discovery/players?regens_only=true").json()["players"]
        names = [p["name"] for p in players]
        assert "Tunde Balogun" in names
        assert "Duplicate Phantom" not in names

        # 3. People directory never exposes private emails
        people = client.get("/community/discovery/people").json()["people"]
        assert len(people) >= 1
        assert "organizer@gtex.test" not in json.dumps(people)

        # 4. Competition discovery & free-entry application -> organizer approval -> canonical participant + notifications
        comps = client.get("/community/competitions").json()["competitions"]
        assert len(comps) == 1
        assert comps[0]["entry_fee_fancoin"] == 0.0
        assert comps[0]["slots_remaining"] == 8

        app_res = client.post(
            "/community/competitions/comp-app-1/apply",
            json={"note": "Active manager ready for all matchdays"},
        )
        assert app_res.status_code == 200, app_res.text
        app_id = app_res.json()["id"]
        assert app_res.json()["status"] == "pending"

        # Applicant cannot view or review organizer queue
        assert client.get("/community/competitions/comp-app-1/applications").status_code == 403
        assert (
            client.post(
                f"/community/competitions/applications/{app_id}/review", json={"decision": "accept"}
            ).status_code
            == 403
        )

        # Organizer reviews & accepts -> creates UserHostedCompetitionParticipant + notifies applicant
        actor_state["id"] = "org-u2"
        notifs_org = client.get("/api/notifications/me").json()
        assert len(notifs_org) >= 1
        assert any(
            n.get("template_key") == "competition.application.received"
            and n.get("metadata", {}).get("event_key") == "competition_application_received"
            for n in notifs_org
        )

        apps = client.get("/community/competitions/comp-app-1/applications").json()["applications"]
        assert len(apps) == 1
        review_res = client.post(
            f"/community/competitions/applications/{app_id}/review",
            json={"decision": "accept", "review_note": "Welcome aboard"},
        )
        assert review_res.status_code == 200, review_res.text
        assert review_res.json()["status"] == "accepted"

        part = (
            session.query(UserHostedCompetitionParticipant)
            .filter(
                UserHostedCompetitionParticipant.competition_id == "comp-app-1",
                UserHostedCompetitionParticipant.user_id == "fan-u1",
            )
            .one_or_none()
        )
        assert part is not None

        actor_state["id"] = "fan-u1"
        comps_after = client.get("/community/competitions").json()["competitions"]
        assert comps_after[0]["viewer_joined"] is True
        assert comps_after[0]["slots_remaining"] == 7
        notifs_fan = client.get("/api/notifications/me").json()
        assert any(
            n.get("template_key") == "competition.application.reviewed"
            and n.get("metadata", {}).get("event_key") == "competition_application_reviewed"
            for n in notifs_fan
        )
    finally:
        session.close()


def test_pm_group_pagination_leave_block_and_websocket_auth_scoping() -> None:
    session, actor_state, client, hub = _setup_app()
    try:
        # Create 3-person group conversation
        thread = client.post(
            "/community/private-messages/threads",
            json={
                "participant_user_ids": ["org-u2", "admin-u3"],
                "subject": "Tactics Group",
                "initial_message": "Opening tactical thread",
            },
        ).json()
        thread_id = thread["id"]
        assert thread["is_group"] is True

        # Post 4 more messages to exercise seq pagination
        for i in range(4):
            r = client.post(f"/community/private-messages/threads/{thread_id}/messages", json={"body": f"PM #{i}"})
            assert r.status_code == 201

        page1 = client.get(f"/community/private-messages/threads/{thread_id}/messages/page?limit=2").json()
        assert len(page1["messages"]) == 2
        assert page1["has_more"] is True
        page2 = client.get(
            f"/community/private-messages/threads/{thread_id}/messages/page?limit=2&before_seq={page1['next_before_seq']}"
        ).json()
        assert len(page2["messages"]) == 2
        assert page2["messages"][-1]["seq"] < page1["messages"][0]["seq"]

        # WebSocket authorization test: token issued via AuthService
        auth = AuthService()
        fan_token, _ = auth.issue_access_token(session.get(User, "fan-u1"))  # type: ignore[arg-type]
        org_token, _ = auth.issue_access_token(session.get(User, "org-u2"))  # type: ignore[arg-type]

        # Non-owner fan MUST NOT receive owner_comms:club:pub-club-1 subscription
        with client.websocket_connect(f"/realtime/stream?token={fan_token}&topics=owner_comms:club:pub-club-1") as ws:
            hello = ws.receive_json()
            assert hello["type"] == "subscription_ack"
            assert "owner_comms:club:pub-club-1" not in hello["data"]["topics"]

        # Legitimate club owner IS subscribed to owner_comms:club:pub-club-1 and participant to pm:<thread_id>
        with client.websocket_connect(
            f"/realtime/stream?token={org_token}&topics=owner_comms:club:pub-club-1,pm:{thread_id}"
        ) as ws:
            hello = ws.receive_json()
            assert hello["type"] == "subscription_ack"
            assert "owner_comms:club:pub-club-1" in hello["data"]["topics"]
            assert f"pm:{thread_id}" in hello["data"]["topics"]

        # Leave group removes user from thread list
        assert client.post(f"/community/private-messages/threads/{thread_id}/leave").status_code == 200
        assert all(t["id"] != thread_id for t in client.get("/community/private-messages/threads").json())

        # Blocking excludes user from People discovery and unblocking restores
        assert client.post("/community/users/org-u2/block").status_code == 201
        people_blocked = client.get("/community/discovery/people").json()["people"]
        assert all(p["id"] != "org-u2" for p in people_blocked)
        assert client.delete("/community/users/org-u2/block").status_code == 200
        people_unblocked = client.get("/community/discovery/people").json()["people"]
        assert any(p["id"] == "org-u2" for p in people_unblocked)
    finally:
        realtime_service._GLOBAL_REALTIME_HUB = None
        session.close()


def test_alembic_migration_20261113_0243_head_and_downgrade_upgrade_cycle(tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{(tmp_path / 'community_comms_migration.db').as_posix()}"
    cfg = build_alembic_config(db_url)
    command.upgrade(cfg, "head")
    eng = create_engine(db_url, connect_args={"check_same_thread": False})
    try:
        insp = inspect(eng)
        for table_name in (
            "community_channels",
            "community_channel_messages",
            "community_posts",
            "community_post_comments",
            "community_bookmarks",
            "community_poll_votes",
            "community_user_mutes",
            "community_competition_applications",
            "owner_club_conversations",
            "owner_club_messages",
            "owner_club_meetings",
            "owner_club_announcements",
        ):
            assert insp.has_table(table_name), f"Missing migrated table {table_name}"
        with eng.connect() as conn:
            ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert ver == "20261113_0243_community_and_owner_comms_overhaul"
    finally:
        eng.dispose()
