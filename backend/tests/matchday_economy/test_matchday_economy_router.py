from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_optional_current_user, get_session
from app.matchday_economy.router import router as matchday_economy_router
from app.models.admin_rules import AdminFeatureFlag
from app.models.base import Base, utcnow
from app.models.broadcast_rights import BroadcastAccessGrant, BroadcastRight, BroadcastRightsAuction, ViewSession
from app.models.broadcast_watch_session import BroadcastWatchSession
from app.models.clip_variant import ClipVariant
from app.models.club_profile import ClubProfile
from app.models.creator_clip_monetization import CreatorClipRevenueAttribution
from app.models.fan_prediction import (
    FanPredictionFixture,
    FanPredictionFixtureStatus,
    FanPredictionRewardGrant,
    FanPredictionRewardType,
    FanPredictionSubmission,
)
from app.models.fan_war import FanWarPoint, FanWarProfile, FanbaseRanking, NationsCupEntry
from app.models.federation import Federation, FederationLeague, FederationMembership, FederationProposal, FederationSanction
from app.models.notification_center import NotificationPreference
from app.models.notification_record import NotificationRecord
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardListing,
    PlayerCardOwnerHistory,
    PlayerCardSale,
    PlayerCardTier,
)
from app.models.scale_backbone import OrchestratorClipStateRecord, ViralDispatchPoolEntryRecord, ViralLeaderboardEntryRecord
from app.models.sponsored_clip import SponsoredClip
from app.models.ticketing import StadiumEvent, StadiumTicket, TicketReaction, TicketWaitlist
from app.models.user import KycStatus, User, UserRole


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            NotificationPreference.__table__,
            NotificationRecord.__table__,
            AdminFeatureFlag.__table__,
            Federation.__table__,
            FederationLeague.__table__,
            FederationMembership.__table__,
            FederationProposal.__table__,
            FederationSanction.__table__,
            FanPredictionFixture.__table__,
            FanPredictionSubmission.__table__,
            FanPredictionRewardGrant.__table__,
            FanWarProfile.__table__,
            FanWarPoint.__table__,
            FanbaseRanking.__table__,
            NationsCupEntry.__table__,
            ClipVariant.__table__,
            ViralLeaderboardEntryRecord.__table__,
            ViralDispatchPoolEntryRecord.__table__,
            OrchestratorClipStateRecord.__table__,
            BroadcastRight.__table__,
            BroadcastRightsAuction.__table__,
            BroadcastAccessGrant.__table__,
            ViewSession.__table__,
            BroadcastWatchSession.__table__,
            CreatorClipRevenueAttribution.__table__,
            SponsoredClip.__table__,
            StadiumEvent.__table__,
            StadiumTicket.__table__,
            TicketWaitlist.__table__,
            TicketReaction.__table__,
            PlayerCardTier.__table__,
            PlayerCard.__table__,
            PlayerCardHolding.__table__,
            PlayerCardOwnerHistory.__table__,
            PlayerCardListing.__table__,
            PlayerCardSale.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        _seed(db_session)
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(matchday_economy_router, prefix="/api")
    app.state.optional_user_id = None

    def override_session() -> Iterator[Session]:
        yield session

    def override_optional_user() -> User | None:
        user_id = app.state.optional_user_id
        return session.get(User, user_id) if user_id else None

    def override_current_admin() -> User:
        user = session.get(User, "user-admin")
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_optional_current_user] = override_optional_user
    app.dependency_overrides[get_current_admin] = override_current_admin
    with TestClient(app) as test_client:
        yield test_client


def test_public_overview_filters_hidden_and_beta_sections(client: TestClient) -> None:
    response = client.get("/api/matchday-economy/overview")

    assert response.status_code == 200, response.text
    payload = response.json()
    keys = {item["key"] for item in payload["sections"]}
    assert payload["audience"] == "guest"
    assert "federation_governance" in keys
    assert "fan_economy" in keys
    assert "viral_broadcast" in keys
    assert "ticketing_stadium" not in keys
    assert "player_card_collectibles" not in keys


