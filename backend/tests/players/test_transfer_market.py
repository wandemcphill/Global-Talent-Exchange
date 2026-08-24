from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_session
from app.auth.service import AuthService
from app.common.enums.contract_status import ContractStatus
from app.ingestion.models import Club as IngestionClub
from app.ingestion.models import Competition, Player, Season
from app.models.access_control import Organization, OrganizationMembership  # noqa: F401
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.transfer_bid import TransferBid
from app.models.transfer_market import CoachProfile, TransferHubOffer, TransferListing, TransferNegotiation
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
    buyer_player = Player(
        id="player-2",
        source_provider="test",
        provider_external_id="player-2",
        current_club_id=buyer_ingestion_club.id,
        current_club_profile_id=buyer_profile.id,
        current_competition_id=competition.id,
        full_name="River Midfielder",
        normalized_position="midfielder",
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
            buyer_player,
            contract,
            window,
        ]
    )
    session.commit()
    access_service = AccessControlService(session)
    access_service.ensure_club_organization(seller_profile, owner_user_id=seller_user.id)
    access_service.ensure_club_organization(buyer_profile, owner_user_id=buyer_user.id)
    session.commit()
    return {
        "player_id": player.id,
        "buyer_player_id": buyer_player.id,
        "seller_club_id": seller_profile.id,
        "buyer_club_id": buyer_profile.id,
        "seller_user_id": seller_user.id,
        "buyer_user_id": buyer_user.id,
        "window_id": window.id,
    }


def _auth_headers(session: Session, *, user_id: str) -> dict[str, str]:
    user = session.get(User, user_id)
    assert user is not None
    token, _expires_in, _session_id = AuthService().issue_access_token_with_session(user, session=session)
    return {"Authorization": f"Bearer {token}"}


def test_transfer_market_bid_extends_auction_window(
    transfer_market_api: TestClient, transfer_market_session: Session
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])
    expires_at = datetime.now(UTC) + timedelta(seconds=20)
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "1500000.00",
            "expires_at": expires_at.isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )
    assert listing_response.status_code == 201
    listing_id = listing_response.json()["id"]

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "amount": "1700000.00",
            "activity_context": "aggressive_push",
        },
        headers=buyer_headers,
    )
    assert bid_response.status_code == 200
    payload = bid_response.json()
    assert payload["current_highest_bid"] == "1700000.00"
    assert payload["bid_count"] == 1
    assert datetime.fromisoformat(payload["expires_at"]) > expires_at


