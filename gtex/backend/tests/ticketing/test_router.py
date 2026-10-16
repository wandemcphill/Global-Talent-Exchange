from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import (
    get_current_match_user,
    get_current_wallet_user,
    get_session as auth_get_session,
)
from app.match_engine.schemas import MatchCrowdStateView
from app.models.base import Base
from app.models.calendar_engine import CalendarEvent, CalendarSeason, GlobalEvent
from app.models.club_infra import ClubStadium
from app.models.club_profile import ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.event_backbone import EventOutbox
from app.models.notification_record import NotificationRecord
from app.models.ticketing import StadiumEvent, StadiumTicket, TicketReaction, TicketWaitlist
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction, LedgerUnit
from app.live_ops.models import LiveEvent, SeasonPass, SeasonPassXpGrant
from app.ticketing.router import router as ticketing_router
from app.ticketing.runtime import TicketingRuntime
from app.wallets.service import LedgerPosting, WalletService


def _build_app() -> tuple[FastAPI, sessionmaker[Session], dict[str, User]]:
    app = FastAPI()
    app.include_router(ticketing_router)
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            ClubStadium.__table__,
            CalendarSeason.__table__,
            CalendarEvent.__table__,
            GlobalEvent.__table__,
            CompetitionMatch.__table__,
            StadiumEvent.__table__,
            StadiumTicket.__table__,
            TicketWaitlist.__table__,
            TicketReaction.__table__,
            NotificationRecord.__table__,
            LiveEvent.__table__,
            SeasonPass.__table__,
            SeasonPassXpGrant.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            EventOutbox.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    users = {
        "user-1": User(
            id="user-1",
            email="one@example.com",
            username="one",
            full_name="User One",
            display_name="User One",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        "user-2": User(
            id="user-2",
            email="two@example.com",
            username="two",
            full_name="User Two",
            display_name="User Two",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        "user-3": User(
            id="user-3",
            email="three@example.com",
            username="three",
            full_name="User Three",
            display_name="User Three",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
        "vip-user": User(
            id="vip-user",
            email="vip@example.com",
            username="vip",
            full_name="VIP User",
            display_name="VIP User",
            password_hash="hash",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
            is_active=True,
        ),
    }
    with session_factory() as session:
        session.add_all(users.values())
        session.flush()
        session.add_all(
            [
                ClubProfile(
                    id="club-home",
                    owner_user_id="user-1",
                    club_name="Alpha FC",
                    short_name="Alpha",
                    slug="alpha-fc",
                    primary_color="#111111",
                    secondary_color="#dddddd",
                    accent_color="#00aa00",
                    home_venue_name="Alpha Dome",
                    visibility="public",
                ),
                ClubProfile(
                    id="club-away",
                    owner_user_id="user-2",
                    club_name="Beta FC",
                    short_name="Beta",
                    slug="beta-fc",
                    primary_color="#222222",
                    secondary_color="#cccccc",
                    accent_color="#aa0000",
                    home_venue_name="Beta Park",
                    visibility="public",
                ),
                ClubStadium(
                    id="stadium-home",
                    club_id="club-home",
                    name="Alpha Dome",
                    capacity=2,
                    theme_key="finals",
                ),
                CompetitionMatch(
                    id="final-match",
                    competition_id="competition-1",
                    round_id="round-1",
                    round_number=1,
                    stage="final",
                    home_club_id="club-home",
                    away_club_id="club-away",
                    scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
                    status="scheduled",
                    metadata_json={"home_name": "Alpha FC", "away_name": "Beta FC", "rivalry_score": 0.62},
                ),
                SeasonPass(
                    id="season-pass-vip",
                    user_id="vip-user",
                    season_id="season-1",
                    tier="premium",
                    xp=1800,
                    level=18,
                    rewards_json={},
                    metadata_json={},
                ),
            ]
        )
        for user in users.values():
            _seed_main_wallet(session, user, amount=Decimal("500.0000"))
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    def override_user(request: Request) -> User:
        return users[request.headers.get("X-User-Id", "user-1")]

    app.dependency_overrides[auth_get_session] = override_session
    app.dependency_overrides[get_current_wallet_user] = override_user
    app.dependency_overrides[get_current_match_user] = override_user
    app.state.session_factory = session_factory
    app.state.ticketing_runtime = TicketingRuntime(app=app, session_factory=session_factory)
    app.state.stadium_ticket_crowd_overlay_provider = app.state.ticketing_runtime.crowd_overlay
    return app, session_factory, users


def _seed_main_wallet(session: Session, actor: User, *, amount: Decimal) -> None:
    wallet_service = WalletService()
    accounts = wallet_service.ensure_default_accounts(session, actor)
    operations = wallet_service.ensure_operations_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=accounts[LedgerUnit.CREDIT], amount=amount),
            LedgerPosting(account=operations, amount=-amount),
        ],
        reason=wallet_service.trade_settlement_reason,
        reference=f"seed-wallet:{actor.id}",
        description="Seed wallet for ticketing tests",
        actor=actor,
    )
    session.flush()


