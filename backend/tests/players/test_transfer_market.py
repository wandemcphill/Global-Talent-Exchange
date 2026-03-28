from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_session
from app.common.enums.contract_status import ContractStatus
from app.ingestion.models import Club as IngestionClub
from app.ingestion.models import Competition, Player, Season
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.transfer_bid import TransferBid
from app.models.transfer_market import CoachProfile, TransferListing, TransferNegotiation
from app.models.transfer_window import TransferWindow
from app.models.user import KycStatus, User, UserRole
from app.regen_universe import models as _regen_universe_models  # noqa: F401
from app.transfer_market.router import router


@pytest.fixture()
def transfer_market_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _configure_test_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture()
def transfer_market_api(transfer_market_session: Session):
    app = FastAPI()
    app.include_router(router)

    def _session_override():
        yield transfer_market_session

    app.dependency_overrides[get_session] = _session_override
    with TestClient(app) as client:
        yield client


def seed_transfer_market_context(session: Session) -> dict[str, str]:
    seller_user = User(
        id="user-seller",
        email="seller@example.com",
        username="seller",
        display_name="Seller",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    buyer_user = User(
        id="user-buyer",
        email="buyer@example.com",
        username="buyer",
        display_name="Buyer",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    seller_profile = ClubProfile(
        id="club-profile-metro",
        owner_user_id=seller_user.id,
        club_name="Metro FC",
        short_name="MFC",
        slug="metro-fc",
        primary_color="#112233",
        secondary_color="#445566",
        accent_color="#ddeeff",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    buyer_profile = ClubProfile(
        id="club-profile-river",
        owner_user_id=buyer_user.id,
        club_name="River FC",
        short_name="RFC",
        slug="river-fc",
        primary_color="#223344",
        secondary_color="#ffffff",
        accent_color="#ff9900",
        country_code="ES",
        region_name="Madrid",
        city_name="Madrid",
    )
    competition = Competition(
        id="competition-premier",
        source_provider="test",
        provider_external_id="competition-premier",
        name="Premier League",
        slug="premier-league",
    )
    season = Season(
        id="season-current",
        source_provider="test",
        provider_external_id="season-current",
        competition_id=competition.id,
        label="2025/26",
        year_start=2025,
        year_end=2026,
        season_status="in_progress",
    )
    seller_ingestion_club = IngestionClub(
        id="ing-club-metro",
        source_provider="test",
        provider_external_id="metro-fc",
        current_competition_id=competition.id,
        name="Metro FC",
        slug="metro-fc",
    )
    buyer_ingestion_club = IngestionClub(
        id="ing-club-river",
        source_provider="test",
        provider_external_id="river-fc",
        current_competition_id=competition.id,
        name="River FC",
        slug="river-fc",
    )
    player = Player(
        id="player-1",
        source_provider="test",
        provider_external_id="player-1",
        current_club_id=seller_ingestion_club.id,
        current_club_profile_id=seller_profile.id,
        current_competition_id=competition.id,
        full_name="Ayo Forward",
        normalized_position="forward",
    )
    contract = PlayerContract(
        id="contract-1",
        player_id=player.id,
        club_id=seller_profile.id,
        status=ContractStatus.ACTIVE.value,
        wage_amount=Decimal("1200.00"),
        signed_on=date(2025, 7, 1),
        starts_on=date(2025, 7, 1),
        ends_on=date(2027, 6, 30),
    )
    window = TransferWindow(
        id="window-1",
        territory_code="NG",
        label="Summer Window",
        status="open",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 12, 31),
    )
    session.add_all(
        [
            seller_user,
            buyer_user,
            seller_profile,
            buyer_profile,
            competition,
            season,
            seller_ingestion_club,
            buyer_ingestion_club,
            player,
            contract,
            window,
        ]
    )
    session.commit()
    return {
        "player_id": player.id,
        "seller_club_id": seller_profile.id,
        "buyer_club_id": buyer_profile.id,
        "window_id": window.id,
    }


def test_transfer_market_bid_extends_auction_window(transfer_market_api: TestClient, transfer_market_session: Session) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    expires_at = datetime.now(UTC) + timedelta(seconds=20)
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "selling_club_id": context["seller_club_id"],
            "base_price": "1500000.00",
            "expires_at": expires_at.isoformat(),
            "window_id": context["window_id"],
        },
    )
    assert listing_response.status_code == 201
    listing_id = listing_response.json()["id"]

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "amount": "1700000.00",
            "activity_context": "aggressive_push",
        },
    )
    assert bid_response.status_code == 200
    payload = bid_response.json()
    assert payload["current_highest_bid"] == "1700000.00"
    assert payload["bid_count"] == 1
    assert datetime.fromisoformat(payload["expires_at"]) > expires_at