def test_transfer_hub_supports_loan_swap_offer_lifecycle(
    transfer_market_api: TestClient, transfer_market_session: Session
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])
    listing_response = transfer_market_api.post(
        "/api/transfer-hub/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "800000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=3)).isoformat(),
            "window_id": context["window_id"],
            "listing_type": "loan_to_buy",
            "asset_type": "real_player",
            "visibility": "public",
            "salary_amount": "25000.00",
            "contract_years_remaining": "2.50",
            "buy_clause_amount": "1200000.00",
            "loan_terms": {"months": 12, "wage_share_pct": 60},
            "swap_terms": {"minimum_rating": 70, "positions": ["midfielder"]},
            "availability": {"loan": True, "swap": True, "loan_to_buy": True},
        },
        headers=seller_headers,
    )
    assert listing_response.status_code == 201
    listing_payload = listing_response.json()
    assert listing_payload["listing_type"] == "loan_to_buy"
    assert listing_payload["loan_terms"]["months"] == 12
    assert listing_payload["swap_terms"]["minimum_rating"] == 70

    offer_body = {
        "bidder_club_id": context["buyer_club_id"],
        "offer_type": "swap_plus_cash",
        "cash_amount": "300000.00",
        "offered_player_ids": [context["buyer_player_id"]],
        "loan_terms": {"months": 12},
        "swap_terms": {"sell_on_pct": 10},
        "conditional_terms": {"must_include_position": "midfielder"},
        "idempotency_key": "offer-key-123",
    }
    offer_response = transfer_market_api.post(
        f"/api/transfer-hub/listings/{listing_payload['id']}/offers",
        json=offer_body,
        headers=buyer_headers,
    )
    assert offer_response.status_code == 201
    offer_payload = offer_response.json()
    assert offer_payload["status"] == "open"
    assert offer_payload["offered_player_ids"] == [context["buyer_player_id"]]

    repeat_response = transfer_market_api.post(
        f"/api/transfer-hub/listings/{listing_payload['id']}/offers",
        json=offer_body,
        headers=buyer_headers,
    )
    assert repeat_response.status_code == 201
    assert repeat_response.json()["id"] == offer_payload["id"]

    accept_response = transfer_market_api.post(
        f"/api/transfer-hub/offers/{offer_payload['id']}/accept",
        headers=seller_headers,
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"
    offer = transfer_market_session.get(TransferHubOffer, offer_payload["id"])
    assert offer is not None
    listing = transfer_market_session.get(TransferListing, listing_payload["id"])
    assert listing is not None
    assert listing.status == "accepted"


def test_transfer_market_completes_transfer_after_player_and_coach_approval(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "2000000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
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
        headers=seller_headers,
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
        headers=buyer_headers,
    )
    assert coach_profile_response.status_code == 200

    coach_demand_response = transfer_market_api.post(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/demands",
        json={"need": "forward", "urgency": "high"},
        headers=buyer_headers,
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
        headers=buyer_headers,
    )
    assert dynamics_response.status_code == 200

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "amount": "2500000.00",
        },
        headers=buyer_headers,
    )
    assert bid_response.status_code == 200

    close_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/close",
        headers=seller_headers,
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"

    contract_offer_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/contract-offer",
        json={
            "wage_offer_amount": "2200.00",
            "contract_years": 4,
            "expected_role": "starter",
            "release_clause_amount": "9000000.00",
            "bonus_terms": "Goal bonus",
            "notes": "Move fast",
        },
        headers=buyer_headers,
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
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "1800000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
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
        headers=seller_headers,
    )
    transfer_market_api.put(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/profile",
        json={
            "personality_json": {"discipline": 95},
            "tactical_philosophy": "possession",
            "authority_level": 95,
            "transfer_preference": "control",
        },
        headers=buyer_headers,
    )
    transfer_market_api.post(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/demands",
        json={"need": "defensive_midfielder", "urgency": "high"},
        headers=buyer_headers,
    )
    transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "amount": "2050000.00",
        },
        headers=buyer_headers,
    )
    transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/close",
        headers=seller_headers,
    )

    contract_offer_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/contract-offer",
        json={
            "wage_offer_amount": "2300.00",
            "contract_years": 4,
            "expected_role": "starter",
        },
        headers=buyer_headers,
    )
    assert contract_offer_response.status_code == 200
    negotiation_payload = contract_offer_response.json()
    assert negotiation_payload["status"] == "coach_blocked"
    assert negotiation_payload["coach_opinion"]["stance"] == "reject"

    listing = transfer_market_session.get(TransferListing, listing_id)
    assert listing is not None
    assert listing.status == "closed"
    assert (
        transfer_market_session.scalar(select(TransferNegotiation).where(TransferNegotiation.listing_id == listing_id))
        is not None
    )
    assert (
        transfer_market_session.scalar(select(TransferBid).where(TransferBid.player_id == context["player_id"])) is None
    )
    assert (
        transfer_market_session.scalar(select(CoachProfile).where(CoachProfile.club_id == context["buyer_club_id"]))
        is not None
    )


def test_transfer_market_watchlist_uses_authenticated_club_context(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])

    response = transfer_market_api.post(
        "/api/transfer-market/watchlist",
        json={
            "player_id": context["player_id"],
            "source": "scouting",
            "discovery_score": 74,
        },
        headers=buyer_headers,
    )

    assert response.status_code == 201
    assert response.json()["club_id"] == context["buyer_club_id"]
    assert response.json()["player_id"] == context["player_id"]


def test_transfer_market_rejects_spoofed_selling_club_id(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])

    response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "selling_club_id": context["buyer_club_id"],
            "base_price": "1600000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "transfer_market_club_access_required"


def test_transfer_market_rejects_spoofed_bidder_club_id(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])
    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "1500000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )
    listing_id = listing_response.json()["id"]

    response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={
            "bidder_club_id": context["seller_club_id"],
            "amount": "1700000.00",
        },
        headers=buyer_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "transfer_market_club_access_required"


def test_transfer_market_rejects_preseeded_national_regen_listing(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    seed = NationalRegenSeed(
        seed_key="seed:transfer:block",
        display_name="Cheikh Sarr",
        age=19,
        age_band="u20",
        country_code="SN",
        country_name="Senegal",
        seed_type="preseeded_national_pool",
        primary_position="ST",
        current_rating=71,
        potential_rating=85,
        growth_curve=0.73,
        rarity_tier="rare",
        status="available",
        metadata_json={},
    )
    transfer_market_session.add(seed)
    transfer_market_session.commit()

    response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": seed.id,
            "base_price": "1500000.00",
            "expires_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Preseeded national regens are national-pool-only and cannot be transfer listed."
    )