def test_admin_overview_combines_batches_28_to_32_counts(client: TestClient) -> None:
    response = client.get("/api/admin/matchday-economy/overview")

    assert response.status_code == 200, response.text
    payload = response.json()
    sections = {item["key"]: item for item in payload["sections"]}
    assert payload["audience"] == "admin"
    assert set(sections) == {
        "federation_governance",
        "fan_economy",
        "viral_broadcast",
        "ticketing_stadium",
        "player_card_collectibles",
    }
    federation_metrics = _metrics(sections["federation_governance"])
    fan_metrics = _metrics(sections["fan_economy"])
    ticketing_metrics = _metrics(sections["ticketing_stadium"])
    card_metrics = _metrics(sections["player_card_collectibles"])
    assert federation_metrics["federations"] == 1
    assert federation_metrics["proposals"] == 1
    assert fan_metrics["prediction_fixtures"] == 1
    assert fan_metrics["fan_points"] == 1
    assert ticketing_metrics["gross_revenue"] == 5000
    assert card_metrics["open_listings"] == 1
    assert sections["ticketing_stadium"]["health_status"] == "gated"
    assert sections["player_card_collectibles"]["health_status"] == "hidden"


def test_admin_matchday_actions_settle_real_rows(client: TestClient) -> None:
    sanction_response = client.post(
        "/api/admin/matchday-economy/federation-sanctions/fed-sanction-1/resolve",
        json={"note": "Served"},
    )
    assert sanction_response.status_code == 200, sanction_response.text
    assert sanction_response.json()["status"] == "resolved"

    prediction_response = client.post(
        "/api/admin/matchday-economy/predictions/prediction-fixture-1/settle-rewards",
        json={"fancoin_amount": "30.0000", "max_winners": 1},
    )
    assert prediction_response.status_code == 200, prediction_response.text
    assert prediction_response.json()["metrics"]["reward_grants_created"] == 1

    ticket_response = client.post(
        "/api/admin/matchday-economy/tickets/ticket-1/check-in",
        json={"loyalty_points": 50, "xp_awarded": 20, "reaction_type": "cheer"},
    )
    assert ticket_response.status_code == 200, ticket_response.text
    assert ticket_response.json()["metrics"]["event_tickets_used"] == 1

    card_response = client.post(
        "/api/admin/matchday-economy/card-listings/listing-public-1/settle",
        json={"buyer_user_id": "user-admin", "quantity": 1, "fee_bps": 500},
    )
    assert card_response.status_code == 200, card_response.text
    assert card_response.json()["metrics"]["gross_credits"] == 250

    overview = client.get("/api/admin/matchday-economy/overview").json()
    sections = {item["key"]: item for item in overview["sections"]}
    assert _metrics(sections["federation_governance"])["sanctions"] == 0
    assert _metrics(sections["ticketing_stadium"])["used"] == 1
    assert _metrics(sections["player_card_collectibles"])["open_listings"] == 0


def test_admin_matchday_actions_publish_notification_matrix_events(
    client: TestClient,
    session: Session,
) -> None:
    client.post(
        "/api/admin/matchday-economy/federation-sanctions/fed-sanction-1/resolve",
        json={"note": "Served"},
    )
    client.post(
        "/api/admin/matchday-economy/predictions/prediction-fixture-1/settle-rewards",
        json={"fancoin_amount": "30.0000", "max_winners": 1},
    )
    client.post(
        "/api/admin/matchday-economy/tickets/ticket-1/check-in",
        json={"loyalty_points": 50, "xp_awarded": 20, "reaction_type": "cheer"},
    )
    client.post(
        "/api/admin/matchday-economy/card-listings/listing-public-1/settle",
        json={"buyer_user_id": "user-admin", "quantity": 1, "fee_bps": 500},
    )

    records = list(session.scalars(select(NotificationRecord)).all())
    event_keys = {record.resource_type for record in records}
    assert {
        "federation_sanction_resolved",
        "prediction_settled",
        "ticket_attendance_reward",
        "card_listing_sold",
    }.issubset(event_keys)
    assert any(
        record.user_id == "user-admin" and record.resource_type == "card_listing_sold"
        for record in records
    )
    assert any(
        record.user_id == "user-owner" and record.resource_type == "ticket_attendance_reward"
        for record in records
    )


def _metrics(section: dict[str, object]) -> dict[str, float]:
    return {item["key"]: item["value"] for item in section["metrics"]}


