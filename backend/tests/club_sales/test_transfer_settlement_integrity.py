from __future__ import annotations

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.club_sale_market.schemas import ClubSaleTransferExecuteRequest
from app.club_sale_market.service import ClubSaleMarketError, ClubSaleMarketService
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.routes.transfers import router as transfers_router
from app.wallets.service import LedgerPosting, WalletService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, user_id: str, email: str, username: str) -> User:
    user = User(id=user_id, email=email, username=username, password_hash="hashed")
    session.add(user)
    session.flush()
    return user


def _create_club(session, *, club_id: str, owner_user_id: str) -> ClubProfile:
    club = ClubProfile(
        id=club_id,
        owner_user_id=owner_user_id,
        club_name="Integrity FC",
        short_name="IFC",
        slug=f"integrity-fc-{club_id}",
        crest_asset_ref=None,
        primary_color="#112233",
        secondary_color="#ddeeff",
        accent_color="#44aa66",
        home_venue_name="Integrity Park",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        description="Integrity test club",
        visibility="public",
        founded_at=None,
    )
    session.add(club)
    session.flush()
    return club


def _seed_wallet(session, wallet: WalletService, user: User, *, amount: Decimal) -> None:
    account = wallet.get_user_account(session, user, LedgerUnit.COIN)
    platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform, amount=-amount),
            LedgerPosting(account=account, amount=amount),
        ],
        reason=wallet.trade_settlement_reason,
        reference="seed-wallet",
        description="Seeding test wallet",
        external_reference="seed-wallet",
        actor=user,
    )


def test_transfers_router_reexport_exists() -> None:
    assert transfers_router is not None
    assert hasattr(transfers_router, "routes")


def test_club_sale_transfer_execute_request_schema_optional_price() -> None:
    req_no_price = ClubSaleTransferExecuteRequest(offer_id="off-1")
    assert req_no_price.offer_id == "off-1"
    assert req_no_price.executed_sale_price is None

    req_with_price = ClubSaleTransferExecuteRequest(offer_id="off-2", executed_sale_price=Decimal("150.0000"))
    assert req_with_price.executed_sale_price == Decimal("150.0000")


def test_transfer_settlement_binds_to_persistent_offer_price(session) -> None:
    wallet = WalletService()
    service = ClubSaleMarketService(session=session, wallet_service=wallet)
    seller = _create_user(session, user_id="seller-u1", email="seller@test.gtex", username="seller_u1")
    buyer = _create_user(session, user_id="buyer-u2", email="buyer@test.gtex", username="buyer_u2")
    club = _create_club(session, club_id="club-settle-test", owner_user_id=seller.id)
    _seed_wallet(session, wallet, buyer, amount=Decimal("500.0000"))

    service.create_listing(
        actor=seller,
        club_id=club.id,
        asking_price=Decimal("100.0000"),
        visibility="public",
        note="Public asking price is visible.",
        metadata_json={"channel": "open-market"},
    )
    inquiry = service.create_inquiry(
        actor=buyer,
        club_id=club.id,
        message="Interested buyer ready to talk.",
        metadata_json={"origin": "public-profile"},
    )
    offer = service.create_offer(
        actor=buyer,
        club_id=club.id,
        offer_price=Decimal("95.0000"),
        inquiry_id=inquiry["inquiry_id"],
        message="Cash buyer, ready to settle.",
        expires_at=None,
        metadata_json={"deal": "cash"},
    )
    service.accept_offer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        message="Accepted pending settlement.",
    )

    # 1. Tampered caller price MUST fail with club_sale_transfer_price_mismatch
    with pytest.raises(ClubSaleMarketError, match="must match the accepted offer price"):
        service.execute_transfer(
            actor=seller,
            club_id=club.id,
            offer_id=offer["offer_id"],
            executed_sale_price=Decimal("50.0000"),  # Tampered price
        )

    # 2. Omitting executed_sale_price (None) MUST succeed and authoritatively settle at offer.offered_price
    transfer = service.execute_transfer(
        actor=seller,
        club_id=club.id,
        offer_id=offer["offer_id"],
        executed_sale_price=None,  # No caller price supplied; binds strictly to DB offer
    )
    assert transfer["executed_sale_price"] == Decimal("95.0000")
    assert transfer["status"] == "settled"