def test_transfer_market_completes_transfer_after_player_and_coach_approval(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "selling_club_id": context["seller_club_id"],
            "base_price": "2000000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "window_id": context["window_id"],
        },
    )
    assert listing_response.status_code == 201
    listing_id = listing_response.json()["id"]

    decision_profile_response = transfer_market_api.put(
        f"/api/transfer-market/players/{context['player_id']}/decision-profile",
        json={
            "preferred_leagues_json": ["es"],
            "preferred_play_style": "pressing",
            "wage_expectation_amount": "1500.00",
            "ambition_level": 82,
            "happiness": 42,
            "loyalty": 36,
            "ambition": 84,
            "frustration": 18,
        },
    )
    assert decision_profile_response.status_code == 200

    coach_profile_response = transfer_market_api.put(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/profile",
        json={
            "personality_json": {"discipline": 62},
            "tactical_philosophy": "pressing",
            "authority_level": 84,
            "transfer_preference": "pressing",
        },
    )
    assert coach_profile_response.status_code == 200

    coach_demand_response = transfer_market_api.post(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/demands",
        json={"need": "forward", "urgency": "high"},
    )
    assert coach_demand_response.status_code == 201

    dynamics_response = transfer_market_api.put(
        f"/api/transfer-market/clubs/{context['buyer_club_id']}/team-dynamics",
        json={
            "leaders_json": [],
            "cliques_json": [],
            "morale_groups_json": [],
            "chemistry_risk": 8,
        },
    )
    assert dynamics_response.status_code == 200

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "amount": "2500000.00",
        },
    )
    assert bid_response.status_code == 200

    close_response = transfer_market_api.post(f"/api/transfer-market/listings/{listing_id}/close")
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"

    contract_offer_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/contract-offer",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "wage_offer_amount": "2200.00",
            "contract_years": 4,
            "expected_role": "starter",
            "release_clause_amount": "9000000.00",
            "bonus_terms": "Goal bonus",
            "notes": "Move fast",
        },
    )
    assert contract_offer_response.status_code == 200
    negotiation_payload = contract_offer_response.json()
    assert negotiation_payload["status"] == "completed"
    assert negotiation_payload["player_decision"]["action"] == "accept"
    assert negotiation_payload["coach_opinion"]["stance"] == "approve"

    refreshed_listing = transfer_market_api.get(f"/api/transfer-market/listings/{listing_id}")
    assert refreshed_listing.status_code == 200
    assert refreshed_listing.json()["status"] == "sold"

    completed_contract = transfer_market_session.scalar(
        select(PlayerContract)
        .where(PlayerContract.player_id == context["player_id"])
        .order_by(PlayerContract.created_at.desc())
    )
    assert completed_contract is not None
    assert completed_contract.club_id == context["buyer_club_id"]

    lifecycle_bid = transfer_market_session.scalar(
        select(TransferBid).where(TransferBid.player_id == context["player_id"]).order_by(TransferBid.created_at.desc())
    )
    assert lifecycle_bid is not None
    assert lifecycle_bid.buying_club_id == context["buyer_club_id"]


def test_transfer_market_blocks_move_when_coach_strongly_disagrees(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "selling_club_id": context["seller_club_id"],
            "base_price": "1800000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "window_id": context["window_id"],
        },
    )
    listing_id = listing_response.json()["id"]

    transfer_market_api.put(
        f"/api/transfer-market/players/{context['player_id']}/decision-profile",
        json={
            "preferred_leagues_json": ["es"],
            "preferred_play_style": "pressing",
            "wage_expectation_amount": "1400.00",
            "ambition_level": 76,
            "happiness": 35,
            "loyalty": 30,
            "ambition": 82,
            "frustration": 20,
        },
    )
    transfer_market_api.put(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/profile",
        json={
            "personality_json": {"discipline": 95},
            "tactical_philosophy": "possession",
            "authority_level": 95,
            "transfer_preference": "control",
        },
    )
    transfer_market_api.post(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/demands",
        json={"need": "defensive_midfielder", "urgency": "high"},
    )
    transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "amount": "2050000.00",
        },
    )
    transfer_market_api.post(f"/api/transfer-market/listings/{listing_id}/close")

    contract_offer_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/contract-offer",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "wage_offer_amount": "2300.00",
            "contract_years": 4,
            "expected_role": "starter",
        },
    )
    assert contract_offer_response.status_code == 200
    negotiation_payload = contract_offer_response.json()
    assert negotiation_payload["status"] == "coach_blocked"
    assert negotiation_payload["coach_opinion"]["stance"] == "reject"

    listing = transfer_market_session.get(TransferListing, listing_id)
    assert listing is not None
    assert listing.status == "closed"
    assert transfer_market_session.scalar(
        select(TransferNegotiation).where(TransferNegotiation.listing_id == listing_id)
    ) is not None
    assert transfer_market_session.scalar(select(TransferBid).where(TransferBid.player_id == context["player_id"])) is None
    assert transfer_market_session.scalar(select(CoachProfile).where(CoachProfile.club_id == context["buyer_club_id"])) is not None
