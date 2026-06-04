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
from app.auth.security import hash_sensitive_secret
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
from app.models.transfer_market import (
    CoachProfile,
    MarketWatchlistEntry,
    TransferListing,
    TransferListingBid,
    TransferNegotiation,
)
from app.models.transfer_window import TransferWindow
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.regen_universe import models as _regen_universe_models  # noqa: F401
from app.transfer_market.router import router
from app.transfer_market.schemas import ContractOfferRequest, TransferListingCreateRequest
from app.transfer_market.service import TransferMarketService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


class _MemoryCacheBackend:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        del ttl_seconds
        self.values[key] = value


_PIN_CACHE = _MemoryCacheBackend()


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
    _PIN_CACHE.values.clear()
    app.state.cache_backend = _PIN_CACHE
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
        pin_hash=hash_sensitive_secret("1234"),
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    buyer_user = User(
        id="user-buyer",
        email="buyer@example.com",
        username="buyer",
        display_name="Buyer",
        password_hash="x",
        pin_hash=hash_sensitive_secret("1234"),
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
    access_service = AccessControlService(session)
    access_service.ensure_club_organization(seller_profile, owner_user_id=seller_user.id)
    access_service.ensure_club_organization(buyer_profile, owner_user_id=buyer_user.id)
    _fund_coin(session, buyer_user.id, Decimal("10000000.0000"))
    session.commit()
    return {
        "player_id": player.id,
        "seller_club_id": seller_profile.id,
        "buyer_club_id": buyer_profile.id,
        "seller_user_id": seller_user.id,
        "buyer_user_id": buyer_user.id,
        "window_id": window.id,
    }


def _fund_coin(session: Session, user_id: str, amount: Decimal) -> None:
    user = session.get(User, user_id)
    assert user is not None
    wallet_service = WalletService()
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(
                account=wallet_service.ensure_platform_account(session, LedgerUnit.COIN),
                amount=-amount,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            ),
            LedgerPosting(
                account=wallet_service.get_user_account(session, user, LedgerUnit.COIN),
                amount=amount,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            ),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"test-transfer-market-fund:{user_id}",
        description="Test transfer-market wallet funding",
        actor=user,
    )


def _coin_summary(session: Session, user_id: str):
    user = session.get(User, user_id)
    assert user is not None
    return WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)


def _auth_headers(session: Session, *, user_id: str) -> dict[str, str]:
    user = session.get(User, user_id)
    assert user is not None
    issued = AuthService().issue_session_tokens(
        user,
        session=session,
        device_id=f"test-device-{user_id}",
    )
    _PIN_CACHE.set(f"auth:pin:{user.id}:{issued.session_id}:transfer_market.bid", "1")
    return {
        "Authorization": f"Bearer {issued.access_token}",
        "X-Session-Id": issued.session_id,
        "X-Device-Id": issued.trusted_device_id or f"test-device-{user_id}",
    }


