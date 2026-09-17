from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.transfer_market import TransferHubOffer, TransferListing, TransferNegotiation
from backend.tests.players.test_transfer_market import seed_transfer_market_context

# Import the transfer-market package so its Session lifecycle listener is registered.
from app import transfer_market as _transfer_market  # noqa: F401,E402


@pytest.fixture()
def session_factory(tmp_path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'private-negotiation.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def test_private_negotiation_materializes_on_accepted_listing_flush(
    session_factory: sessionmaker[Session],
) -> None:
    session = session_factory()
    seeded = seed_transfer_market_context(session)
    listing = TransferListing(
        id="private-negotiation-listing",
        player_id=seeded["player_id"],
        selling_club_id=seeded["seller_club_id"],
        base_price=Decimal("100.00"),
        status="accepted",
        listing_type="private_negotiation",
        closed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=3),
    )
    offer = TransferHubOffer(
        id="private-negotiation-offer",
        listing_id=listing.id,
        seller_club_id=seeded["seller_club_id"],
        bidder_club_id=seeded["buyer_club_id"],
        cash_amount=Decimal("150.00"),
        status="accepted",
        resolved_at=datetime.now(UTC),
    )
    session.add_all([listing, offer])
    session.commit()
    session.close()

    verify = session_factory()
    try:
        negotiation = verify.scalar(
            verify.query(TransferNegotiation)
            .filter(TransferNegotiation.listing_id == listing.id)
            .statement
        )
        assert negotiation is not None
        assert negotiation.player_id == seeded["player_id"]
        assert negotiation.selling_club_id == seeded["seller_club_id"]
        assert negotiation.bidder_club_id == seeded["buyer_club_id"]
        assert negotiation.status == "awaiting_contract_offer"
        assert negotiation.metadata_json["hub_offer_id"] == offer.id
        assert negotiation.clauses_json["cash_amount"] == "150.00"
    finally:
        verify.close()
