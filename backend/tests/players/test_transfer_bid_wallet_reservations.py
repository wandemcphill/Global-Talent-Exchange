from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.common.enums.transfer_bid_status import TransferBidStatus
from app.ingestion.models import Club as IngestionClub
from app.ingestion.models import Competition, Player
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.transfer_bid import TransferBid
from app.models.transfer_window import TransferWindow
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.user import KycStatus, User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.schemas import player_lifecycle as lifecycle_schemas
from app.schemas.player_lifecycle import (
    ContractCreateRequest,
    TransferBidAcceptRequest,
    TransferBidCreateRequest,
    TransferBidRejectRequest,
)
from app.segments.player_lifecycle.segment_player_lifecycle import router as player_lifecycle_router
from app.services.player_lifecycle_service import PlayerLifecycleService, PlayerLifecycleValidationError
from app.wallets.service import LedgerPosting, WalletService


@dataclass(frozen=True)
class TransferBidWalletContext:
    player_id: str
    seller_club_id: str
    buyer_club_id: str
    seller_owner_id: str
    buyer_owner_id: str
    window_id: str


@pytest.fixture()
def lifecycle_session() -> Session:
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
        engine.dispose()


@pytest.fixture()
def lifecycle_service(lifecycle_session: Session) -> PlayerLifecycleService:
    return PlayerLifecycleService(lifecycle_session)