def test_wallet_strict_transfer_bid_settlement_requires_reserved_hold(
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    buyer = transfer_market_session.get(User, context["buyer_user_id"])
    assert buyer is not None
    wallet_service = WalletService()
    wallet_service.reserve_transfer_bid_funds(
        transfer_market_session,
        user=buyer,
        transfer_bid_id="strict-reservation-bid",
        amount=Decimal("1000.00"),
        unit=LedgerUnit.COIN,
        reference="strict-reservation-bid",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    wallet_service.release_transfer_bid_reservation(
        transfer_market_session,
        user=buyer,
        transfer_bid_id="strict-reservation-bid",
        amount=Decimal("400.00"),
        unit=LedgerUnit.COIN,
        release_reason="test_partial_release",
        reference="strict-reservation-bid",
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )

    with pytest.raises(InsufficientBalanceError):
        wallet_service.settle_transfer_bid_reservation(
            transfer_market_session,
            user=buyer,
            transfer_bid_id="strict-reservation-bid",
            amount=Decimal("1000.00"),
            unit=LedgerUnit.COIN,
            reference="strict-reservation-bid",
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            require_full_reservation=True,
        )

    summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert summary.available_balance == Decimal("9999400.0000")
    assert summary.reserved_balance == Decimal("600.0000")


def test_transfer_market_completion_reuses_listing_reservation_without_double_hold(
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    service = TransferMarketService(transfer_market_session)
    seller = transfer_market_session.get(User, context["seller_user_id"])
    buyer = transfer_market_session.get(User, context["buyer_user_id"])
    assert seller is not None
    assert buyer is not None

    listing = service.create_listing(
        TransferListingCreateRequest(
            player_id=context["player_id"],
            base_price=Decimal("9500000.00"),
            expires_at=datetime.now(UTC) + timedelta(hours=2),
            window_id=context["window_id"],
        ),
        actor=seller,
    )
    service.place_bid(
        listing.id,
        actor=buyer,
        bidder_club_id=context["buyer_club_id"],
        amount=Decimal("10000000.00"),
    )
    service.finalize_listing(listing.id, actor=seller)

    negotiation = service.submit_contract_offer(
        listing.id,
        ContractOfferRequest(
            bidder_club_id=context["buyer_club_id"],
            wage_offer_amount=Decimal("2200.00"),
            contract_years=4,
            expected_role="starter",
        ),
        actor=buyer,
        bidder_club_id=context["buyer_club_id"],
    )

    assert negotiation.status == "completed"
    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    seller_summary = _coin_summary(transfer_market_session, context["seller_user_id"])
    assert buyer_summary.available_balance == Decimal("0.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")
    assert seller_summary.available_balance == Decimal("10000000.0000")


def test_transfer_market_get_listing_finalizes_expired_auction_and_stale_offer_releases_hold(
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    service = TransferMarketService(transfer_market_session)
    seller = transfer_market_session.get(User, context["seller_user_id"])
    buyer = transfer_market_session.get(User, context["buyer_user_id"])
    assert seller is not None
    assert buyer is not None
    admin = User(
        id="transfer-market-admin",
        email="tm-admin@example.com",
        username="tm-admin",
        display_name="Transfer Admin",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    transfer_market_session.add(admin)
    transfer_market_session.commit()

    now = datetime.now(UTC)
    listing = service.create_listing(
        TransferListingCreateRequest(
            player_id=context["player_id"],
            base_price=Decimal("2000000.00"),
            expires_at=now + timedelta(minutes=5),
            window_id=context["window_id"],
        ),
        actor=seller,
        reference_at=now,
    )
    service.place_bid(
        listing.id,
        actor=buyer,
        bidder_club_id=context["buyer_club_id"],
        amount=Decimal("2500000.00"),
        reference_at=now,
    )

    expired_view = service.get_listing(listing.id, reference_at=now + timedelta(minutes=6))
    assert expired_view.status == "closed"
    negotiation = transfer_market_session.scalar(
        select(TransferNegotiation).where(TransferNegotiation.listing_id == listing.id)
    )
    assert negotiation is not None
    assert negotiation.status == "awaiting_contract_offer"
    assert _coin_summary(transfer_market_session, context["buyer_user_id"]).reserved_balance == Decimal(
        "2500000.0000"
    )

    job_view = service.run_background_jobs(
        actor=admin,
        reference_at=negotiation.decision_due_at + timedelta(seconds=1),
    )

    assert job_view.collapsed_negotiations == 1
    transfer_market_session.refresh(negotiation)
    assert negotiation.status == "collapsed"
    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("10000000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")


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
    assert payload["current_bid"]["wallet_reservation_status"] == "reserved"
    assert payload["current_bid"]["wallet_reserved_amount"] == "1700000.0000"

    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("8300000.0000")
    assert buyer_summary.reserved_balance == Decimal("1700000.0000")

    raised_bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={"amount": "1800000.00"},
        headers=buyer_headers,
    )
    assert raised_bid_response.status_code == 200
    raised_payload = raised_bid_response.json()
    assert raised_payload["current_bid"]["wallet_reservation_status"] == "reserved"
    assert raised_payload["current_bid"]["wallet_reserved_amount"] == "1800000.0000"
    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("8200000.0000")
    assert buyer_summary.reserved_balance == Decimal("1800000.0000")


def test_transfer_market_close_releases_bid_when_reserve_price_is_not_met(
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
            "reserve_price": "2000000.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=seller_headers,
    )
    assert listing_response.status_code == 201
    listing_id = listing_response.json()["id"]

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={"amount": "1700000.00"},
        headers=buyer_headers,
    )
    assert bid_response.status_code == 200
    assert _coin_summary(transfer_market_session, context["buyer_user_id"]).reserved_balance == Decimal(
        "1700000.0000"
    )

    close_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/close",
        headers=seller_headers,
    )
    assert close_response.status_code == 200
    payload = close_response.json()
    assert payload["status"] == "closed"
    assert payload["current_bid"]["wallet_reservation_status"] == "released"
    assert (
        transfer_market_session.scalar(select(TransferNegotiation).where(TransferNegotiation.listing_id == listing_id))
        is None
    )
    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("10000000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")


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
    reservation = dict((lifecycle_bid.structured_terms_json or {}).get("wallet_reservation") or {})
    assert reservation["status"] == "settled"
    assert reservation["transfer_market_listing_id"] == listing_id
    listing_bid = transfer_market_session.scalar(
        select(TransferListingBid).where(TransferListingBid.listing_id == listing_id)
    )
    assert listing_bid is not None
    listing_bid_reservation = dict((listing_bid.metadata_json or {}).get("wallet_reservation") or {})
    assert listing_bid_reservation["status"] == "settled"
    assert listing_bid_reservation["lifecycle_transfer_bid_id"] == lifecycle_bid.id

    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    seller_summary = _coin_summary(transfer_market_session, context["seller_user_id"])
    assert buyer_summary.available_balance == Decimal("7500000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")
    assert seller_summary.available_balance == Decimal("2500000.0000")


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
    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("10000000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")


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


def test_market_players_filters_meta_and_detail_contract(
    transfer_market_api: TestClient,
    transfer_market_session: Session,
) -> None:
    context = seed_transfer_market_context(transfer_market_session)
    seller_headers = _auth_headers(transfer_market_session, user_id=context["seller_user_id"])
    player = transfer_market_session.get(Player, context["player_id"])
    assert player is not None
    player.date_of_birth = date(2001, 6, 2)
    player.current_market_reference_value = 1650000.0
    transfer_market_session.commit()

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
    assert listing_response.status_code == 201, listing_response.text
    listing_id = listing_response.json()["id"]

    search_response = transfer_market_api.get(
        "/api/transfer-market/players",
        params={"position": "forward", "page": 1, "page_size": 1},
    )
    assert search_response.status_code == 200, search_response.text
    search_payload = search_response.json()
    assert search_payload["pagination_mode"] == "page"
    assert search_payload["total"] == 1
    assert search_payload["has_next"] is False
    item = search_payload["items"][0]
    assert item["id"] == context["player_id"]
    assert item["name"] == "Ayo Forward"
    assert item["listing_id"] == listing_id
    assert item["availability"] == "available"
    assert item["checkout_eligible"] is True
    assert item["contract_end"] == "2027-06-30"

    detail_response = transfer_market_api.get(f"/api/transfer-market/players/{context['player_id']}")
    assert detail_response.status_code == 200, detail_response.text
    detail_payload = detail_response.json()
    assert detail_payload["listing_id"] == listing_id
    assert detail_payload["club"]["id"] == context["seller_club_id"]
    assert detail_payload["value"] == "1650000.0"

    meta_response = transfer_market_api.get("/api/transfer-market/filters/meta")
    assert meta_response.status_code == 200, meta_response.text
    meta = meta_response.json()
    assert meta["pagination_mode"] == "page"
    assert meta["positions"] == ["forward"]
    assert meta["availability_types"] == ["available", "injured", "suspended", "away", "unfit"]
    assert meta["bid_statuses"] == ["pending", "counter", "accepted", "rejected", "withdrawn"]
    assert [bracket["label"] for bracket in meta["value_brackets"]] == [
        "under_1m",
        "1m_to_5m",
        "5m_to_20m",
        "20m_plus",
    ]


def test_market_basket_bid_detail_activity_and_reservation_parity_contract(
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
    assert listing_response.status_code == 201, listing_response.text
    listing_id = listing_response.json()["id"]

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={"amount": "1700000.00"},
        headers=buyer_headers,
    )
    assert bid_response.status_code == 200, bid_response.text
    listing_payload = bid_response.json()
    bid = listing_payload["current_bid"]
    bid_id = bid["bid_id"]

    bid_detail_response = transfer_market_api.get(f"/api/transfer-market/bid/{bid_id}", headers=buyer_headers)
    assert bid_detail_response.status_code == 200, bid_detail_response.text
    bid_detail = bid_detail_response.json()
    assert bid_detail["id"] == bid_id
    assert bid_detail["listing_id"] == listing_id
    assert bid_detail["player_id"] == context["player_id"]
    assert bid_detail["status"] == "pending"
    assert bid_detail["wallet_reservation_status"] == bid["wallet_reservation_status"]
    assert bid_detail["wallet_reserved_amount"] == bid["wallet_reserved_amount"]
    assert bid_detail["wallet_reservation_reference"] == bid["wallet_reservation_reference"]
    assert bid_detail["events"][0]["type"] == "market.bid.placed"

    active_bids_response = transfer_market_api.get(
        "/api/transfer-market/bids",
        params={"clubId": context["buyer_club_id"]},
        headers=buyer_headers,
    )
    assert active_bids_response.status_code == 200, active_bids_response.text
    assert active_bids_response.json()[0]["id"] == bid_id

    basket_response = transfer_market_api.post(
        "/api/transfer-market/basket",
        json={"player_id": context["player_id"]},
        headers=buyer_headers,
    )
    assert basket_response.status_code == 201, basket_response.text
    basket_payload = basket_response.json()
    assert basket_payload["count"] == 1
    assert basket_payload["items"][0]["checkout_eligible"] is True
    assert basket_payload["items"][0]["listing_id"] == listing_id

    checkout_response = transfer_market_api.get("/api/transfer-market/checkout", headers=buyer_headers)
    assert checkout_response.status_code == 200, checkout_response.text
    assert checkout_response.json()["ready"] is True
    assert checkout_response.json()["blocked_reasons"] == []

    activity_response = transfer_market_api.get("/api/transfer-market/activity", params={"limit": 10})
    assert activity_response.status_code == 200, activity_response.text
    assert any(
        event["type"] == "market.bid.placed" and event["bid_id"] == bid_id
        for event in activity_response.json()
    )


def test_market_bid_withdraw_releases_wallet_reservation_and_persists_status(
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
    assert listing_response.status_code == 201, listing_response.text
    listing_id = listing_response.json()["id"]

    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={"amount": "1700000.00"},
        headers=buyer_headers,
    )
    assert bid_response.status_code == 200, bid_response.text
    bid_id = bid_response.json()["current_bid"]["bid_id"]
    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("8300000.0000")
    assert buyer_summary.reserved_balance == Decimal("1700000.0000")

    withdraw_response = transfer_market_api.post(
        f"/api/transfer-market/bid/{bid_id}/withdraw",
        json={"reason": "found better squad fit"},
        headers=buyer_headers,
    )
    assert withdraw_response.status_code == 200, withdraw_response.text
    withdrawn = withdraw_response.json()
    assert withdrawn["id"] == bid_id
    assert withdrawn["status"] == "withdrawn"
    assert withdrawn["wallet_reservation_status"] == "released"
    assert withdrawn["wallet_reserved_amount"] == "0.0000"

    buyer_summary = _coin_summary(transfer_market_session, context["buyer_user_id"])
    assert buyer_summary.available_balance == Decimal("10000000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")

    transfer_market_session.expire_all()
    persisted_bid = transfer_market_session.get(TransferListingBid, bid_id)
    assert persisted_bid is not None
    bid_metadata = dict(persisted_bid.metadata_json or {})
    assert bid_metadata["market_bid_status"] == "withdrawn"
    assert bid_metadata["withdrawn_reason"] == "found better squad fit"
    reservation = dict(bid_metadata["wallet_reservation"])
    assert reservation["status"] == "released"
    assert reservation["release_reason"] == "withdrawn"

    bid_detail_response = transfer_market_api.get(f"/api/transfer-market/bid/{bid_id}", headers=buyer_headers)
    assert bid_detail_response.status_code == 200, bid_detail_response.text
    assert bid_detail_response.json()["status"] == "withdrawn"


def test_market_checkout_submission_persists_basket_audit_marker(
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
    assert listing_response.status_code == 201, listing_response.text
    listing_id = listing_response.json()["id"]

    basket_response = transfer_market_api.post(
        "/api/transfer-market/basket",
        json={"player_id": context["player_id"]},
        headers=buyer_headers,
    )
    assert basket_response.status_code == 201, basket_response.text

    checkout_response = transfer_market_api.post(
        "/api/transfer-market/checkout",
        json={"idempotency_key": "checkout-audit-1", "notes": "ready for contract desk"},
        headers=buyer_headers,
    )
    assert checkout_response.status_code == 200, checkout_response.text
    checkout_payload = checkout_response.json()
    assert checkout_payload["ready"] is True
    assert checkout_payload["audit_ref"] == "checkout-audit-1"
    assert checkout_payload["blocked_reasons"] == []
    assert checkout_payload["items"][0]["listing_id"] == listing_id

    transfer_market_session.expire_all()
    basket_entry = transfer_market_session.scalar(
        select(MarketWatchlistEntry).where(
            MarketWatchlistEntry.club_id == context["buyer_club_id"],
            MarketWatchlistEntry.player_id == context["player_id"],
            MarketWatchlistEntry.source == "basket",
        )
    )
    assert basket_entry is not None
    attempts = list(dict(basket_entry.metadata_json or {}).get("checkout_attempts") or [])
    assert attempts == [
        {
            "audit_ref": "checkout-audit-1",
            "ready": True,
            "blocked_reasons": [],
            "submitted_at": attempts[0]["submitted_at"],
            "notes": "ready for contract desk",
        }
    ]


def test_market_history_returns_completed_transfer_contract(
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
    assert listing_response.status_code == 201, listing_response.text
    listing_id = listing_response.json()["id"]

    assert transfer_market_api.put(
        f"/api/transfer-market/players/{context['player_id']}/decision-profile",
        json={
            "preferred_leagues_json": ["es"],
            "preferred_play_style": "pressing",
            "wage_expectation_amount": "1500.00",
            "ambition_level": 80,
            "happiness": 45,
            "loyalty": 35,
            "ambition": 84,
            "frustration": 12,
        },
        headers=seller_headers,
    ).status_code == 200
    assert transfer_market_api.put(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/profile",
        json={
            "personality_json": {"discipline": 62},
            "tactical_philosophy": "pressing",
            "authority_level": 84,
            "transfer_preference": "pressing",
        },
        headers=buyer_headers,
    ).status_code == 200
    assert transfer_market_api.post(
        f"/api/transfer-market/coaches/{context['buyer_club_id']}/demands",
        json={"need": "forward", "urgency": "high"},
        headers=buyer_headers,
    ).status_code == 201
    assert transfer_market_api.put(
        f"/api/transfer-market/clubs/{context['buyer_club_id']}/team-dynamics",
        json={"leaders_json": [], "cliques_json": [], "morale_groups_json": [], "chemistry_risk": 8},
        headers=buyer_headers,
    ).status_code == 200
    bid_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/bids",
        json={"amount": "1800000.00"},
        headers=buyer_headers,
    )
    assert bid_response.status_code == 200, bid_response.text
    bid_id = bid_response.json()["current_bid"]["bid_id"]

    close_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/close",
        headers=seller_headers,
    )
    assert close_response.status_code == 200, close_response.text
    contract_offer_response = transfer_market_api.post(
        f"/api/transfer-market/listings/{listing_id}/contract-offer",
        json={
            "wage_offer_amount": "2200.00",
            "contract_years": 4,
            "expected_role": "starter",
            "release_clause_amount": "9000000.00",
            "bonus_terms": "Goal bonus",
            "notes": "Move fast",
            "bidder_club_id": context["buyer_club_id"],
        },
        headers=buyer_headers,
    )
    assert contract_offer_response.status_code == 200, contract_offer_response.text
    assert contract_offer_response.json()["status"] == "completed"

    history_response = transfer_market_api.get("/api/transfer-market/history")
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert history[0]["type"] == "market.transfer.completed"
    assert history[0]["status"] == "accepted"
    assert history[0]["bid_id"] == bid_id
    assert history[0]["listing_id"] == listing_id