def test_ticketing_router_handles_buy_waitlist_resale_crowd_and_rewards() -> None:
    app, session_factory, users = _build_app()
    client = TestClient(app)

    event_response = client.get("/tickets/event/final-match", headers={"X-User-Id": "user-1"})
    assert event_response.status_code == 200, event_response.text
    event_payload = event_response.json()["event"]
    assert event_payload["event_type"] == "final"
    assert event_payload["capacity"] == 2

    buy_regular = client.post(
        "/tickets/buy",
        json={"match_id": "final-match", "seat_tier": "regular"},
        headers={"X-User-Id": "user-1"},
    )
    assert buy_regular.status_code == 201, buy_regular.text
    regular_ticket = buy_regular.json()["ticket"]
    regular_price = Decimal(regular_ticket["price"])

    buy_premium = client.post(
        "/tickets/buy",
        json={"match_id": "final-match", "seat_tier": "premium"},
        headers={"X-User-Id": "user-2"},
    )
    assert buy_premium.status_code == 201, buy_premium.text
    assert buy_premium.json()["event"]["event_status"] == "sold_out"
    premium_price = Decimal(buy_premium.json()["ticket"]["price"])

    oversell = client.post(
        "/tickets/buy",
        json={"match_id": "final-match", "seat_tier": "regular"},
        headers={"X-User-Id": "user-3"},
    )
    assert oversell.status_code == 409, oversell.text

    waitlist = client.post(
        "/tickets/waitlist",
        json={"match_id": "final-match", "seat_tier": "regular"},
        headers={"X-User-Id": "user-3"},
    )
    assert waitlist.status_code == 201, waitlist.text
    assert waitlist.json()["status"] == "queued"

    resale_price = (regular_price * Decimal("1.2500")).quantize(Decimal("0.0001"))
    resale = client.post(
        "/tickets/resell",
        json={"ticket_id": regular_ticket["ticket_id"], "price": str(resale_price)},
        headers={"X-User-Id": "user-1"},
    )
    assert resale.status_code == 200, resale.text
    resale_payload = resale.json()
    assert resale_payload["ticket"]["status"] == "available"
    assert resale_payload["notified_waitlist_count"] == 1

    resale_buy = client.post(
        "/tickets/buy",
        json={"match_id": "final-match", "resale_ticket_id": regular_ticket["ticket_id"]},
        headers={"X-User-Id": "user-3"},
    )
    assert resale_buy.status_code == 201, resale_buy.text
    assert resale_buy.json()["ticket"]["user_id"] == "user-3"
    assert resale_buy.json()["ticket"]["seat_code"] == regular_ticket["seat_code"]

    reaction = client.post(
        "/tickets/attendance/final-match/react",
        json={"reaction_type": "cheer", "intensity": 1.5},
        headers={"X-User-Id": "user-3"},
    )
    assert reaction.status_code == 200, reaction.text
    assert Decimal(reaction.json()["crowd_delta"]) > Decimal("0.0000")

    overlay = app.state.ticketing_runtime.crowd_overlay("final-match", MatchCrowdStateView())
    assert overlay is not None
    assert overlay.crowd_intensity > 0.5
    assert overlay.chant_level > 0.5

    with session_factory() as session:
        match = session.get(CompetitionMatch, "final-match")
        assert match is not None
        match.status = "completed"
        match.completed_at = datetime.now(timezone.utc)
        session.commit()

    rewards = client.get("/tickets/event/final-match", headers={"X-User-Id": "user-3"})
    assert rewards.status_code == 200, rewards.text
    my_ticket = rewards.json()["my_ticket"]
    assert my_ticket["status"] == "used"
    assert my_ticket["loyalty_points_awarded"] > 0
    assert my_ticket["xp_awarded"] > 0
    assert my_ticket["exclusive_drop_code"] is not None

    with session_factory() as session:
        wallet_service = WalletService()
        user_one_balance = wallet_service.get_wallet_summary(session, users["user-1"], currency=LedgerUnit.CREDIT).available_balance
        user_two_balance = wallet_service.get_wallet_summary(session, users["user-2"], currency=LedgerUnit.CREDIT).available_balance
        user_three_balance = wallet_service.get_wallet_summary(session, users["user-3"], currency=LedgerUnit.CREDIT).available_balance
        seller_proceeds = (resale_price * Decimal("0.8500")).quantize(Decimal("0.0001"))
        assert user_one_balance == Decimal("500.0000") - regular_price + seller_proceeds
        assert user_two_balance == Decimal("500.0000") - premium_price
        assert user_three_balance == Decimal("500.0000") - resale_price

        notification = session.scalar(
            select(NotificationRecord).where(
                NotificationRecord.user_id == "user-3",
                NotificationRecord.topic == "ticket_resale_available",
            )
        )
        assert notification is not None

        event = session.scalar(select(StadiumEvent).where(StadiumEvent.match_id == "final-match"))
        assert event is not None
        assert event.tickets_sold == 2
        assert event.tickets_used >= 1


