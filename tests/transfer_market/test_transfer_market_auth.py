from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.access_control import Organization, OrganizationMembership
from backend.app.models.club_profile import ClubProfile
from backend.app.models.user import User, UserRole
from backend.app.transfer_market.router import _service, router
from backend.app.transfer_market.schemas import WatchlistEntryCreateRequest
from backend.app.transfer_market.service import (
    TRANSFER_MARKET_EXECUTION_ROLES,
    TransferMarketPermissionError,
    TransferMarketService,
)


def _build_user(*, user_id: str, role: UserRole = UserRole.USER) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="not-used",
        role=role,
        is_active=True,
    )


def _build_club(*, club_id: str, owner_user_id: str) -> ClubProfile:
    return ClubProfile(
        id=club_id,
        owner_user_id=owner_user_id,
        club_name=f"{club_id} FC",
        slug=club_id,
        primary_color="#112233",
        secondary_color="#445566",
        accent_color="#778899",
    )


@pytest.fixture()
def transfer_market_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(bind=engine)
    ClubProfile.__table__.create(bind=engine)
    Organization.__table__.create(bind=engine)
    OrganizationMembership.__table__.create(bind=engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_watchlist_route_requires_authenticated_user() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_service] = lambda: SimpleNamespace()
    app.dependency_overrides[get_session] = lambda: SimpleNamespace()

    with TestClient(app) as client:
        response = client.post(
            "/api/transfer-market/watchlist",
            json={"club_id": "club-alpha", "player_id": "player-1"},
        )

    assert response.status_code == 401


def test_job_route_requires_admin_actor() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_service] = lambda: SimpleNamespace()
    app.dependency_overrides[get_current_user] = lambda: _build_user(
        user_id="user-basic",
        role=UserRole.USER,
    )

    with TestClient(app) as client:
        response = client.post("/api/transfer-market/jobs/run", json={})

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access is required for this action."


def test_resolve_actor_club_id_uses_owned_club_when_request_omits_club_id(
    transfer_market_session: Session,
) -> None:
    owner = _build_user(user_id="owner-user", role=UserRole.CLUB)
    club = _build_club(club_id="club-owner", owner_user_id=owner.id)
    transfer_market_session.add_all([owner, club])
    transfer_market_session.commit()

    service = TransferMarketService(transfer_market_session)

    resolved_club_id = service._resolve_actor_club_id(
        owner,
        None,
        allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
        forbidden_detail="transfer_market_club_access_required",
    )

    assert resolved_club_id == club.id


def test_add_watchlist_entry_rejects_actor_without_club_access(
    transfer_market_session: Session,
) -> None:
    owner = _build_user(user_id="owner-user", role=UserRole.CLUB)
    intruder = _build_user(user_id="intruder-user", role=UserRole.USER)
    club = _build_club(club_id="club-secure", owner_user_id=owner.id)
    transfer_market_session.add_all([owner, intruder, club])
    transfer_market_session.commit()

    service = TransferMarketService(transfer_market_session)

    with pytest.raises(TransferMarketPermissionError) as exc_info:
        service.add_watchlist_entry(
            WatchlistEntryCreateRequest(
                club_id=club.id,
                player_id="player-1",
            ),
            actor=intruder,
        )

    assert str(exc_info.value) == "transfer_market_watchlist_access_required"


def test_place_bid_rejects_actor_without_bidder_club_access(
    transfer_market_session: Session,
) -> None:
    owner = _build_user(user_id="owner-user", role=UserRole.CLUB)
    intruder = _build_user(user_id="intruder-user", role=UserRole.USER)
    club = _build_club(club_id="club-bidder", owner_user_id=owner.id)
    transfer_market_session.add_all([owner, intruder, club])
    transfer_market_session.commit()

    service = TransferMarketService(transfer_market_session)

    with pytest.raises(TransferMarketPermissionError) as exc_info:
        service.place_bid(
            "listing-1",
            actor=intruder,
            bidder_club_id=club.id,
            amount=Decimal("5.00"),
        )

    assert str(exc_info.value) == "transfer_market_bidder_club_access_required"


def test_run_background_jobs_rejects_non_admin_actor(
    transfer_market_session: Session,
) -> None:
    actor = _build_user(user_id="operator-user", role=UserRole.CLUB)
    transfer_market_session.add(actor)
    transfer_market_session.commit()

    service = TransferMarketService(transfer_market_session)

    with pytest.raises(TransferMarketPermissionError) as exc_info:
        service.run_background_jobs(actor=actor)

    assert str(exc_info.value) == "transfer_market_admin_access_required"
