from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol

from backend.app.market.models import Listing, Offer, TradeIntent


class MarketRepository(Protocol):
    def save_listing(self, listing: Listing) -> Listing:
        ...

    def save_offer(self, offer: Offer) -> Offer:
        ...

    def save_trade_intent(self, trade_intent: TradeIntent) -> TradeIntent:
        ...

    def get_listing(self, listing_id: str) -> Listing | None:
        ...

    def get_offer(self, offer_id: str) -> Offer | None:
        ...

    def get_trade_intent(self, intent_id: str) -> TradeIntent | None:
        ...

    def list_offers_for_listing(self, listing_id: str) -> tuple[Offer, ...]:
        ...

    def list_offers_for_asset(self, asset_id: str, seller_user_id: str | None = None) -> tuple[Offer, ...]:
        ...

    def list_trade_intents_for_asset(self, asset_id: str) -> tuple[TradeIntent, ...]:
        ...

    def list_listings_for_asset(self, asset_id: str) -> tuple[Listing, ...]:
        ...

    def iter_trade_intents(self) -> tuple[TradeIntent, ...]:
        ...

    def iter_offers(self) -> tuple[Offer, ...]:
        ...

    def iter_listings(self) -> tuple[Listing, ...]:
        ...


@dataclass(slots=True)
class InMemoryMarketRepository:
    _listings: dict[str, Listing] = field(default_factory=dict)
    _offers: dict[str, Offer] = field(default_factory=dict)
    _trade_intents: dict[str, TradeIntent] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def save_listing(self, listing: Listing) -> Listing:
        with self._lock:
            self._listings[listing.listing_id] = listing
        return listing

    def save_offer(self, offer: Offer) -> Offer:
        with self._lock:
            self._offers[offer.offer_id] = offer
        return offer

    def save_trade_intent(self, trade_intent: TradeIntent) -> TradeIntent:
        with self._lock:
            self._trade_intents[trade_intent.intent_id] = trade_intent
        return trade_intent

    def get_listing(self, listing_id: str) -> Listing | None:
        with self._lock:
            return self._listings.get(listing_id)

    def get_offer(self, offer_id: str) -> Offer | None:
        with self._lock:
            return self._offers.get(offer_id)

    def get_trade_intent(self, intent_id: str) -> TradeIntent | None:
        with self._lock:
            return self._trade_intents.get(intent_id)

    def list_offers_for_listing(self, listing_id: str) -> tuple[Offer, ...]:
        with self._lock:
            return tuple(offer for offer in self._offers.values() if offer.listing_id == listing_id)

    def list_offers_for_asset(self, asset_id: str, seller_user_id: str | None = None) -> tuple[Offer, ...]:
        with self._lock:
            return tuple(
                offer
                for offer in self._offers.values()
                if offer.asset_id == asset_id and (seller_user_id is None or offer.seller_user_id == seller_user_id)
            )

    def list_trade_intents_for_asset(self, asset_id: str) -> tuple[TradeIntent, ...]:
        with self._lock:
            return tuple(intent for intent in self._trade_intents.values() if intent.asset_id == asset_id)

    def list_listings_for_asset(self, asset_id: str) -> tuple[Listing, ...]:
        with self._lock:
            return tuple(listing for listing in self._listings.values() if listing.asset_id == asset_id)

    def iter_trade_intents(self) -> tuple[TradeIntent, ...]:
        with self._lock:
            return tuple(self._trade_intents.values())

    def iter_offers(self) -> tuple[Offer, ...]:
        with self._lock:
            return tuple(self._offers.values())

    def iter_listings(self) -> tuple[Listing, ...]:
        with self._lock:
            return tuple(self._listings.values())
