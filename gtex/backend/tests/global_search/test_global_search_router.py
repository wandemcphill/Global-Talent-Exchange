from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.global_search.router import router as global_search_router
from app.ingestion.models import Player
from app.models.broadcast_rights import BroadcastRight, BroadcastRightsAuction
from app.models.clip_variant import ClipVariant
from app.models.coin_trader import CoinTradeOrder, CoinTraderProfile
from app.models.base import Base
from app.models.club_growth import AcademyProfile, AcademyProspect, ClubStaffProfile
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.fan_prediction import FanPredictionFixture, FanPredictionFixtureStatus
from app.models.fan_war import FanWarProfile
from app.models.federation import Federation
from app.models.news_article import NewsArticle
from app.models.notification_record import NotificationRecord
from app.models.player_cards import PlayerCard, PlayerCardListing, PlayerCardTier
from app.models.player_token_market import PlayerShareMarket
from app.models.sponsored_clip import SponsoredClip
from app.models.ticketing import StadiumEvent, StadiumTicket
from app.models.transfer_market import TransferListing
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerUnit
from app.notifications.router import admin_router as notifications_admin_router


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
            ClubStaffProfile.__table__,
            AcademyProfile.__table__,
            AcademyProspect.__table__,
            ClubSponsorshipPackage.__table__,
            UserCompetition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            Player.__table__,
            PlayerShareMarket.__table__,
            NewsArticle.__table__,
            NotificationRecord.__table__,
            Federation.__table__,
            FanPredictionFixture.__table__,
            FanWarProfile.__table__,
            BroadcastRight.__table__,
            BroadcastRightsAuction.__table__,
            ClipVariant.__table__,
            SponsoredClip.__table__,
            TransferListing.__table__,
            CoinTraderProfile.__table__,
            CoinTradeOrder.__table__,
            StadiumEvent.__table__,
            StadiumTicket.__table__,
            PlayerCardTier.__table__,
            PlayerCard.__table__,
            PlayerCardListing.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        owner = User(
            id="user-owner",
            email="owner@example.com",
            username="owner",
            display_name="Owner",
            password_hash="x",
            role=UserRole.USER,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        admin = User(
            id="user-admin",
            email="admin@example.com",
            username="admin",
            display_name="Admin",
            password_hash="x",
            role=UserRole.ADMIN,
            kyc_status=KycStatus.FULLY_VERIFIED,
        )
        club = ClubProfile(
            id="club-arsenal",
            owner_user_id="user-owner",
            club_name="Arsenal Lagos",
            short_name="AFC",
            slug="arsenal-lagos",
            primary_color="#EF0107",
            secondary_color="#FFFFFF",
            accent_color="#063672",
            country_code="NG",
            city_name="Lagos",
        )
        rival_club = ClubProfile(
            id="club-rangers",
            owner_user_id="user-owner",
            club_name="Rangers Lagos",
            short_name="RFC",
            slug="rangers-lagos",
            primary_color="#0055A4",
            secondary_color="#FFFFFF",
            accent_color="#C8102E",
            country_code="NG",
            city_name="Lagos",
        )
        player = Player(
            id="player-jude",
            source_provider="fixture",
            provider_external_id="jude-1",
            full_name="Jude Bellingham",
            canonical_display_name="Jude Bellingham",
            normalized_position="CM",
            position="Midfielder",
            real_world_club_name="Real Madrid",
            real_world_league_name="La Liga",
            is_real_player=True,
        )
        now = datetime.now(UTC)
        db_session.add_all(
            [
                owner,
                admin,
                club,
                rival_club,
                player,
                ClubStaffProfile(
                    id="staff-agent-lagos",
                    market_key="agent-lagos-elite",
                    display_name="Adaeze Nwosu",
                    staff_type="agent",
                    rarity="elite",
                    skills_json=["negotiation", "contract_handling"],
                    salary_minor=12000,
                    commission_bps=450,
                    rating=88,
                    active=True,
                ),
                AcademyProfile(
                    id="academy-arsenal",
                    club_id=club.id,
                    level=3,
                    investment_minor=50000,
                ),
                AcademyProspect(
                    id="prospect-kelechi",
                    club_id=club.id,
                    academy_profile_id="academy-arsenal",
                    display_name="Kelechi Okoro",
                    nationality="NG",
                    position="ST",
                    age=16,
                    portrait_asset_ref="newgen/ng/kelechi-okoro.png",
                    status="contract_offered",
                ),
                ClubSponsorshipPackage(
                    id="sponsor-front-shirt",
                    code="front-shirt",
                    name="Front Shirt Sponsor",
                    asset_type=SponsorshipAssetType.JERSEY_FRONT,
                    base_amount_minor=100000,
                    currency="CREDITS",
                    default_duration_months=2,
                    payout_schedule="monthly",
                    description="Primary shirt package for verified GTEX clubs.",
                    is_active=True,
                ),
                UserCompetition(
                    id="competition-lagos-final",
                    host_user_id=owner.id,
                    name="Lagos Continental Cup",
                    description="Federation final with broadcast rights, fan predictions, and viral highlights.",
                    format="single_elimination",
                    visibility="public",
                    status="active",
                    start_mode="scheduled",
                    currency="CREDIT",
                    metadata_json={"federation_id": "federation-africa"},
                ),
                CompetitionRound(
                    id="round-lagos-final",
                    competition_id="competition-lagos-final",
                    round_number=1,
                    stage="final",
                    name="Final",
                    status="scheduled",
                ),
                CompetitionMatch(
                    id="match-lagos-final",
                    competition_id="competition-lagos-final",
                    round_id="round-lagos-final",
                    round_number=1,
                    stage="final",
                    home_club_id=club.id,
                    away_club_id=rival_club.id,
                    status="scheduled",
                    scheduled_at=now + timedelta(days=1),
                    match_date=date.today() + timedelta(days=1),
                ),
                NewsArticle(
                    article_type="market",
                    title="Arsenal Lagos scout Real Madrid midfielders",
                    body="A transfer market story linking GTEX clubs and Real Madrid.",
                    summary="Real Madrid midfielders are drawing GTEX attention.",
                ),
                Federation(
                    id="federation-africa",
                    name="Africa GTEX Federation",
                    owner_user_id=admin.id,
                    structure_json={"level": "continental"},
                    rules_json={"eligibility": "verified_clubs"},
                    competitions_json=[{"competition_id": "competition-lagos-final"}],
                    members_json=[{"club_id": club.id}],
                    ranking_score=88.0,
                    reputation_score=74.0,
                    audience_size=120000,
                    is_public=True,
                    default_reality_mode="hybrid",
                    metadata_json={"region": "Africa"},
                ),
                FanPredictionFixture(
                    id="prediction-lagos-final",
                    match_id="match-lagos-final",
                    competition_id="competition-lagos-final",
                    home_club_id=club.id,
                    away_club_id=rival_club.id,
                    created_by_user_id=admin.id,
                    title="Lagos final prediction card",
                    description="Predict the Lagos Continental Cup first scorer and final winner.",
                    status=FanPredictionFixtureStatus.OPEN,
                    opens_at=now - timedelta(hours=1),
                    locks_at=now + timedelta(hours=8),
                    token_cost=2,
                    promo_pool_fancoin=Decimal("50.0000"),
                ),
                FanWarProfile(
                    id="fan-war-lagos",
                    profile_type="club",
                    entity_key="club:arsenal-lagos",
                    display_name="Lagos Fan War",
                    slug="lagos-fan-war",
                    club_id=club.id,
                    country_code="NG",
                    country_name="Nigeria",
                    tagline="Lagos supporters push matchday energy.",
                    prestige_points=250,
                ),
                BroadcastRightsAuction(
                    id="broadcast-auction-lagos",
                    competition_id="competition-lagos-final",
                    seller_owner_id=owner.id,
                    reserve_price=Decimal("500.0000"),
                    revenue_share_percentage=Decimal("12.50"),
                    exclusivity=False,
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=30),
                    starts_at=now - timedelta(hours=1),
                    ends_at=now + timedelta(days=3),
                    status="auction_live",
                ),
                BroadcastRight(
                    id="broadcast-right-lagos",
                    competition_id="competition-lagos-final",
                    owner_id=owner.id,
                    acquisition_price=Decimal("750.0000"),
                    revenue_share_percentage=Decimal("15.00"),
                    exclusivity=True,
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=30),
                ),
                ClipVariant(
                    variant_id="clip-lagos-goal-vertical",
                    base_clip_id="clip-lagos-goal",
                    format_type="vertical",
                    view_count=2000,
                    watch_time=4500.0,
                    viral_score=91.0,
                    promotion_status="trending",
                    is_winner=True,
                ),
                SponsoredClip(
                    id="sponsored-clip-lagos",
                    advertiser_id="advertiser-lagos",
                    clip_id="clip-lagos-goal",
                    budget=Decimal("250.0000"),
                    bid_cpm=Decimal("4.5000"),
                    target_formats_json=["vertical"],
                    target_creators_json=["creator-lagos"],
                    target_regions_json=["NG"],
                    impressions_served=900,
                    start_time=now - timedelta(hours=1),
                    end_time=now + timedelta(days=1),
                    is_active=True,
                    clip_payload_json={"title": "Lagos goal sponsor"},
                ),
                TransferListing(
                    id="transfer-jude",
                    player_id=player.id,
                    selling_club_id=club.id,
                    base_price=Decimal("7500.00"),
                    current_highest_bid=Decimal("0.00"),
                    status="open",
                    listing_type="transfer",
                    asset_type="real_player",
                    visibility="public",
                    expires_at=now + timedelta(days=7),
                ),
                CoinTraderProfile(
                    id="trader-lagos",
                    user_id=owner.id,
                    display_name="Lagos Liquidity Desk",
                    country_code="NG",
                    status="approved",
                    tier="gold",
                    rating=4.8,
                    completion_rate=98.0,
                    liquidity_snapshot_json={"coin": "1000.0000"},
                ),
                CoinTradeOrder(
                    id="coin-order-owner",
                    trader_profile_id="trader-lagos",
                    user_id=owner.id,
                    direction="user_buys",
                    coin_unit=LedgerUnit.COIN,
                    coin_amount=Decimal("50.0000"),
                    quoted_rate_fiat=Decimal("1200.0000"),
                    fiat_total=Decimal("60000.0000"),
                    fiat_currency="NGN",
                    status="accepted",
                ),
                StadiumEvent(
                    id="event-lagos-final",
                    stadium_id="stadium-lagos",
                    match_id="match-lagos-final",
                    title="Lagos Derby Final",
                    venue_name="GTEX Arena",
                    event_type="cup",
                    event_status="on_sale",
                    capacity=50000,
                    tier_distribution_json={"regular": 40000, "vip": 10000},
                    base_price_json={"regular": "20.0000", "vip": "100.0000"},
                    public_sales_starts_at=now - timedelta(hours=1),
                    sales_close_at=now + timedelta(days=1),
                    resale_ticket_count=1,
                ),
                StadiumTicket(
                    id="ticket-resale-vip",
                    event_id="event-lagos-final",
                    user_id=owner.id,
                    match_id="match-lagos-final",
                    seat_tier="vip",
                    seat_code="VIP-10",
                    price=Decimal("100.0000"),
                    original_price=Decimal("100.0000"),
                    status="available",
                    resale_listing_price=Decimal("125.0000"),
                    listed_at=now,
                ),
                PlayerCardTier(
                    id="tier-gold",
                    code="gold",
                    name="Gold",
                    rarity_rank=2,
                    max_supply=1000,
                    supply_multiplier=Decimal("1.0000"),
                    base_mint_price_credits=Decimal("10.0000"),
                    is_active=True,
                ),
                PlayerCard(
                    id="card-jude-gold",
                    player_id=player.id,
                    tier_id="tier-gold",
                    edition_code="founders",
                    display_name="Jude Bellingham Gold",
                    season_label="2026",
                    card_variant="base",
                    supply_total=100,
                    supply_available=50,
                    is_active=True,
                ),
                PlayerCardListing(
                    id="card-listing-row",
                    listing_id="card-listing-jude-gold",
                    player_card_id="card-jude-gold",
                    seller_user_id=owner.id,
                    quantity=3,
                    price_per_card_credits=Decimal("88.0000"),
                    status="open",
                    is_negotiable=True,
                    expires_at=now + timedelta(days=3),
                ),
            ]
        )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def client(session: Session) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(global_search_router, prefix="/api")
    app.include_router(notifications_admin_router, prefix="/api")

    def override_session() -> Iterator[Session]:
        yield session

    def override_current_user() -> User:
        user = session.get(User, "user-owner")
        assert user is not None
        return user

    def override_current_admin() -> User:
        user = session.get(User, "user-admin")
        assert user is not None
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_current_admin] = override_current_admin
    with TestClient(app) as test_client:
        yield test_client