def test_ticketing_router_supports_ceremony_vip_flow_and_early_access(monkeypatch) -> None:
    app, session_factory, _users = _build_app()
    client = TestClient(app)

    monkeypatch.setattr(
        "app.awards.service.AwardsCultureService.get_ceremony",
        lambda self, season_id=None: {
            "season_id": season_id or "season-1",
            "title": "GTEX Awards Night 1",
            "countdown_seconds": 180,
            "segments": [{"title": "Golden Boot", "presenter": "Amina Cole"}],
        },
    )

    ceremony_event = client.get("/tickets/event/ceremony:season-1", headers={"X-User-Id": "vip-user"})
    assert ceremony_event.status_code == 200, ceremony_event.text
    ceremony_payload = ceremony_event.json()["event"]
    assert ceremony_payload["event_type"] == "ceremony"
    assert ceremony_payload["tier_distribution"]["regular"] == 0
    assert ceremony_payload["experience"]["red_carpet"] is True
    assert ceremony_payload["user_has_early_access"] is True

    with session_factory() as session:
        event = session.scalar(select(StadiumEvent).where(StadiumEvent.match_id == "ceremony:season-1"))
        assert event is not None
        event.early_access_starts_at = datetime.now(timezone.utc) - timedelta(hours=1)
        event.public_sales_starts_at = datetime.now(timezone.utc) + timedelta(hours=1)
        session.commit()

    blocked = client.post(
        "/tickets/buy",
        json={"match_id": "ceremony:season-1", "seat_tier": "vip"},
        headers={"X-User-Id": "user-1"},
    )
    assert blocked.status_code == 409, blocked.text

    vip_buy = client.post(
        "/tickets/buy",
        json={"match_id": "ceremony:season-1", "seat_tier": "vip"},
        headers={"X-User-Id": "vip-user"},
    )
    assert vip_buy.status_code == 201, vip_buy.text
    vip_payload = vip_buy.json()
    assert vip_payload["ticket"]["seat_tier"] == "vip"
    assert vip_payload["attendee_access"]["badge"] == "You are in the stadium"
    assert vip_payload["attendee_access"]["low_latency_target_ms"] == 110
    assert "tunnel_cam" in vip_payload["attendee_access"]["exclusive_camera_angles"]