def _seed_context(session: Session) -> TransferBidWalletContext:
    seller_owner = User(
        id="seller-owner",
        email="seller@example.com",
        username="sellerowner",
        display_name="Seller Owner",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    buyer_owner = User(
        id="buyer-owner",
        email="buyer@example.com",
        username="buyerowner",
        display_name="Buyer Owner",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    seller_club = ClubProfile(
        id="club-seller",
        owner_user_id=seller_owner.id,
        club_name="Seller FC",
        short_name="SFC",
        slug="seller-fc",
        primary_color="#123456",
        secondary_color="#ffffff",
        accent_color="#ffcc00",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
    )
    buyer_club = ClubProfile(
        id="club-buyer",
        owner_user_id=buyer_owner.id,
        club_name="Buyer FC",
        short_name="BFC",
        slug="buyer-fc",
        primary_color="#654321",
        secondary_color="#eeeeee",
        accent_color="#00aaff",
        country_code="NG",
        region_name="Abuja",
        city_name="Abuja",
    )
    competition = Competition(
        id="competition-transfer-bid-wallet",
        source_provider="test",
        provider_external_id="competition-transfer-bid-wallet",
        name="Wallet League",
        slug="wallet-league",
    )
    ingestion_club = IngestionClub(
        id="ingestion-club-seller",
        source_provider="test",
        provider_external_id="ingestion-club-seller",
        current_competition_id=competition.id,
        name="Seller FC",
        slug="seller-fc",
    )
    player = Player(
        id="player-transfer-wallet",
        source_provider="test",
        provider_external_id="player-transfer-wallet",
        current_club_id=ingestion_club.id,
        current_club_profile_id=seller_club.id,
        current_competition_id=competition.id,
        full_name="Reserved Funds Forward",
        normalized_position="forward",
    )
    window = TransferWindow(
        id="window-transfer-wallet",
        territory_code="NG",
        label="Wallet Window",
        status="upcoming",
        opens_on=date(2026, 3, 1),
        closes_on=date(2026, 3, 31),
    )
    session.add_all([seller_owner, buyer_owner, seller_club, buyer_club, competition, ingestion_club, player, window])
    session.commit()
    return TransferBidWalletContext(
        player_id=player.id,
        seller_club_id=seller_club.id,
        buyer_club_id=buyer_club.id,
        seller_owner_id=seller_owner.id,
        buyer_owner_id=buyer_owner.id,
        window_id=window.id,
    )


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
        reference=f"test-transfer-bid-fund:{user_id}",
        description="Test transfer bid wallet funding",
        actor=user,
    )
    session.commit()


def _buyer(lifecycle_session: Session, context: TransferBidWalletContext) -> User:
    buyer = lifecycle_session.get(User, context.buyer_owner_id)
    assert buyer is not None
    return buyer


def _seller(lifecycle_session: Session, context: TransferBidWalletContext) -> User:
    seller = lifecycle_session.get(User, context.seller_owner_id)
    assert seller is not None
    return seller


def _admin_user(lifecycle_session: Session) -> User:
    admin = User(
        id="admin-transfer-bid-review-action",
        email="admin-transfer-bid-review-action@example.com",
        username="admintransferbidreviewaction",
        display_name="Admin Transfer Bid Review Action",
        password_hash="x",
        role=UserRole.SUPER_ADMIN,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    lifecycle_session.add(admin)
    lifecycle_session.commit()
    return admin


def _intruder_user(lifecycle_session: Session) -> User:
    intruder = User(
        id="intruder-transfer-bid",
        email="intruder-transfer-bid@example.com",
        username="intrudertransferbid",
        display_name="Intruder Transfer Bid",
        password_hash="x",
        role=UserRole.USER,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    lifecycle_session.add(intruder)
    lifecycle_session.commit()
    return intruder


def _app_for_lifecycle_routes(lifecycle_session: Session, *, current_user: User | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(player_lifecycle_router)

    def override_session():
        yield lifecycle_session

    app.dependency_overrides[get_session] = override_session
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return app


def _wallet_snapshot(session: Session, user: User) -> tuple[Decimal, Decimal, Decimal, Decimal, tuple[str, ...]]:
    summary = _coin_summary(session, user)
    return (
        summary.available_balance,
        summary.reserved_balance,
        summary.locked_balance,
        summary.total_balance,
        tuple(summary.lock_reasons),
    )


def _lock_reason_text(reason: object) -> str:
    if isinstance(reason, dict):
        return " ".join(str(value) for value in reason.values()).lower()
    return str(reason).lower()


def _bid_review_audit_events(session: Session, bid: TransferBid) -> list[PlayerLifecycleEvent]:
    return list(
        session.scalars(
            select(PlayerLifecycleEvent)
            .where(
                PlayerLifecycleEvent.player_id == bid.player_id,
                PlayerLifecycleEvent.related_entity_type == "transfer_bid",
                PlayerLifecycleEvent.related_entity_id == bid.id,
                PlayerLifecycleEvent.event_type == "admin_transfer_bid_review_action",
            )
            .order_by(PlayerLifecycleEvent.created_at.asc())
        )
    )


def _create_active_contract(
    lifecycle_service: PlayerLifecycleService,
    context: TransferBidWalletContext,
) -> None:
    lifecycle_service.create_contract(
        context.player_id,
        ContractCreateRequest(
            club_id=context.seller_club_id,
            wage_amount=Decimal("75000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2027, 6, 30),
        ),
    )


def _create_bid(
    lifecycle_service: PlayerLifecycleService,
    context: TransferBidWalletContext,
    *,
    amount: Decimal = Decimal("300.00"),
) -> TransferBid:
    return lifecycle_service.create_bid(
        context.window_id,
        TransferBidCreateRequest(
            player_id=context.player_id,
            buying_club_id=context.buyer_club_id,
            bid_amount=amount,
            wage_offer_amount=Decimal("90000.00"),
        ),
        submitted_on=date(2026, 3, 12),
    )


def _keep_window_open_for_route_tests(session: Session, context: TransferBidWalletContext) -> None:
    window = session.get(TransferWindow, context.window_id)
    assert window is not None
    window.status = "open"
    window.opens_on = date(2020, 1, 1)
    window.closes_on = date(2100, 12, 31)
    session.commit()


def _coin_summary(session: Session, user: User):
    return WalletService().get_wallet_summary(session, user, currency=LedgerUnit.COIN)


def _route_dependency_call_names(route) -> set[str]:
    names: set[str] = set()

    def visit(dependant) -> None:
        for dependency in dependant.dependencies:
            call = dependency.call
            if call is not None:
                names.add(getattr(call, "__name__", repr(call)))
            visit(dependency)

    visit(route.dependant)
    return names


def test_transfer_bid_status_enum_covers_canonical_review_lifecycle() -> None:
    canonical_statuses = {
        "draft",
        "pending",
        "submitted",
        "counter",
        "accepted",
        "rejected",
        "withdrawn",
    }

    assert canonical_statuses.issubset({status.value for status in TransferBidStatus})


def test_transfer_bid_mutation_routes_require_authenticated_club_owner_dependency() -> None:
    app = FastAPI()
    app.include_router(player_lifecycle_router)
    route_specs = {
        ("POST", "/api/transfers/windows/{window_id}/bids"): "create",
        ("POST", "/api/transfers/windows/{window_id}/bids/{bid_id}/accept"): "accept",
        ("POST", "/api/transfers/windows/{window_id}/bids/{bid_id}/reject"): "reject",
        ("POST", "/api/transfers/windows/{window_id}/bids/{bid_id}/counter"): "counter",
        ("POST", "/api/transfers/windows/{window_id}/bids/{bid_id}/withdraw"): "withdraw",
    }
    authenticated_dependencies = {"get_current_user", "get_current_wallet_user", "get_current_football_user"}
    missing_auth = []

    for route in app.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")
        for method, route_path in route_specs:
            if method in methods and path == route_path:
                dependency_names = _route_dependency_call_names(route)
                if dependency_names.isdisjoint(authenticated_dependencies):
                    missing_auth.append(f"{route_specs[(method, route_path)]} {method} {route_path}")

    assert not missing_auth, (
        "Transfer bid mutation routes should require an authenticated club-owner actor dependency: "
        + ", ".join(missing_auth)
    )


@pytest.mark.parametrize("operation", ["create", "accept", "reject", "counter", "withdraw"])
def test_transfer_bid_mutation_routes_reject_non_owner_actor(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
    operation: str,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _keep_window_open_for_route_tests(lifecycle_session, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    intruder = _intruder_user(lifecycle_session)
    bid = None if operation == "create" else _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=intruder)

    if operation == "create":
        path = f"/api/transfers/windows/{context.window_id}/bids"
        payload = {
            "player_id": context.player_id,
            "buying_club_id": context.buyer_club_id,
            "bid_amount": "300.00",
            "wage_offer_amount": "90000.00",
        }
    elif operation == "accept":
        assert bid is not None
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/accept"
        payload = {
            "contract_ends_on": "2028-06-30",
            "contract_starts_on": "2026-03-12",
            "wage_amount": "90000.00",
            "signed_on": "2026-03-12",
        }
    elif operation == "reject":
        assert bid is not None
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/reject"
        payload = {"reason": "Non-owner cannot reject transfer bids"}
    elif operation == "counter":
        assert bid is not None
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/counter"
        payload = {
            "bid_amount": "350.00",
            "wage_offer_amount": "95000.00",
            "notes": "Non-owner cannot counter transfer bids",
        }
    else:
        assert bid is not None
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/withdraw"
        payload = {"reason": "Non-owner cannot withdraw transfer bids"}

    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 403, response.text


def test_buyer_owner_can_create_and_withdraw_bid_routes(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    buyer = _buyer(lifecycle_session, context)
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=buyer)

    with TestClient(app) as client:
        created = client.post(
            f"/api/transfers/windows/{context.window_id}/bids",
            json={
                "player_id": context.player_id,
                "buying_club_id": context.buyer_club_id,
                "bid_amount": "300.00",
                "wage_offer_amount": "90000.00",
                "allow_outside_window": True,
                "exemption_reason": "Route ownership verification",
            },
        )

        assert created.status_code == 201, created.text
        bid_id = created.json()["id"]
        assert created.json()["status"] == TransferBidStatus.SUBMITTED.value

        withdrawn = client.post(
            f"/api/transfers/windows/{context.window_id}/bids/{bid_id}/withdraw",
            json={"reason": "Buyer changed squad plan"},
        )

    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["status"] == TransferBidStatus.WITHDRAWN.value
    assert _coin_summary(lifecycle_session, buyer).available_balance == Decimal("1000.0000")
    assert _coin_summary(lifecycle_session, buyer).reserved_balance == Decimal("0.0000")


@pytest.mark.parametrize("operation", ["accept", "reject", "counter"])
def test_seller_owner_can_progress_seller_side_bid_routes(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
    operation: str,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    seller = _seller(lifecycle_session, context)
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=seller)

    if operation == "accept":
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/accept"
        payload = {
            "contract_ends_on": "2028-06-30",
            "contract_starts_on": "2026-03-12",
            "wage_amount": "90000.00",
            "signed_on": "2026-03-12",
        }
        expected_status = TransferBidStatus.COMPLETED.value
    elif operation == "reject":
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/reject"
        payload = {"reason": "Seller chose another offer"}
        expected_status = TransferBidStatus.REJECTED.value
    else:
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/counter"
        bid.structured_terms_json = {
            **dict(bid.structured_terms_json or {}),
            "outside_window_exempt": True,
            "exemption_reason": "Route ownership verification",
        }
        lifecycle_session.commit()
        payload = {
            "bid_amount": "350.00",
            "wage_offer_amount": "95000.00",
            "notes": "Seller countered with stronger terms",
        }
        expected_status = TransferBidStatus.SUBMITTED.value

    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code in {200, 201}, response.text
    assert response.json()["status"] == expected_status


@pytest.mark.parametrize(
    ("operation", "actor_side"),
    [
        ("accept", "buyer"),
        ("reject", "buyer"),
        ("counter", "buyer"),
        ("withdraw", "seller"),
    ],
)
def test_transfer_bid_routes_reject_wrong_side_club_owner(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
    operation: str,
    actor_side: str,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    actor = _buyer(lifecycle_session, context) if actor_side == "buyer" else _seller(lifecycle_session, context)
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=actor)

    if operation == "accept":
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/accept"
        payload = {
            "contract_ends_on": "2028-06-30",
            "contract_starts_on": "2026-03-12",
            "wage_amount": "90000.00",
            "signed_on": "2026-03-12",
        }
    elif operation == "reject":
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/reject"
        payload = {"reason": "Wrong club side cannot reject"}
    elif operation == "counter":
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/counter"
        payload = {"bid_amount": "350.00", "wage_offer_amount": "95000.00"}
    else:
        path = f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/withdraw"
        payload = {"reason": "Wrong club side cannot withdraw"}

    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 403, response.text


def test_transfer_bid_create_route_replays_idempotency_key_without_duplicate_hold(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    buyer = _buyer(lifecycle_session, context)
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=buyer)
    payload = {
        "player_id": context.player_id,
        "buying_club_id": context.buyer_club_id,
        "bid_amount": "300.00",
        "wage_offer_amount": "90000.00",
        "allow_outside_window": True,
        "exemption_reason": "Route idempotency verification",
    }
    headers = {"Idempotency-Key": "transfer-bid-create-replay"}

    with TestClient(app) as client:
        first = client.post(f"/api/transfers/windows/{context.window_id}/bids", json=payload, headers=headers)
        second = client.post(f"/api/transfers/windows/{context.window_id}/bids", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]
    assert _coin_summary(lifecycle_session, buyer).available_balance == Decimal("700.0000")
    assert _coin_summary(lifecycle_session, buyer).reserved_balance == Decimal("300.0000")
    assert len(lifecycle_service.list_window_bids(context.window_id)) == 1


def test_transfer_bid_create_route_rejects_idempotency_key_payload_conflict(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    buyer = _buyer(lifecycle_session, context)
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=buyer)
    payload = {
        "player_id": context.player_id,
        "buying_club_id": context.buyer_club_id,
        "bid_amount": "300.00",
        "wage_offer_amount": "90000.00",
        "allow_outside_window": True,
        "exemption_reason": "Route idempotency verification",
    }
    conflicting_payload = {**payload, "bid_amount": "350.00"}
    headers = {"Idempotency-Key": "transfer-bid-create-conflict"}

    with TestClient(app) as client:
        first = client.post(f"/api/transfers/windows/{context.window_id}/bids", json=payload, headers=headers)
        second = client.post(
            f"/api/transfers/windows/{context.window_id}/bids",
            json=conflicting_payload,
            headers=headers,
        )

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    assert _coin_summary(lifecycle_session, buyer).available_balance == Decimal("700.0000")
    assert _coin_summary(lifecycle_session, buyer).reserved_balance == Decimal("300.0000")
    assert len(lifecycle_service.list_window_bids(context.window_id)) == 1


def test_underfunded_transfer_bid_create_fails_without_bid_or_wallet_reservation(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("250.0000"))
    buyer = _buyer(lifecycle_session, context)
    request = TransferBidCreateRequest(
        player_id=context.player_id,
        buying_club_id=context.buyer_club_id,
        bid_amount=Decimal("300.00"),
        wage_offer_amount=Decimal("90000.00"),
    )
    before_wallet = _wallet_snapshot(lifecycle_session, buyer)

    with pytest.raises(PlayerLifecycleValidationError, match="does not have enough GTex Coin"):
        lifecycle_service.create_bid(
            context.window_id,
            request,
            submitted_on=date(2026, 3, 12),
            idempotency_key="underfunded-transfer-bid-create",
        )

    assert (
        lifecycle_session.scalars(
            select(TransferBid).where(
                TransferBid.window_id == context.window_id,
                TransferBid.player_id == context.player_id,
            )
        ).all()
        == []
    )
    assert _wallet_snapshot(lifecycle_session, buyer) == before_wallet
    assert _coin_summary(lifecycle_session, buyer).reserved_balance == Decimal("0.0000")

    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("100.0000"))
    created = lifecycle_service.create_bid(
        context.window_id,
        request,
        submitted_on=date(2026, 3, 12),
        idempotency_key="underfunded-transfer-bid-create",
    )
    replay = lifecycle_service.create_bid(
        context.window_id,
        request,
        submitted_on=date(2026, 3, 12),
        idempotency_key="underfunded-transfer-bid-create",
    )
    buyer_summary = _coin_summary(lifecycle_session, buyer)

    assert replay.id == created.id
    assert len(lifecycle_service.list_window_bids(context.window_id)) == 1
    assert buyer_summary.available_balance == Decimal("50.0000")
    assert buyer_summary.reserved_balance == Decimal("300.0000")


def test_transfer_bid_accept_route_replays_idempotency_key_without_duplicate_settlement(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    seller = _seller(lifecycle_session, context)
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=seller)
    payload = {
        "contract_ends_on": "2028-06-30",
        "contract_starts_on": "2026-03-12",
        "wage_amount": "90000.00",
        "signed_on": "2026-03-12",
    }
    headers = {"Idempotency-Key": "transfer-bid-accept-replay"}

    with TestClient(app) as client:
        first = client.post(
            f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/accept",
            json=payload,
            headers=headers,
        )
        second = client.post(
            f"/api/transfers/windows/{context.window_id}/bids/{bid.id}/accept",
            json=payload,
            headers=headers,
        )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["id"] == bid.id
    assert _coin_summary(lifecycle_session, _buyer(lifecycle_session, context)).total_balance == Decimal("700.0000")
    assert _coin_summary(lifecycle_session, seller).total_balance == Decimal("300.0000")


def test_transfer_bid_counter_route_replays_idempotency_key_without_duplicate_replacement(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    seller = _seller(lifecycle_session, context)
    original = _create_bid(lifecycle_service, context, amount=Decimal("200.00"))
    original.structured_terms_json = {
        **dict(original.structured_terms_json or {}),
        "outside_window_exempt": True,
        "exemption_reason": "Route idempotency verification",
    }
    lifecycle_session.commit()
    app = _app_for_lifecycle_routes(lifecycle_session, current_user=seller)
    payload = {
        "bid_amount": "350.00",
        "wage_offer_amount": "95000.00",
        "notes": "Seller countered with stronger terms",
    }
    headers = {"Idempotency-Key": "transfer-bid-counter-replay"}

    with TestClient(app) as client:
        first = client.post(
            f"/api/transfers/windows/{context.window_id}/bids/{original.id}/counter",
            json=payload,
            headers=headers,
        )
        second = client.post(
            f"/api/transfers/windows/{context.window_id}/bids/{original.id}/counter",
            json=payload,
            headers=headers,
        )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]
    assert len(lifecycle_service.list_window_bids(context.window_id)) == 2
    assert _coin_summary(lifecycle_session, _buyer(lifecycle_session, context)).reserved_balance == Decimal("350.0000")


def test_submitted_bid_reserves_buyer_coin_and_surfaces_wallet_lock_reason(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))

    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))

    buyer_summary = _coin_summary(lifecycle_session, _buyer(lifecycle_session, context))
    overview = WalletService().get_adaptive_overview(lifecycle_session, _buyer(lifecycle_session, context))

    assert bid.status == TransferBidStatus.SUBMITTED.value
    assert buyer_summary.available_balance == Decimal("700.0000")
    assert buyer_summary.reserved_balance == Decimal("300.0000")
    assert buyer_summary.locked_balance == Decimal("300.0000")
    assert buyer_summary.total_balance == Decimal("1000.0000")
    assert any("bid" in reason.lower() for reason in buyer_summary.lock_reasons), buyer_summary.lock_reasons
    assert overview["reserved_balance"] == Decimal("300.0000")
    assert any("bid" in _lock_reason_text(reason) for reason in overview["lock_reasons"]), overview["lock_reasons"]


def test_pending_bid_status_is_active_and_withdraw_releases_reservation(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    bid.status = TransferBidStatus.PENDING.value
    lifecycle_session.commit()

    queue = lifecycle_service.list_admin_transfer_bid_reviews(status_filter="pending")
    buyer = _buyer(lifecycle_session, context)
    before_withdraw = _coin_summary(lifecycle_session, buyer)

    assert queue.total == 1
    assert queue.items[0].status == TransferBidStatus.PENDING
    assert queue.items[0].wallet_reservation_status == "reserved"
    assert queue.items[0].wallet_reserved_amount == Decimal("300.0000")
    assert before_withdraw.available_balance == Decimal("700.0000")
    assert before_withdraw.reserved_balance == Decimal("300.0000")

    withdrawn = lifecycle_service.withdraw_bid(
        context.window_id,
        bid.id,
        lifecycle_schemas.TransferBidWithdrawRequest(reason="Pending bid withdrawn"),
    )
    after_withdraw = _coin_summary(lifecycle_session, buyer)

    assert withdrawn.status == TransferBidStatus.WITHDRAWN.value
    assert after_withdraw.available_balance == Decimal("1000.0000")
    assert after_withdraw.reserved_balance == Decimal("0.0000")


def test_draft_bid_status_is_inactive_and_does_not_touch_wallets(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    draft = TransferBid(
        id="draft-transfer-bid-wallet",
        window_id=context.window_id,
        player_id=context.player_id,
        selling_club_id=context.seller_club_id,
        buying_club_id=context.buyer_club_id,
        status=TransferBidStatus.DRAFT.value,
        bid_amount=Decimal("300.00"),
        wage_offer_amount=Decimal("90000.00"),
        structured_terms_json={"drafted_on": "2026-03-12"},
    )
    lifecycle_session.add(draft)
    lifecycle_session.commit()
    buyer = _buyer(lifecycle_session, context)

    draft_view = lifecycle_service.to_transfer_bid_view(draft)
    queue = lifecycle_service.list_admin_transfer_bid_reviews(status_filter="draft")

    assert draft_view.status == TransferBidStatus.DRAFT
    assert draft_view.wallet_reservation_status is None
    assert draft_view.wallet_reserved_amount is None
    assert queue.total == 1
    assert queue.items[0].status == TransferBidStatus.DRAFT
    assert queue.items[0].severity == "low"
    assert _coin_summary(lifecycle_session, buyer).available_balance == Decimal("1000.0000")
    assert _coin_summary(lifecycle_session, buyer).reserved_balance == Decimal("0.0000")

    with pytest.raises(PlayerLifecycleValidationError, match="Only submitted transfer bids can be accepted"):
        lifecycle_service.accept_bid(
            context.window_id,
            draft.id,
            TransferBidAcceptRequest(
                contract_ends_on=date(2028, 6, 30),
                contract_starts_on=date(2026, 3, 12),
                wage_amount=Decimal("90000.00"),
                signed_on=date(2026, 3, 12),
            ),
            reference_on=date(2026, 3, 12),
        )
    with pytest.raises(PlayerLifecycleValidationError, match="Only submitted transfer bids can be rejected"):
        lifecycle_service.reject_bid(
            context.window_id,
            draft.id,
            TransferBidRejectRequest(reason="Draft cannot be rejected"),
        )
    with pytest.raises(PlayerLifecycleValidationError, match="Only submitted transfer bids can be countered"):
        lifecycle_service.counter_bid(
            context.window_id,
            draft.id,
            lifecycle_schemas.TransferBidCounterRequest(bid_amount=Decimal("350.00")),
            reference_on=date(2026, 3, 12),
        )
    with pytest.raises(PlayerLifecycleValidationError, match="Only submitted transfer bids can be withdrawn"):
        lifecycle_service.withdraw_bid(
            context.window_id,
            draft.id,
            lifecycle_schemas.TransferBidWithdrawRequest(reason="Draft cannot be withdrawn"),
        )
    assert _coin_summary(lifecycle_session, buyer).available_balance == Decimal("1000.0000")
    assert _coin_summary(lifecycle_session, buyer).reserved_balance == Decimal("0.0000")


def test_admin_transfer_bid_review_queue_is_read_only_and_wallet_aware(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))

    queue = lifecycle_service.list_admin_transfer_bid_reviews(
        status_filter="submitted",
        window_id=context.window_id,
        q=context.player_id,
    )

    assert queue.total == 1
    assert queue.limit == 50
    assert queue.offset == 0
    assert len(queue.items) == 1
    review = queue.items[0]
    assert review.id == bid.id
    assert review.wallet_reservation_status == "reserved"
    assert review.wallet_reserved_amount == Decimal("300.0000")
    assert review.severity == "medium"
    assert review.escalation_state == "monitor"
    assert review.action_state == "audit_only"
    assert review.available_actions == ("acknowledge", "escalate", "note")
    assert "audit" in review.blocked_reason.lower()
    assert review.audit_reference == f"transfer-bid:{bid.id}"
    assert any(event.event_type == "transfer_bid_submitted" for event in review.audit_trail)


def test_admin_transfer_bid_review_http_route_returns_read_only_wallet_rows(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    admin = User(
        id="admin-transfer-review",
        email="admin-transfer-review@example.com",
        username="admintransferreview",
        display_name="Admin Transfer Review",
        password_hash="x",
        role=UserRole.SUPER_ADMIN,
        kyc_status=KycStatus.FULLY_VERIFIED,
    )
    lifecycle_session.add(admin)
    lifecycle_session.commit()

    app = FastAPI()
    app.include_router(player_lifecycle_router)

    def override_session():
        yield lifecycle_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin

    with TestClient(app) as client:
        response = client.get(
            "/api/admin/transfers/bids/review-queue",
            params={
                "status": "submitted",
                "window_id": context.window_id,
                "q": context.player_id,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    row = payload["items"][0]
    assert row["id"] == bid.id
    assert row["action_state"] == "audit_only"
    assert row["available_actions"] == ["acknowledge", "escalate", "note"]
    assert row["wallet_reservation_status"] == "reserved"
    assert Decimal(str(row["wallet_reserved_amount"])) == Decimal("300.0000")
    assert row["wallet_reservation_reference"] == f"transfer-bid:{bid.id}:fee"
    assert row["audit_reference"] == f"transfer-bid:{bid.id}"
    assert "audit" in row["blocked_reason"].lower()


def test_admin_transfer_bid_review_uses_ledger_truth_for_partial_reservation(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    buyer = _buyer(lifecycle_session, context)

    WalletService().release_transfer_bid_reservation(
        lifecycle_session,
        user=buyer,
        transfer_bid_id=bid.id,
        amount=Decimal("125.0000"),
        release_reason="partial_review_test",
        reference=f"transfer-bid:{bid.id}:partial-review-test",
        description="Partial release to verify review rows use ledger reservation truth",
        unit=LedgerUnit.COIN,
        player_id=bid.player_id,
        buying_club_id=bid.buying_club_id,
        selling_club_id=bid.selling_club_id,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    lifecycle_session.commit()
    stale_terms = (bid.structured_terms_json or {})["wallet_reservation"]

    review = lifecycle_service.list_admin_transfer_bid_reviews(status_filter="submitted").items[0]

    assert stale_terms["status"] == "reserved"
    assert Decimal(stale_terms["amount_gtex_coin"]) == Decimal("300.0000")
    assert review.wallet_reservation_status == "partially_reserved"
    assert review.wallet_reserved_amount == Decimal("175.0000")
    assert review.structured_terms_json["wallet_reservation"]["actual_reserved_gtex_coin"] == "175.0000"
    assert review.structured_terms_json["wallet_reservation"]["amount_gtex_coin"] == "300.0000"


def test_admin_transfer_bid_review_action_records_audit_without_wallet_or_lifecycle_mutation(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    buyer = _buyer(lifecycle_session, context)
    admin = _admin_user(lifecycle_session)
    request_type = getattr(lifecycle_schemas, "AdminTransferBidReviewActionRequest", None)
    review_action = getattr(lifecycle_service, "record_admin_transfer_bid_review_action", None)
    before_wallet = _wallet_snapshot(lifecycle_session, buyer)
    before_status = bid.status
    before_terms = dict(bid.structured_terms_json or {})

    assert request_type is not None, (
        "AdminTransferBidReviewActionRequest must define the admin-safe review-only "
        "transfer bid action payload."
    )
    assert callable(review_action), (
        "PlayerLifecycleService.record_admin_transfer_bid_review_action must record admin review "
        "audit events without accepting, rejecting, withdrawing, countering, settling, or "
        "releasing transfer-bid wallet reservations."
    )

    reviewed = review_action(
        context.window_id,
        bid.id,
        request_type(
            action="acknowledge",
            reason="wallet_reservation_verified",
            notes="Wallet reservation matches the submitted bid ledger hold.",
        ),
        actor=admin,
    )
    lifecycle_session.refresh(bid)

    assert reviewed.action_state == "audit_recorded"
    assert reviewed.business_state_changed is False
    assert reviewed.wallet_state_changed is False
    assert reviewed.review.id == bid.id
    assert reviewed.review.status == TransferBidStatus.SUBMITTED.value
    assert reviewed.review.wallet_reservation_status == "reserved"
    assert reviewed.review.wallet_reserved_amount == Decimal("300.0000")
    assert bid.status == before_status
    assert dict(bid.structured_terms_json or {}) == before_terms
    assert _wallet_snapshot(lifecycle_session, buyer) == before_wallet

    audit_events = _bid_review_audit_events(lifecycle_session, bid)
    assert len(audit_events) == 1
    audit = audit_events[0]
    assert audit.event_status == "acknowledge"
    assert audit.club_id == context.buyer_club_id
    assert audit.notes == "Wallet reservation matches the submitted bid ledger hold."
    assert audit.details_json["actor_user_id"] == admin.id
    assert audit.details_json["action"] == "acknowledge"
    assert audit.details_json["reason"] == "wallet_reservation_verified"
    assert audit.details_json["business_state_changed"] is False
    assert audit.details_json["wallet_state_changed"] is False
    reservation = audit.details_json["wallet_reservation"]
    assert reservation["status"] == "reserved"
    assert Decimal(str(reservation["amount_gtex_coin"])) == Decimal("300.0000")


def test_admin_transfer_bid_review_action_http_route_is_audit_only(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    buyer = _buyer(lifecycle_session, context)
    admin = _admin_user(lifecycle_session)
    before_wallet = _wallet_snapshot(lifecycle_session, buyer)
    before_status = bid.status
    before_terms = dict(bid.structured_terms_json or {})

    app = FastAPI()
    app.include_router(player_lifecycle_router)

    def override_session():
        yield lifecycle_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin

    with TestClient(app) as client:
        response = client.post(
            f"/api/admin/transfers/windows/{context.window_id}/bids/{bid.id}/review-actions",
            json={
                "action": "acknowledge",
                "reason": "wallet_reservation_verified",
                "notes": "Wallet reservation reviewed by admin.",
            },
        )

    assert response.status_code != 404, (
        "POST /api/admin/transfers/windows/{window_id}/bids/{bid_id}/review-actions must expose the canonical "
        "admin-safe transfer-bid review action route."
    )
    assert response.status_code == 200
    lifecycle_session.refresh(bid)
    payload = response.json()

    assert payload["action_state"] == "audit_recorded"
    assert payload["business_state_changed"] is False
    assert payload["wallet_state_changed"] is False
    assert payload["review"]["id"] == bid.id
    assert payload["review"]["status"] == TransferBidStatus.SUBMITTED.value
    assert payload["review"]["wallet_reservation_status"] == "reserved"
    assert Decimal(str(payload["review"]["wallet_reserved_amount"])) == Decimal("300.0000")
    assert bid.status == before_status
    assert dict(bid.structured_terms_json or {}) == before_terms
    assert _wallet_snapshot(lifecycle_session, buyer) == before_wallet

    audit_events = _bid_review_audit_events(lifecycle_session, bid)
    assert len(audit_events) == 1
    assert audit_events[0].event_status == "acknowledge"
    assert audit_events[0].details_json["actor_user_id"] == admin.id


def test_rejected_bid_releases_active_reservation(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))

    assert _coin_summary(lifecycle_session, _buyer(lifecycle_session, context)).reserved_balance == Decimal("300.0000")

    rejected = lifecycle_service.reject_bid(
        context.window_id,
        bid.id,
        TransferBidRejectRequest(reason="Seller chose another offer"),
    )

    buyer_summary = _coin_summary(lifecycle_session, _buyer(lifecycle_session, context))

    assert rejected.status == TransferBidStatus.REJECTED.value
    assert buyer_summary.available_balance == Decimal("1000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")
    assert buyer_summary.lock_reasons == ()


def test_accepted_bid_settles_from_reserved_funds_and_credits_seller(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))

    assert _coin_summary(lifecycle_session, _buyer(lifecycle_session, context)).reserved_balance == Decimal("300.0000")

    accepted = lifecycle_service.accept_bid(
        context.window_id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=date(2026, 3, 12),
            wage_amount=Decimal("90000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )

    buyer_summary = _coin_summary(lifecycle_session, _buyer(lifecycle_session, context))
    seller_summary = _coin_summary(lifecycle_session, _seller(lifecycle_session, context))

    assert accepted.status == TransferBidStatus.COMPLETED.value
    assert buyer_summary.available_balance == Decimal("700.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")
    assert buyer_summary.total_balance == Decimal("700.0000")
    assert seller_summary.available_balance == Decimal("300.0000")
    assert seller_summary.total_balance == Decimal("300.0000")


def test_accepted_bid_settles_reserved_balance_first_then_available_shortfall(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    buyer = _buyer(lifecycle_session, context)

    WalletService().release_transfer_bid_reservation(
        lifecycle_session,
        user=buyer,
        transfer_bid_id=bid.id,
        amount=Decimal("125.0000"),
        release_reason="partial_test_release",
        reference=f"transfer-bid:{bid.id}:partial-test-release",
        description="Partial release to verify accepted bids settle remaining holds first",
        unit=LedgerUnit.COIN,
        player_id=bid.player_id,
        buying_club_id=bid.buying_club_id,
        selling_club_id=bid.selling_club_id,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
    )
    lifecycle_session.commit()

    partially_released_summary = _coin_summary(lifecycle_session, buyer)
    assert partially_released_summary.available_balance == Decimal("825.0000")
    assert partially_released_summary.reserved_balance == Decimal("175.0000")
    assert partially_released_summary.total_balance == Decimal("1000.0000")

    accepted = lifecycle_service.accept_bid(
        context.window_id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=date(2026, 3, 12),
            wage_amount=Decimal("90000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )

    buyer_summary = _coin_summary(lifecycle_session, buyer)
    seller_summary = _coin_summary(lifecycle_session, _seller(lifecycle_session, context))
    reservation = (accepted.structured_terms_json or {})["wallet_reservation"]

    assert accepted.status == TransferBidStatus.COMPLETED.value
    assert buyer_summary.available_balance == Decimal("700.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")
    assert buyer_summary.total_balance == Decimal("700.0000")
    assert seller_summary.available_balance == Decimal("300.0000")
    assert reservation["status"] == "settled"
    assert Decimal(str(reservation["settlement_amount_gtex_coin"])) == Decimal("300.0000")
    assert Decimal(str(reservation["settled_reserved_gtex_coin"])) == Decimal("175.0000")
    assert Decimal(str(reservation["settled_available_gtex_coin"])) == Decimal("125.0000")


def test_future_accepted_bid_keeps_wallet_reserved_until_transfer_activates(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    buyer = _buyer(lifecycle_session, context)
    seller = _seller(lifecycle_session, context)

    accepted = lifecycle_service.accept_bid(
        context.window_id,
        bid.id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=date(2026, 7, 1),
            wage_amount=Decimal("90000.00"),
            signed_on=date(2026, 3, 12),
        ),
        reference_on=date(2026, 3, 12),
    )
    buyer_before_move = _coin_summary(lifecycle_session, buyer)
    seller_before_move = _coin_summary(lifecycle_session, seller)
    before_move_reservation = (accepted.structured_terms_json or {})["wallet_reservation"]

    assert accepted.status == TransferBidStatus.ACCEPTED.value
    assert buyer_before_move.available_balance == Decimal("700.0000")
    assert buyer_before_move.reserved_balance == Decimal("300.0000")
    assert buyer_before_move.total_balance == Decimal("1000.0000")
    assert seller_before_move.available_balance == Decimal("0.0000")
    assert before_move_reservation["status"] == "reserved"

    assert lifecycle_service.apply_pending_transfer_activations(
        as_of=date(2026, 7, 1),
        player_id=context.player_id,
    ) == 1
    activated_bid = lifecycle_session.get(TransferBid, bid.id)
    assert activated_bid is not None
    buyer_after_move = _coin_summary(lifecycle_session, buyer)
    seller_after_move = _coin_summary(lifecycle_session, seller)
    after_move_reservation = (activated_bid.structured_terms_json or {})["wallet_reservation"]

    assert activated_bid.status == TransferBidStatus.COMPLETED.value
    assert buyer_after_move.available_balance == Decimal("700.0000")
    assert buyer_after_move.reserved_balance == Decimal("0.0000")
    assert buyer_after_move.total_balance == Decimal("700.0000")
    assert seller_after_move.available_balance == Decimal("300.0000")
    assert after_move_reservation["status"] == "settled"


def test_withdrawn_bid_releases_active_reservation(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    bid = _create_bid(lifecycle_service, context, amount=Decimal("300.00"))
    withdraw_request_type = getattr(lifecycle_schemas, "TransferBidWithdrawRequest", None)
    withdraw_bid = getattr(lifecycle_service, "withdraw_bid", None)

    assert withdraw_request_type is not None, "TransferBidWithdrawRequest must define the withdrawn lifecycle contract"
    assert callable(withdraw_bid), "PlayerLifecycleService.withdraw_bid must release active bid reservations"
    assert _coin_summary(lifecycle_session, _buyer(lifecycle_session, context)).reserved_balance == Decimal("300.0000")

    withdrawn = withdraw_bid(
        context.window_id,
        bid.id,
        withdraw_request_type(reason="Buyer changed squad plan"),
    )
    buyer_summary = _coin_summary(lifecycle_session, _buyer(lifecycle_session, context))

    assert withdrawn.status == TransferBidStatus.WITHDRAWN.value
    assert buyer_summary.available_balance == Decimal("1000.0000")
    assert buyer_summary.reserved_balance == Decimal("0.0000")


def test_counter_replacement_releases_prior_hold_and_reserves_replacement(
    lifecycle_session: Session,
    lifecycle_service: PlayerLifecycleService,
) -> None:
    context = _seed_context(lifecycle_session)
    _create_active_contract(lifecycle_service, context)
    _fund_coin(lifecycle_session, context.buyer_owner_id, Decimal("1000.0000"))
    original = _create_bid(lifecycle_service, context, amount=Decimal("200.00"))
    counter_request_type = getattr(lifecycle_schemas, "TransferBidCounterRequest", None)
    counter_bid = getattr(lifecycle_service, "counter_bid", None)

    assert counter_request_type is not None, "TransferBidCounterRequest must define the counter replacement contract"
    assert callable(counter_bid), "PlayerLifecycleService.counter_bid must replace and re-reserve active bids"
    assert _coin_summary(lifecycle_session, _buyer(lifecycle_session, context)).reserved_balance == Decimal("200.0000")

    replacement = counter_bid(
        context.window_id,
        original.id,
        counter_request_type(
            bid_amount=Decimal("350.00"),
            wage_offer_amount=Decimal("95000.00"),
            notes="Counter with stronger salary",
        ),
        reference_on=date(2026, 3, 13),
    )
    lifecycle_session.refresh(original)
    buyer_summary = _coin_summary(lifecycle_session, _buyer(lifecycle_session, context))

    assert original.status == "counter"
    assert replacement.id != original.id
    assert replacement.status == TransferBidStatus.SUBMITTED.value
    assert buyer_summary.available_balance == Decimal("650.0000")
    assert buyer_summary.reserved_balance == Decimal("350.0000")
    assert buyer_summary.total_balance == Decimal("1000.0000")