def test_global_search_returns_role_safe_user_results(client: TestClient) -> None:
    response = client.get("/api/search", params={"q": "Jude", "limit": 10})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload[0]["type"] == "player"
    assert payload[0]["title"] == "Jude Bellingham"
    assert all(item["permission_required"] is None for item in payload)


def test_admin_search_includes_admin_targets(client: TestClient) -> None:
    response = client.get("/api/admin/search", params={"q": "owner", "limit": 10})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(item["type"] == "admin_user" and item["permission_required"] == "admin" for item in payload)


def test_global_search_indexes_live_product_loops(client: TestClient) -> None:
    search_terms = {
        "transfer_listing": "Jude",
        "coin_trader": "Liquidity",
        "regen": "Kelechi",
        "staff": "Adaeze",
        "sponsor_package": "Front Shirt",
        "federation": "Africa",
        "fan_prediction": "first scorer",
        "fan_war": "supporters",
        "broadcast_auction": "auction_live",
        "broadcast_right": "broadcast-right-lagos",
        "viral_clip": "vertical",
        "sponsored_clip": "advertiser-lagos",
        "ticket_event": "Derby",
        "ticket_resale": "VIP-10",
        "player_card_listing": "founders",
    }

    for expected_type, query in search_terms.items():
        response = client.get("/api/search", params={"q": query, "limit": 20})

        assert response.status_code == 200, response.text
        payload = response.json()
        assert any(item["type"] == expected_type for item in payload), payload
        assert all(item["permission_required"] is None for item in payload)


