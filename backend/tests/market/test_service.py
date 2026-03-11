import pytest

from backend.app.market import (
    ListingStatus,
    ListingType,
    MarketConflictError,
    MarketEngine,
    MarketValidationError,
    OfferStatus,
    TradeIntentDirection,
    TradeIntentStatus,
)


def test_transfer_listing_requires_ask_price() -> None:
    engine = MarketEngine()

    with pytest.raises(MarketValidationError):
        engine.create_listing(
            asset_id="asset-1",
            seller_user_id="seller-1",
            listing_type=ListingType.TRANSFER,
        )


def test_duplicate_open_listing_for_same_asset_is_rejected() -> None:
    engine = MarketEngine()
    engine.create_listing(
        asset_id="asset-1",
        seller_user_id="seller-1",
        listing_type=ListingType.TRANSFER,
        ask_price=150,
    )

    with pytest.raises(MarketConflictError):
        engine.create_listing(
            asset_id="asset-1",
            seller_user_id="seller-1",
            listing_type=ListingType.TRANSFER,
            ask_price=160,
        )


def test_listing_offer_counter_accept_flow_completes_listing() -> None:
    engine = MarketEngine()
    listing = engine.create_listing(
        asset_id="asset-1",
        seller_user_id="seller-1",
        listing_type=ListingType.HYBRID,
        ask_price=120,
        desired_asset_ids=("asset-x",),
    )

    initial_offer = engine.create_offer(
        asset_id=listing.asset_id,
        seller_user_id=listing.seller_user_id,
        buyer_user_id="buyer-1",
        listing_id=listing.listing_id,
        cash_amount=90,
        offered_asset_ids=("asset-x",),
    )
    competing_offer = engine.create_offer(
        asset_id=listing.asset_id,
        seller_user_id=listing.seller_user_id,
        buyer_user_id="buyer-2",
        listing_id=listing.listing_id,
        cash_amount=120,
    )

    counter = engine.counter_offer(
        offer_id=initial_offer.offer_id,
        acting_user_id="seller-1",
        cash_amount=110,
        offered_asset_ids=("asset-x",),
    )
    accepted = engine.accept_offer(offer_id=counter.offer_id, acting_user_id="buyer-1")

    assert accepted.status is OfferStatus.ACCEPTED
    assert engine.get_listing(listing.listing_id).status is ListingStatus.COMPLETED
    assert engine.get_offer(initial_offer.offer_id).status is OfferStatus.COUNTERED
    assert engine.get_offer(competing_offer.offer_id).status is OfferStatus.REJECTED


def test_direct_offer_flow_works_without_listing() -> None:
    engine = MarketEngine()

    offer = engine.create_offer(
        asset_id="asset-9",
        seller_user_id="seller-9",
        buyer_user_id="buyer-9",
        cash_amount=75,
    )
    accepted = engine.accept_offer(offer_id=offer.offer_id, acting_user_id="seller-9")

    assert accepted.status is OfferStatus.ACCEPTED
    offers = engine.list_offers_for_asset(asset_id="asset-9", seller_user_id="seller-9")
    assert offers[0].listing_id is None


def test_trade_intent_matches_open_listing_and_is_fulfilled_on_sale() -> None:
    engine = MarketEngine()
    listing = engine.create_listing(
        asset_id="asset-10",
        seller_user_id="seller-10",
        listing_type=ListingType.TRANSFER,
        ask_price=95,
    )
    buy_intent = engine.create_trade_intent(
        user_id="buyer-10",
        asset_id="asset-10",
        direction=TradeIntentDirection.BUY,
        price_ceiling=100,
    )

    matches = engine.match_trade_intents(listing_id=listing.listing_id)
    offer = engine.create_offer(
        asset_id="asset-10",
        seller_user_id="seller-10",
        buyer_user_id="buyer-10",
        listing_id=listing.listing_id,
        cash_amount=95,
    )
    engine.accept_offer(offer_id=offer.offer_id, acting_user_id="seller-10")

    assert [intent.intent_id for intent in matches] == [buy_intent.intent_id]
    assert engine.get_trade_intent(buy_intent.intent_id).status is TradeIntentStatus.FULFILLED


def test_swap_intent_requires_assets_or_cash_ceiling() -> None:
    engine = MarketEngine()

    with pytest.raises(MarketValidationError):
        engine.create_trade_intent(
            user_id="buyer-1",
            asset_id="asset-11",
            direction=TradeIntentDirection.SWAP,
        )


def test_cancelling_listing_rejects_pending_listing_offers() -> None:
    engine = MarketEngine()
    listing = engine.create_listing(
        asset_id="asset-12",
        seller_user_id="seller-12",
        listing_type=ListingType.TRANSFER,
        ask_price=130,
    )
    offer = engine.create_offer(
        asset_id="asset-12",
        seller_user_id="seller-12",
        buyer_user_id="buyer-12",
        listing_id=listing.listing_id,
        cash_amount=130,
    )

    cancelled = engine.cancel_listing(listing_id=listing.listing_id, acting_user_id="seller-12")

    assert cancelled.status is ListingStatus.CANCELLED
    assert engine.get_offer(offer.offer_id).status is OfferStatus.REJECTED
