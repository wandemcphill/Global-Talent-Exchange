"""Cash, loan, and swap accepts settle the sporting move or refuse with a reason."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Player
from app.models.base import Base
from app.models.transfer_market import TransferHubOffer, TransferListing
from app.models.user import User
from app.transfer_market.service import TransferMarketService, TransferMarketValidationError
from tests.players.test_transfer_market import seed_transfer_market_context


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _open_deal(
    session: Session,
    seeded: dict[str, str],
    *,
    listing_id: str,
    offer_id: str,
    offer_type: str,
    cash_amount: Decimal = Decimal("0"),
    salary_amount: Decimal | None = None,
    contract_years: Decimal | None = None,
    loan_terms: dict | None = None,
    offered_player_ids: list[str] | None = None,
) -> None:
    session.add(
        TransferListing(
            id=listing_id,
            player_id=seeded["player_id"],
            selling_club_id=seeded["seller_club_id"],
            base_price=cash_amount or Decimal("100.00"),
            status="open",
            listing_type=offer_type,
            expires_at=datetime.now(UTC) + timedelta(days=4),
            salary_amount=salary_amount,
            contract_years_remaining=contract_years,
            loan_terms_json=dict(loan_terms or {}),
        )
    )
    session.add(
        TransferHubOffer(
            id=offer_id,
            listing_id=listing_id,
            offer_type=offer_type,
            seller_club_id=seeded["seller_club_id"],
            bidder_club_id=seeded["buyer_club_id"],
            cash_amount=cash_amount,
            offered_player_ids_json=list(offered_player_ids or []),
            loan_terms_json=dict(loan_terms or {}),
            status="open",
        )
    )
    session.commit()


def test_cash_accept_moves_the_player_and_a_second_accept_is_refused(session: Session) -> None:
    seeded = seed_transfer_market_context(session)
    _open_deal(
        session,
        seeded,
        listing_id="listing-cash",
        offer_id="offer-cash",
        offer_type="transfer",
        cash_amount=Decimal("25.00"),
        salary_amount=Decimal("400.00"),
        contract_years=Decimal("3"),
    )
    service = TransferMarketService(session)
    seller = session.get(User, seeded["seller_user_id"])
    service.accept_hub_offer("offer-cash", actor=seller)

    player = session.get(Player, seeded["player_id"])
    assert player is not None
    assert player.current_club_profile_id == seeded["buyer_club_id"]
    offer = session.get(TransferHubOffer, "offer-cash")
    assert offer is not None
    assert offer.metadata_json.get("settlement") == "completed"

    with pytest.raises(TransferMarketValidationError):
        service.accept_hub_offer("offer-cash", actor=seller)


def test_loan_accept_moves_the_player_until_the_return_date(session: Session) -> None:
    seeded = seed_transfer_market_context(session)
    _open_deal(
        session,
        seeded,
        listing_id="listing-loan",
        offer_id="offer-loan",
        offer_type="loan",
        loan_terms={"ends_on": "2027-06-30"},
    )
    service = TransferMarketService(session)
    seller = session.get(User, seeded["seller_user_id"])
    service.accept_hub_offer("offer-loan", actor=seller)

    player = session.get(Player, seeded["player_id"])
    offer = session.get(TransferHubOffer, "offer-loan")
    assert player.current_club_profile_id == seeded["buyer_club_id"]
    assert offer.metadata_json["settlement"] == "loan_active"
    assert offer.metadata_json["loan"]["return_on"] == "2027-06-30"
    assert offer.metadata_json["loan"]["origin_club_id"] == seeded["seller_club_id"]


def test_loan_without_a_return_date_is_refused(session: Session) -> None:
    seeded = seed_transfer_market_context(session)
    _open_deal(
        session,
        seeded,
        listing_id="listing-loan-open",
        offer_id="offer-loan-open",
        offer_type="loan",
    )
    service = TransferMarketService(session)
    seller = session.get(User, seeded["seller_user_id"])
    with pytest.raises(TransferMarketValidationError, match="return date"):
        service.accept_hub_offer("offer-loan-open", actor=seller)
    player = session.get(Player, seeded["player_id"])
    assert player.current_club_profile_id == seeded["seller_club_id"]


def test_swap_accept_exchanges_both_players(session: Session) -> None:
    seeded = seed_transfer_market_context(session)
    _open_deal(
        session,
        seeded,
        listing_id="listing-swap",
        offer_id="offer-swap",
        offer_type="swap",
        offered_player_ids=[seeded["buyer_player_id"]],
    )
    service = TransferMarketService(session)
    seller = session.get(User, seeded["seller_user_id"])
    service.accept_hub_offer("offer-swap", actor=seller)

    outgoing = session.get(Player, seeded["player_id"])
    incoming = session.get(Player, seeded["buyer_player_id"])
    offer = session.get(TransferHubOffer, "offer-swap")
    assert outgoing.current_club_profile_id == seeded["buyer_club_id"]
    assert incoming.current_club_profile_id == seeded["seller_club_id"]
    assert offer.metadata_json["settlement"] == "swapped"


def test_swap_of_a_player_outside_the_bidding_club_is_refused(session: Session) -> None:
    seeded = seed_transfer_market_context(session)
    _open_deal(
        session,
        seeded,
        listing_id="listing-swap-bad",
        offer_id="offer-swap-bad",
        offer_type="swap",
        offered_player_ids=[seeded["player_id"]],
    )
    service = TransferMarketService(session)
    seller = session.get(User, seeded["seller_user_id"])
    with pytest.raises(TransferMarketValidationError, match="not at the bidding club"):
        service.accept_hub_offer("offer-swap-bad", actor=seller)
