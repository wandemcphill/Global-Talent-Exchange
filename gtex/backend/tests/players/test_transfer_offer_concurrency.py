"""Concurrency coverage for Transfer Hub offer resolution.

Accepting a hub offer closes the listing and rejects every sibling offer. That
transition used to be a read-then-write: the handler checked ``offer.status``
on an object loaded in its own transaction, then wrote the new status. Two
request-scoped sessions resolving *different* offers on the *same* listing both
observed an open listing and both closed it, so a single player ended up sold
twice.

These tests pin the invariant that survives concurrent resolution: at most one
offer on a listing may reach ``accepted``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.transfer_market import TransferHubOffer, TransferListing
from app.models.user import User
from app.transfer_market.service import TransferMarketService, TransferMarketValidationError
from backend.tests.players.test_transfer_market import seed_transfer_market_context

LISTING_ID = "listing-concurrency"


@pytest.fixture(autouse=True)
def _configure_test_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_DATABASE_URL", "sqlite+pysqlite:///:memory:")


@pytest.fixture()
def session_factory(tmp_path) -> sessionmaker[Session]:
    """A file-backed engine so independent sessions get independent transactions."""
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'transfer-concurrency.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def context(session_factory: sessionmaker[Session]) -> dict[str, str]:
    """One open listing carrying two competing offers from the same seller."""
    session = session_factory()
    seeded = seed_transfer_market_context(session)
    session.add(
        TransferListing(
            id=LISTING_ID,
            player_id=seeded["player_id"],
            selling_club_id=seeded["seller_club_id"],
            base_price=Decimal("100.00"),
            status="open",
            expires_at=datetime.now(UTC) + timedelta(days=3),
        )
    )
    for offer_id in ("offer-first", "offer-second"):
        session.add(
            TransferHubOffer(
                id=offer_id,
                listing_id=LISTING_ID,
                seller_club_id=seeded["seller_club_id"],
                bidder_club_id=seeded["buyer_club_id"],
                cash_amount=Decimal("150.00"),
                status="open",
            )
        )
    session.commit()
    session.close()
    return seeded


def _accept(factory: sessionmaker[Session], *, offer_id: str, user_id: str) -> None:
    session = factory()
    try:
        service = TransferMarketService(session)
        service.accept_hub_offer(offer_id, actor=session.get(User, user_id))
    finally:
        session.close()


def test_concurrent_accepts_on_one_listing_settle_a_single_winner(
    session_factory: sessionmaker[Session],
    context: dict[str, str],
) -> None:
    seller_id = context["seller_user_id"]

    first = session_factory()
    second = session_factory()
    try:
        service_first = TransferMarketService(first)
        service_second = TransferMarketService(second)
        # Both transactions load their offer *and hold it* while the listing is
        # still open, which is the interleaving two concurrent requests produce:
        # each handler reads before either has committed. The strong references
        # matter -- SQLAlchemy's identity map is weak, so dropping them would
        # let the second session re-read post-commit state and quietly model a
        # sequential run instead of a concurrent one.
        first_offer = first.get(TransferHubOffer, "offer-first")
        second_offer = second.get(TransferHubOffer, "offer-second")
        assert first_offer.status == "open"
        assert second_offer.status == "open"

        service_first.accept_hub_offer("offer-first", actor=first.get(User, seller_id))
        # The second session still sees its pre-commit snapshot ...
        assert second_offer.status == "open"
        # ... so the guard has to be enforced by the write itself.
        with pytest.raises(TransferMarketValidationError):
            service_second.accept_hub_offer("offer-second", actor=second.get(User, seller_id))
    finally:
        first.close()
        second.close()

    verify = session_factory()
    offers = {offer.id: offer.status for offer in verify.query(TransferHubOffer).all()}
    listing = verify.get(TransferListing, LISTING_ID)
    verify.close()

    assert sorted(offers) == ["offer-first", "offer-second"]
    assert [oid for oid, state in offers.items() if state == "accepted"] == ["offer-first"]
    assert offers["offer-second"] == "rejected"
    assert listing.status == "accepted"


def test_single_accept_still_closes_the_listing_and_rejects_siblings(
    session_factory: sessionmaker[Session],
    context: dict[str, str],
) -> None:
    _accept(session_factory, offer_id="offer-first", user_id=context["seller_user_id"])

    verify = session_factory()
    offers = {offer.id: offer.status for offer in verify.query(TransferHubOffer).all()}
    listing = verify.get(TransferListing, LISTING_ID)
    verify.close()

    assert offers == {"offer-first": "accepted", "offer-second": "rejected"}
    assert listing.status == "accepted"


def test_reaccepting_a_settled_offer_is_refused(
    session_factory: sessionmaker[Session],
    context: dict[str, str],
) -> None:
    _accept(session_factory, offer_id="offer-first", user_id=context["seller_user_id"])

    replay = session_factory()
    try:
        service = TransferMarketService(replay)
        with pytest.raises(TransferMarketValidationError):
            service.accept_hub_offer("offer-first", actor=replay.get(User, context["seller_user_id"]))
    finally:
        replay.close()

    verify = session_factory()
    accepted = [offer.id for offer in verify.query(TransferHubOffer).all() if offer.status == "accepted"]
    verify.close()
    assert accepted == ["offer-first"]