def _seed(session: Session) -> None:
    now = utcnow()
    session.add_all(
        [
            User(
                id="user-owner",
                email="owner@example.com",
                username="owner",
                display_name="Owner",
                password_hash="x",
                role=UserRole.USER,
                kyc_status=KycStatus.FULLY_VERIFIED,
            ),
            User(
                id="user-admin",
                email="admin@example.com",
                username="admin",
                display_name="Admin",
                password_hash="x",
                role=UserRole.ADMIN,
                kyc_status=KycStatus.FULLY_VERIFIED,
            ),
            ClubProfile(
                id="club-1",
                owner_user_id="user-owner",
                club_name="Derby Home FC",
                short_name="DHF",
                slug="derby-home-fc",
                primary_color="#0B6E4F",
                secondary_color="#FFFFFF",
                accent_color="#F7C948",
            ),
            ClubProfile(
                id="club-2",
                owner_user_id="user-owner",
                club_name="Derby Away FC",
                short_name="DAF",
                slug="derby-away-fc",
                primary_color="#155EEF",
                secondary_color="#FFFFFF",
                accent_color="#D92D20",
            ),
        ]
    )
    session.add_all(
        [
            AdminFeatureFlag(
                feature_key="federations",
                title="Federations",
                enabled=True,
                audience="public",
                launch_state="public",
                metadata_json={"route": "/app/federations"},
            ),
            AdminFeatureFlag(
                feature_key="fan_coin",
                title="Fan Economy",
                enabled=True,
                audience="public",
                launch_state="public",
                metadata_json={"route": "/app/community"},
            ),
            AdminFeatureFlag(
                feature_key="broadcast",
                title="Broadcast",
                enabled=True,
                audience="public",
                launch_state="maintenance",
                metadata_json={"route": "/broadcast"},
            ),
            AdminFeatureFlag(
                feature_key="ticketing",
                title="Ticketing",
                enabled=True,
                audience="beta",
                launch_state="beta",
                beta_only=True,
                metadata_json={"route": "/app/play"},
            ),
            AdminFeatureFlag(
                feature_key="player_card_marketplace",
                title="Player Cards",
                enabled=True,
                audience="internal",
                launch_state="hidden",
                metadata_json={"route": "/player-cards"},
            ),
        ]
    )
    federation = Federation(
        id="fed-1",
        name="GTEX CAF",
        owner_user_id="user-admin",
        audience_size=2500,
    )
    session.add(federation)
    session.add(
        FederationLeague(
            id="fed-league-1",
            federation_id=federation.id,
            name="CAF Creator League",
            competition_type="league",
            format="round_robin",
            status="active",
        )
    )
    session.add(
        FederationMembership(
            id="fed-member-1",
            federation_id=federation.id,
            club_id="club-1",
            user_id="user-owner",
            status="active",
        )
    )
    session.add(
        FederationProposal(
            id="fed-proposal-1",
            federation_id=federation.id,
            proposer_user_id="user-owner",
            title="Expand youth eligibility",
            summary="Allow one U20 regen slot per national cup entry.",
            status="open",
        )
    )
    session.add(
        FederationSanction(
            id="fed-sanction-1",
            federation_id=federation.id,
            club_id="club-1",
            applied_by_user_id="user-admin",
            sanction_type="fine",
            reason="Fixture integrity review.",
            status="active",
        )
    )
    fixture = FanPredictionFixture(
        id="prediction-fixture-1",
        match_id="match-1",
        competition_id="competition-1",
        home_club_id="club-1",
        away_club_id="club-2",
        created_by_user_id="user-admin",
        title="Derby prediction",
        status=FanPredictionFixtureStatus.OPEN,
        opens_at=now - timedelta(hours=1),
        locks_at=now + timedelta(hours=2),
    )
    session.add(fixture)
    session.add(
        FanPredictionSubmission(
            id="prediction-submission-1",
            fixture_id=fixture.id,
            user_id="user-owner",
            leaderboard_week_start=date.today(),
            winner_club_id="club-1",
            first_goal_scorer_player_id="player-1",
            total_goals=3,
            mvp_player_id="player-2",
        )
    )
    session.add(
        FanPredictionRewardGrant(
            id="prediction-reward-1",
            user_id="user-owner",
            fixture_id=fixture.id,
            reward_type=FanPredictionRewardType.FANCOIN,
            fancoin_amount=Decimal("25"),
        )
    )
    profile = FanWarProfile(
        id="fan-profile-1",
        profile_type="country",
        entity_key="NG",
        display_name="Nigeria",
        slug="nigeria",
    )
    session.add(profile)
    session.add(
        FanWarPoint(
            id="fan-point-1",
            profile_id=profile.id,
            actor_user_id="user-owner",
            source_type="prediction",
            weighted_points=15,
        )
    )
    session.add(
        FanbaseRanking(
            id="fan-ranking-1",
            board_type="country",
            period_type="weekly",
            window_start=date.today(),
            window_end=date.today() + timedelta(days=7),
            profile_id=profile.id,
            profile_type="country",
            rank=1,
            points_total=15,
        )
    )
    session.add(
        NationsCupEntry(
            id="nations-entry-1",
            competition_id="competition-1",
            creator_profile_id="creator-profile-1",
            creator_user_id="user-owner",
            club_id="club-1",
            country_code="NG",
            country_name="Nigeria",
        )
    )
    session.add(
        ClipVariant(
            variant_id="clip-var-1",
            base_clip_id="clip-1",
            format_type="vertical",
            viral_score=91,
            pushed_to_trending=True,
        )
    )
    session.add(ViralLeaderboardEntryRecord(clip_id="clip-1", score=91, payload_json={"title": "Derby goal"}))
    session.add(ViralDispatchPoolEntryRecord(clip_id="clip-1", score=91, expires_at=now + timedelta(hours=1)))
    session.add(OrchestratorClipStateRecord(clip_id="clip-1", stage="scale", base_clip_id="clip-1"))
    right = BroadcastRight(
        id="broadcast-right-1",
        competition_id="competition-1",
        owner_id="user-owner",
        acquisition_price=Decimal("1000"),
        revenue_share_percentage=Decimal("10"),
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )
    session.add(right)
    session.add(
        BroadcastRightsAuction(
            id="broadcast-auction-1",
            competition_id="competition-1",
            seller_owner_id="user-owner",
            reserve_price=Decimal("500"),
            revenue_share_percentage=Decimal("12"),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            ends_at=now + timedelta(days=1),
            status="open",
        )
    )
    session.add(BroadcastAccessGrant(id="broadcast-grant-1", broadcast_right_id=right.id, user_id="user-owner"))
    session.add(ViewSession(id="view-session-1", user_id="user-owner", match_id="match-1", competition_id="competition-1"))
    session.add(BroadcastWatchSession(id="watch-session-1", user_id="user-owner", channel_id="main", current_match_id="match-1"))
    session.add(
        CreatorClipRevenueAttribution(
            id="clip-revenue-1",
            export_id="export-1",
            creator_user_id="user-owner",
            match_key="match-1",
            views=1000,
            gross_revenue_credit=Decimal("20"),
        )
    )
    session.add(
        SponsoredClip(
            id="sponsored-clip-1",
            advertiser_id="brand-1",
            clip_id="clip-1",
            budget=Decimal("100"),
            bid_cpm=Decimal("5"),
            start_time=now,
            end_time=now + timedelta(days=7),
        )
    )
    event = StadiumEvent(
        id="stadium-event-1",
        stadium_id="stadium-1",
        match_id="match-1",
        title="Derby Night",
        venue_name="GTEX Arena",
        capacity=50000,
        tickets_sold=1,
        gross_revenue=Decimal("5000"),
    )
    session.add(event)
    ticket = StadiumTicket(
        id="ticket-1",
        event_id=event.id,
        user_id="user-owner",
        match_id="match-1",
        seat_tier="A",
        seat_code="A-1",
        price=Decimal("5000"),
        original_price=Decimal("5000"),
        status="sold",
    )
    session.add(ticket)
    session.add(TicketWaitlist(id="waitlist-1", match_id="match-1", user_id="user-owner", status="queued"))
    session.add(
        TicketReaction(
            id="ticket-reaction-1",
            ticket_id=ticket.id,
            match_id="match-1",
            user_id="user-owner",
            reaction_type="cheer",
            crowd_delta=Decimal("1.2"),
            influence_multiplier=Decimal("1.0"),
        )
    )
    tier = PlayerCardTier(id="tier-1", code="gold", name="Gold", rarity_rank=2)
    card = PlayerCard(
        id="card-1",
        player_id="player-1",
        tier_id=tier.id,
        edition_code="2026",
        display_name="Derby Striker Gold",
        supply_total=100,
        supply_available=40,
    )
    session.add(tier)
    session.add(card)
    session.add(PlayerCardHolding(id="holding-1", player_card_id=card.id, owner_user_id="user-owner", quantity_total=2))
    session.add(
        PlayerCardListing(
            id="listing-1",
            listing_id="listing-public-1",
            player_card_id=card.id,
            seller_user_id="user-owner",
            quantity=1,
            price_per_card_credits=Decimal("250"),
            status="open",
        )
    )
    session.add(
        PlayerCardSale(
            id="sale-1",
            sale_id="sale-public-1",
            listing_id="listing-public-1",
            player_card_id=card.id,
            seller_user_id="user-owner",
            buyer_user_id="user-admin",
            quantity=1,
            price_per_card_credits=Decimal("250"),
            gross_credits=Decimal("250"),
            fee_credits=Decimal("10"),
            seller_net_credits=Decimal("240"),
            settlement_reference="settle-1",
        )
    )
    session.commit()
