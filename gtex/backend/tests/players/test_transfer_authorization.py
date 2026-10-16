"""Cross-club / cross-user attack coverage for transfer-market mutations.

Authentication on these routes was hardened previously; this suite pins the
*authorization* half. Every mutation below moves a player asset or a contract,
so the question each test asks is the same: does the endpoint derive authority
from the stored object, or does it trust what the caller sent?

The attacker is a fully legitimate, authenticated user who owns their own club.
That is the realistic threat: not an anonymous caller, but a signed-in rival
naming somebody else's listing, offer or club id.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_control.service import AccessControlService
from app.auth.dependencies import get_session
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.transfer_market import TransferHubOffer, TransferListing
from app.models.user import KycStatus, User, UserRole
from app.transfer_market.router import router
from backend.tests.players.test_transfer_market import _auth_headers, seed_transfer_market_context

ATTACKER_USER_ID = "user-attacker"
ATTACKER_CLUB_ID = "club-profile-outsider"


@pytest.fixture(autouse=True)
def _configure_test_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def api(db_session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def _session_override():
        yield db_session

    app.dependency_overrides[get_session] = _session_override
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def context(db_session: Session) -> dict[str, str]:
    """Seller club, buyer club, and an unrelated attacker club."""
    seeded = seed_transfer_market_context(db_session)

    attacker_user = User(
        id=ATTACKER_USER_ID,
        email="attacker@example.com",
        username="attacker",
        display_name="Attacker",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    attacker_profile = ClubProfile(
        id=ATTACKER_CLUB_ID,
        owner_user_id=attacker_user.id,
        club_name="Outsider FC",
        short_name="OFC",
        slug="outsider-fc",
        primary_color="#000000",
        secondary_color="#ffffff",
        accent_color="#ff0000",
        country_code="GH",
        region_name="Accra",
        city_name="Accra",
    )
    db_session.add_all([attacker_user, attacker_profile])
    db_session.commit()
    AccessControlService(db_session).ensure_club_organization(attacker_profile, owner_user_id=attacker_user.id)
    db_session.commit()

    seeded["attacker_user_id"] = attacker_user.id
    seeded["attacker_club_id"] = attacker_profile.id
    return seeded


def _headers(session: Session, context: dict[str, str], who: str) -> dict[str, str]:
    return _auth_headers(session, user_id=context[f"{who}_user_id"])


def _open_listing(client: TestClient, session: Session, context: dict[str, str], *, price: str = "900000.00") -> str:
    response = client.post(
        "/api/transfer-hub/listings",
        json={
            "player_id": context["player_id"],
            "base_price": price,
            "expires_at": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=_headers(session, context, "seller"),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _open_offer(client: TestClient, session: Session, context: dict[str, str], listing_id: str) -> str:
    response = client.post(
        f"/api/transfer-hub/listings/{listing_id}/offers",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "offer_type": "transfer",
            "cash_amount": "1000000.00",
            "idempotency_key": "attack-suite-offer",
        },
        headers=_headers(session, context, "buyer"),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --------------------------------------------------------------------------
# Authentication boundary
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/transfer-hub/listings", {"player_id": "player-1", "base_price": "1.00"}),
        ("post", "/api/transfer-hub/listings/listing-x/bids", {"amount": "1.00"}),
        ("post", "/api/transfer-hub/listings/listing-x/offers", {"offer_type": "transfer"}),
        ("post", "/api/transfer-hub/offers/offer-x/accept", None),
        ("post", "/api/transfer-hub/offers/offer-x/reject", None),
        ("post", "/api/transfer-hub/offers/offer-x/cancel", None),
        ("post", "/api/transfer-hub/offers/offer-x/counter", {}),
        ("post", "/api/transfer-hub/listings/listing-x/close", None),
        ("post", "/api/transfer-hub/players/player-1/transfer-request", {}),
        ("post", "/api/transfer-market/listings/listing-x/contract-offer", {}),
        ("post", "/api/transfer-market/watchlist", {"player_id": "player-1"}),
        ("put", "/api/transfer-market/clubs/club-x/team-dynamics", {}),
        ("post", "/api/transfer-market/jobs/run", {}),
    ],
)
def test_transfer_mutations_reject_unauthenticated_callers(
    api: TestClient, method: str, path: str, body: object
) -> None:
    response = getattr(api, method)(path, json=body)
    assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"


# --------------------------------------------------------------------------
# Cross-club offer lifecycle
# --------------------------------------------------------------------------


def test_outsider_cannot_accept_an_offer_on_another_clubs_listing(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/accept",
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(TransferHubOffer, offer_id).status == "open"
    assert db_session.get(TransferListing, listing_id).status == "open"


def test_the_selling_club_can_accept_the_same_offer(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/accept",
        headers=_headers(db_session, context, "seller"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    db_session.expire_all()
    assert db_session.get(TransferListing, listing_id).status == "accepted"


def test_outsider_cannot_reject_another_clubs_offer(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/reject",
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(TransferHubOffer, offer_id).status == "open"


def test_the_bidding_club_cannot_reject_its_own_offer_as_the_seller(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    """Rejection authority sits with the seller, derived from the stored offer."""
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/reject",
        headers=_headers(db_session, context, "buyer"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(TransferHubOffer, offer_id).status == "open"


def test_outsider_cannot_cancel_another_clubs_offer(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/cancel",
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(TransferHubOffer, offer_id).status == "open"


def test_the_bidding_club_can_cancel_its_own_offer(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/cancel",
        headers=_headers(db_session, context, "buyer"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_outsider_cannot_counter_another_clubs_offer(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)

    response = api.post(
        f"/api/transfer-hub/offers/{offer_id}/counter",
        json={"cash_amount": "1.00"},
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    offer = db_session.get(TransferHubOffer, offer_id)
    assert offer.status == "open"
    assert offer.cash_amount == Decimal("1000000.00")


# --------------------------------------------------------------------------
# Listing lifecycle and ownership
# --------------------------------------------------------------------------


def test_outsider_cannot_close_another_clubs_listing(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)

    response = api.post(
        f"/api/transfer-hub/listings/{listing_id}/close",
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(TransferListing, listing_id).status == "open"


def test_outsider_cannot_list_a_player_they_do_not_hold(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    """Ownership comes from the player's current club, not the request body."""
    response = api.post(
        "/api/transfer-hub/listings",
        json={
            "player_id": context["player_id"],
            "selling_club_id": context["attacker_club_id"],
            "base_price": "1.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selling club must match the player's current club."
    assert db_session.query(TransferListing).count() == 0


def test_outsider_cannot_list_a_player_under_the_owning_clubs_identity(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    """Naming the victim's club id in the body must not confer their authority."""
    response = api.post(
        "/api/transfer-hub/listings",
        json={
            "player_id": context["player_id"],
            "selling_club_id": context["seller_club_id"],
            "base_price": "1.00",
            "expires_at": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
            "window_id": context["window_id"],
        },
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    assert db_session.query(TransferListing).count() == 0


def test_a_bidder_cannot_bid_under_another_clubs_identity(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)

    response = api.post(
        f"/api/transfer-hub/listings/{listing_id}/bids",
        json={"bidder_club_id": context["buyer_club_id"], "amount": "5000000.00"},
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    db_session.expire_all()
    listing = db_session.get(TransferListing, listing_id)
    assert listing.highest_bidder_id is None


def test_outsider_cannot_open_an_offer_under_another_clubs_identity(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)

    response = api.post(
        f"/api/transfer-hub/listings/{listing_id}/offers",
        json={
            "bidder_club_id": context["buyer_club_id"],
            "offer_type": "transfer",
            "cash_amount": "1.00",
            "idempotency_key": "spoofed-offer-key",
        },
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403
    assert db_session.query(TransferHubOffer).count() == 0


# --------------------------------------------------------------------------
# Contract-level mutations
# --------------------------------------------------------------------------


def test_outsider_cannot_file_a_transfer_request_against_another_clubs_player(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    response = api.post(
        f"/api/transfer-hub/players/{context['player_id']}/transfer-request",
        json={"current_club_id": context["seller_club_id"]},
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403


def test_outsider_cannot_rewrite_another_clubs_team_dynamics(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    response = api.put(
        f"/api/transfer-market/clubs/{context['seller_club_id']}/team-dynamics",
        json={"chemistry_risk": 90.0},
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403


def test_outsider_cannot_rewrite_another_clubs_coach_profile(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    response = api.put(
        f"/api/transfer-market/coaches/{context['seller_club_id']}/profile",
        json={"tactical_philosophy": "impostor-ball"},
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403


def test_non_admin_cannot_run_transfer_market_background_jobs(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    response = api.post(
        "/api/transfer-market/jobs/run",
        json={},
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403


# --------------------------------------------------------------------------
# Read-side exposure
# --------------------------------------------------------------------------


def test_outsider_cannot_read_another_pairs_negotiation(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    api.post(
        f"/api/transfer-hub/listings/{listing_id}/bids",
        json={"amount": "1500000.00"},
        headers=_headers(db_session, context, "buyer"),
    )
    api.post(
        f"/api/transfer-hub/listings/{listing_id}/close",
        headers=_headers(db_session, context, "seller"),
    )

    response = api.get(
        f"/api/transfer-hub/listings/{listing_id}/negotiation",
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403


def test_both_negotiating_clubs_can_read_the_negotiation(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    api.post(
        f"/api/transfer-hub/listings/{listing_id}/bids",
        json={"amount": "1500000.00"},
        headers=_headers(db_session, context, "buyer"),
    )
    api.post(
        f"/api/transfer-hub/listings/{listing_id}/close",
        headers=_headers(db_session, context, "seller"),
    )

    for who in ("seller", "buyer"):
        response = api.get(
            f"/api/transfer-hub/listings/{listing_id}/negotiation",
            headers=_headers(db_session, context, who),
        )
        assert response.status_code == 200, who


def test_outsider_cannot_submit_a_contract_offer_on_another_clubs_negotiation(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    api.post(
        f"/api/transfer-hub/listings/{listing_id}/bids",
        json={"amount": "1500000.00"},
        headers=_headers(db_session, context, "buyer"),
    )
    api.post(
        f"/api/transfer-hub/listings/{listing_id}/close",
        headers=_headers(db_session, context, "seller"),
    )

    response = api.post(
        f"/api/transfer-hub/listings/{listing_id}/contract-offer",
        json={
            "bidder_club_id": context["attacker_club_id"],
            "wage_offer_amount": "1.00",
            "contract_years": "1.0",
            "expected_role": "starter",
        },
        headers=_headers(db_session, context, "attacker"),
    )

    assert response.status_code == 403


# --------------------------------------------------------------------------
# Repeat / duplicate mutation
# --------------------------------------------------------------------------


def test_accepting_an_already_accepted_offer_does_not_transition_twice(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)
    seller_headers = _headers(db_session, context, "seller")

    first = api.post(f"/api/transfer-hub/offers/{offer_id}/accept", headers=seller_headers)
    assert first.status_code == 200
    resolved_at = first.json()["resolved_at"]

    second = api.post(f"/api/transfer-hub/offers/{offer_id}/accept", headers=seller_headers)

    assert second.status_code == 400
    db_session.expire_all()
    offer = db_session.get(TransferHubOffer, offer_id)
    assert offer.status == "accepted"
    assert offer.resolved_at.isoformat().startswith(resolved_at[:19])


def test_an_accepted_offer_cannot_then_be_rejected(
    api: TestClient, db_session: Session, context: dict[str, str]
) -> None:
    listing_id = _open_listing(api, db_session, context)
    offer_id = _open_offer(api, db_session, context, listing_id)
    seller_headers = _headers(db_session, context, "seller")

    assert api.post(f"/api/transfer-hub/offers/{offer_id}/accept", headers=seller_headers).status_code == 200

    response = api.post(f"/api/transfer-hub/offers/{offer_id}/reject", headers=seller_headers)

    assert response.status_code == 400
    db_session.expire_all()
    assert db_session.get(TransferHubOffer, offer_id).status == "accepted"
