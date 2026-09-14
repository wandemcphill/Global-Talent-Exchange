from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.common.enums.contract_status import ContractStatus
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.transfer_bid import TransferBid
from app.models.user import User, UserRole
from app.routes.player_lifecycle import router
from app.schemas.player_lifecycle import ContractCreateRequest, TransferBidCreateRequest
from app.services.player_lifecycle_service import PlayerLifecycleService
from tests.players.test_player_lifecycle import add_window, seed_base_context


def _client(session: Session, *, user_id: str) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def _session_override():
        yield session

    def _current_user_override() -> User:
        user = session.get(User, user_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _current_user_override
    return TestClient(app)


def _add_user_and_club(session: Session, *, user_id: str, club_id: str) -> ClubProfile:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        display_name=user_id.title(),
        password_hash="x",
        role=UserRole.USER,
    )
    club = ClubProfile(
        id=club_id,
        owner_user_id=user.id,
        club_name=club_id.title(),
        short_name=club_id[:3].upper(),
        slug=club_id,
        primary_color="#111111",
        secondary_color="#222222",
        accent_color="#333333",
    )
    session.add_all([user, club])
    session.commit()
    return club


def test_bid_creation_requires_buying_club_owner(lifecycle_session: Session) -> None:
    context = seed_base_context(lifecycle_session)
    add_window(
        lifecycle_session,
        window_id="window-auth-buy",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 12, 31),
    )
    attacker = _add_user_and_club(
        lifecycle_session,
        user_id="transfer-attacker",
        club_id="club-attacker",
    )

    payload = {
        "player_id": context["player_id"],
        "buying_club_id": context["buyer_profile_id"],
        "bid_amount": "1000000.00",
    }

    with _client(lifecycle_session, user_id=attacker.owner_user_id) as client:
        response = client.post("/api/transfers/windows/window-auth-buy/bids", json=payload)

    assert response.status_code == 403, response.text
    assert lifecycle_session.scalars(select(TransferBid)).all() == []


def test_bid_creation_accepts_owned_buying_club(lifecycle_session: Session) -> None:
    context = seed_base_context(lifecycle_session)
    add_window(
        lifecycle_session,
        window_id="window-auth-buy-owned",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 12, 31),
    )

    payload = {
        "player_id": context["player_id"],
        "buying_club_id": context["buyer_profile_id"],
        "bid_amount": "1000000.00",
    }

    with _client(lifecycle_session, user_id="user-owner") as client:
        response = client.post("/api/transfers/windows/window-auth-buy-owned/bids", json=payload)

    assert response.status_code == 201, response.text
    assert response.json()["buying_club_id"] == context["buyer_profile_id"]


def test_bid_acceptance_requires_selling_club_owner(lifecycle_session: Session) -> None:
    context = seed_base_context(lifecycle_session)
    buyer = _add_user_and_club(
        lifecycle_session,
        user_id="transfer-buyer",
        club_id="club-transfer-buyer",
    )
    window = add_window(
        lifecycle_session,
        window_id="window-auth-sell",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 12, 31),
    )
    service = PlayerLifecycleService(lifecycle_session)
    service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("75000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )
    bid = service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=buyer.id,
            bid_amount=Decimal("1000000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )

    attacker = _add_user_and_club(
        lifecycle_session,
        user_id="seller-attacker",
        club_id="club-seller-attacker",
    )
    payload = {
        "contract_ends_on": "2028-03-11",
        "contract_starts_on": "2026-03-12",
        "wage_amount": "85000.00",
        "signed_on": "2026-03-12",
    }

    with _client(lifecycle_session, user_id=attacker.owner_user_id) as client:
        response = client.post(
            f"/api/transfers/windows/{window.id}/bids/{bid.id}/accept",
            json=payload,
        )

    assert response.status_code == 403, response.text
    refreshed = lifecycle_session.get(TransferBid, bid.id)
    assert refreshed is not None
    assert refreshed.status == "submitted"
    assert lifecycle_session.query(PlayerContract).filter_by(player_id=context["player_id"]).count() == 1


def test_bid_acceptance_accepts_owned_selling_club(lifecycle_session: Session) -> None:
    context = seed_base_context(lifecycle_session)
    buyer = _add_user_and_club(
        lifecycle_session,
        user_id="transfer-buyer-owned",
        club_id="club-transfer-buyer-owned",
    )
    window = add_window(
        lifecycle_session,
        window_id="window-auth-sell-owned",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 12, 31),
    )
    service = PlayerLifecycleService(lifecycle_session)
    service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("75000.00"),
            signed_on=date(2026, 1, 1),
            starts_on=date(2026, 1, 1),
            ends_on=date(2027, 1, 1),
        ),
    )
    bid = service.create_bid(
        window.id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=buyer.id,
            bid_amount=Decimal("1000000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )
    payload = {
        "contract_ends_on": "2028-03-11",
        "contract_starts_on": "2026-03-12",
        "wage_amount": "85000.00",
        "signed_on": "2026-03-12",
    }

    with _client(lifecycle_session, user_id="user-owner") as client:
        response = client.post(
            f"/api/transfers/windows/{window.id}/bids/{bid.id}/accept",
            json=payload,
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] in {"accepted", "completed"}
    contracts = lifecycle_session.scalars(
        select(PlayerContract).where(
            PlayerContract.player_id == context["player_id"],
            PlayerContract.club_id == buyer.id,
        )
    ).all()
    assert len(contracts) == 1
    assert contracts[0].status in {ContractStatus.ACTIVE.value, ContractStatus.AGREED.value}