def test_admin_search_indexes_coin_trade_orders(client: TestClient) -> None:
    response = client.get("/api/admin/search", params={"q": "accepted", "limit": 20})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(
        item["type"] == "admin_coin_order" and item["permission_required"] == "admin"
        for item in payload
    )


def test_admin_search_indexes_command_router_catalog(client: TestClient) -> None:
    response = client.get("/api/admin/search", params={"q": "academy", "limit": 20})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(
        item["type"] == "admin_command_route"
        and item["id"] == "academy_regens"
        and item["permission_required"] == "admin"
        for item in payload
    )


def test_notification_event_matrix_and_test_event(client: TestClient, session: Session) -> None:
    matrix = client.get("/api/admin/notifications/event-matrix")
    assert matrix.status_code == 200, matrix.text
    event_keys = {item["event_key"] for item in matrix.json()}
    assert "academy_regen_generated" in event_keys
    assert "club_readiness_complete" in event_keys

    created = client.post(
        "/api/admin/notifications/test-event",
        json={
            "event_key": "academy_regen_generated",
            "target_user_id": "user-owner",
            "resource_id": "prospect-1",
            "metadata_json": {"club_id": "club-arsenal"},
        },
    )

    assert created.status_code == 200, created.text
    assert created.json()["notification"]["topic"] == "club"
    record = session.scalar(
        select(NotificationRecord).where(NotificationRecord.resource_type == "academy_regen_generated")
    )
    assert record is not None
    assert record.metadata_json["deep_link_route"] == "/app/club"