@pytest.mark.parametrize(
    ("method", "path_builder", "payload_builder"),
    [
        (
            "post",
            lambda _context, _listing_id: "/api/transfer-market/listings",
            lambda context: {
                "player_id": context["player_id"],
                "base_price": "1500000.00",
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "window_id": context["window_id"],
            },
        ),
        (
            "post",
            lambda _context, listing_id: f"/api/transfer-market/listings/{listing_id}/bids",
            lambda _context: {"amount": "1700000.00"},
        ),
        (
            "post",
            lambda _context, listing_id: f"/api/transfer-market/listings/{listing_id}/close",
            lambda _context: None,
        ),
        (
            "post",
            lambda _context, listing_id: f"/api/transfer-market/listings/{listing_id}/contract-offer",
            lambda _context: {
                "wage_offer_amount": "2100.00",
                "contract_years": 4,
                "expected_role": "starter",
            },
        ),
        (
            "put",
            lambda context, _listing_id: f"/api/transfer-market/players/{context['player_id']}/decision-profile",
            lambda _context: {
                "preferred_leagues_json": ["es"],
                "preferred_play_style": "pressing",
                "wage_expectation_amount": "1500.00",
                "ambition_level": 80,
                "happiness": 45,
                "loyalty": 35,
                "ambition": 84,
                "frustration": 12,
            },
        ),
        (
            "put",
            lambda context, _listing_id: f"/api/transfer-market/coaches/{context['buyer_club_id']}/profile",
            lambda _context: {
                "personality_json": {"discipline": 62},
                "tactical_philosophy": "pressing",
                "authority_level": 84,
                "transfer_preference": "pressing",
            },
        ),
        (
            "post",
            lambda context, _listing_id: f"/api/transfer-market/coaches/{context['buyer_club_id']}/demands",
            lambda _context: {
                "need": "forward",
                "urgency": "high",
            },
        ),
        (
            "put",
            lambda context, _listing_id: f"/api/transfer-market/clubs/{context['buyer_club_id']}/team-dynamics",
            lambda _context: {
                "leaders_json": [],
                "cliques_json": [],
                "morale_groups_json": [],
                "chemistry_risk": 8,
            },
        ),
        (
            "post",
            lambda _context, _listing_id: "/api/transfer-market/watchlist",
            lambda context: {
                "player_id": context["player_id"],
                "source": "scouting",
                "discovery_score": 71,
            },
        ),
        ("post", lambda _context, _listing_id: "/api/transfer-market/jobs/run", lambda _context: {}),
    ],
)
def test_transfer_market_mutations_require_authentication(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
    method: str,
    path_builder,
    payload_builder,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])

    listing_response = transfer_market_api.post(
        "/api/transfer-market/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "1500000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )
    listing_id = listing_response.json()["id"]

    transfer_market_api.put(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/profile",
        json={
            "personality_json": {"discipline": 62},
            "tactical_philosophy": "pressing",
            "authority_level": 84,
            "transfer_preference": "pressing",
        },
        headers=buyer_headers,
    )
    transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={"amount": "1800000.00"},
        headers=buyer_headers,
    )
    transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/close",
        headers=seller_headers,
    )

    path = path_builder(context, listing_id)
    payload = payload_builder(context)
    response = (
        getattr(transfer_market_api, method)(path, json=payload)
        if payload is not None
        else getattr(transfer_market_api, method)(path)
    )

    assert response.status_code == 401


def test_transfer_hub_offer_list_is_scoped_to_authenticated_club(
    transfer_market_api: TestClient, transfer_market_session: Session
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    buyer_headers = _auth_headers(transfer_market_session, user_id=context["buyer_user_id"])
    listing_response = transfer_market_api.post(
        "/api/transfer-hub/listings",
        json={
            "player_id": context["player_id"],
            "base_price": "800000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=3)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )
    assert listing_response.status_code == 201
    listing_id = listing_response.json()["id"]
    offer_response = transfer_market_api.post(
        f"/api/transfer-hub/listings/{listing_id}/offers",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "offer_type": "cash",
            "cash_amount": "900000.00",
        },
        headers=buyer_headers,
    )
    assert offer_response.status_code == 201

    buyer_list = transfer_market_api.get("/api/transfer-hub/offers", headers=buyer_headers)
    assert buyer_list.status_code == 200
    assert len(buyer_list.json()) == 1

    stranger = User(
        id="user-stranger",
        email="stranger@example.com",
        username="stranger",
        display_name="Stranger",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    transfer_market_session.add(stranger)
    transfer_market_session.commit()
    stranger_headers = _auth_headers(transfer_market_session, user_id=stranger.id)
    stranger_list = transfer_market_api.get("/api/transfer-hub/offers", headers=stranger_headers)
    assert stranger_list.status_code == 403
