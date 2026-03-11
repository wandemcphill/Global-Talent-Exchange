from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import uuid4

from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.market.models import (
    Listing,
    ListingStatus,
    ListingType,
    Offer,
    OfferStatus,
    TradeIntent,
    TradeIntentDirection,
    TradeIntentStatus,
    utcnow,
)
from backend.app.market.projections import MarketSummaryProjector
from backend.app.market.repositories import InMemoryMarketRepository, MarketRepository


class MarketError(Exception):
    pass


class MarketConflictError(MarketError):
    pass


class MarketNotFoundError(MarketError):
    pass


class MarketPermissionError(MarketError):
    pass


class MarketValidationError(MarketError):
    pass


class MarketEngine:
    def __init__(
        self,
        *,
        repository: MarketRepository | None = None,
        summary_projector: MarketSummaryProjector | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.repository = repository or InMemoryMarketRepository()
        self.summary_projector = summary_projector
        self.event_publisher = event_publisher or InMemoryEventPublisher()

    def create_listing(
        self,
        *,
        asset_id: str,
        seller_user_id: str,
        listing_type: ListingType | str,
        ask_price: int | None = None,
        desired_asset_ids: tuple[str, ...] | list[str] = (),
        note: str | None = None,
    ) -> Listing:
        normalized_listing_type = ListingType(listing_type)
        normalized_desired_asset_ids = self._normalize_asset_ids(desired_asset_ids)
        self._validate_listing_payload(
            listing_type=normalized_listing_type,
            ask_price=ask_price,
            desired_asset_ids=normalized_desired_asset_ids,
        )

        if self._has_open_listing(asset_id=asset_id, seller_user_id=seller_user_id):
            raise MarketConflictError("asset already has an open listing for this seller")

        now = utcnow()
        listing = Listing(
            listing_id=self._new_id("lst"),
            asset_id=asset_id,
            seller_user_id=seller_user_id,
            listing_type=normalized_listing_type,
            ask_price=ask_price,
            desired_asset_ids=normalized_desired_asset_ids,
            note=note,
            status=ListingStatus.OPEN,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_listing(listing)
        self._after_asset_mutation(
            asset_id=asset_id,
            event_name="market.listing.created",
            payload={
                "listing_id": listing.listing_id,
                "asset_id": asset_id,
                "seller_user_id": seller_user_id,
                "listing_type": listing.listing_type.value,
                "ask_price": listing.ask_price,
            },
        )
        return listing

    def cancel_listing(self, *, listing_id: str, acting_user_id: str) -> Listing:
        listing = self.get_listing(listing_id)
        if listing.seller_user_id != acting_user_id:
            raise MarketPermissionError("only the seller can cancel the listing")
        if listing.status != ListingStatus.OPEN:
            raise MarketConflictError("listing is not open")

        updated_listing = self._store_listing(
            replace(listing, status=ListingStatus.CANCELLED, updated_at=utcnow())
        )
        self._reject_pending_offers(
            asset_id=listing.asset_id,
            seller_user_id=listing.seller_user_id,
            listing_id=listing_id,
        )
        self._after_asset_mutation(
            asset_id=listing.asset_id,
            event_name="market.listing.cancelled",
            payload={
                "listing_id": listing.listing_id,
                "asset_id": listing.asset_id,
                "seller_user_id": listing.seller_user_id,
            },
        )
        return updated_listing

    def create_offer(
        self,
        *,
        asset_id: str,
        seller_user_id: str,
        buyer_user_id: str,
        cash_amount: int = 0,
        offered_asset_ids: tuple[str, ...] | list[str] = (),
        listing_id: str | None = None,
        note: str | None = None,
    ) -> Offer:
        normalized_offered_asset_ids = self._normalize_asset_ids(offered_asset_ids)
        self._validate_offer_terms(cash_amount=cash_amount, offered_asset_ids=normalized_offered_asset_ids)

        if seller_user_id == buyer_user_id:
            raise MarketValidationError("seller and buyer must be different users")

        if listing_id is not None:
            listing = self.get_listing(listing_id)
            if listing.status != ListingStatus.OPEN:
                raise MarketConflictError("listing is not open")
            if listing.asset_id != asset_id or listing.seller_user_id != seller_user_id:
                raise MarketValidationError("offer target does not match listing")

        if self._has_pending_negotiation(
            asset_id=asset_id,
            seller_user_id=seller_user_id,
            buyer_user_id=buyer_user_id,
            listing_id=listing_id,
        ):
            raise MarketConflictError("an active negotiation already exists for this buyer and target")

        now = utcnow()
        offer = Offer(
            offer_id=self._new_id("off"),
            asset_id=asset_id,
            listing_id=listing_id,
            seller_user_id=seller_user_id,
            buyer_user_id=buyer_user_id,
            proposer_user_id=buyer_user_id,
            recipient_user_id=seller_user_id,
            cash_amount=cash_amount,
            offered_asset_ids=normalized_offered_asset_ids,
            note=note,
            status=OfferStatus.PENDING,
            parent_offer_id=None,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_offer(offer)
        self._after_asset_mutation(
            asset_id=asset_id,
            event_name="market.offer.created",
            payload={
                "offer_id": offer.offer_id,
                "asset_id": asset_id,
                "seller_user_id": seller_user_id,
                "buyer_user_id": buyer_user_id,
                "listing_id": listing_id,
                "cash_amount": cash_amount,
            },
        )
        return offer

    def counter_offer(
        self,
        *,
        offer_id: str,
        acting_user_id: str,
        cash_amount: int = 0,
        offered_asset_ids: tuple[str, ...] | list[str] = (),
        note: str | None = None,
    ) -> Offer:
        offer = self.get_offer(offer_id)
        if offer.status != OfferStatus.PENDING:
            raise MarketConflictError("only pending offers can be countered")
        if offer.recipient_user_id != acting_user_id:
            raise MarketPermissionError("only the recipient can counter the offer")

        normalized_offered_asset_ids = self._normalize_asset_ids(offered_asset_ids)
        self._validate_offer_terms(cash_amount=cash_amount, offered_asset_ids=normalized_offered_asset_ids)

        self._store_offer(replace(offer, status=OfferStatus.COUNTERED, updated_at=utcnow()))

        now = utcnow()
        counter = Offer(
            offer_id=self._new_id("off"),
            asset_id=offer.asset_id,
            listing_id=offer.listing_id,
            seller_user_id=offer.seller_user_id,
            buyer_user_id=offer.buyer_user_id,
            proposer_user_id=acting_user_id,
            recipient_user_id=offer.proposer_user_id,
            cash_amount=cash_amount,
            offered_asset_ids=normalized_offered_asset_ids,
            note=note,
            status=OfferStatus.PENDING,
            parent_offer_id=offer.offer_id,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_offer(counter)
        self._after_asset_mutation(
            asset_id=offer.asset_id,
            event_name="market.offer.countered",
            payload={
                "offer_id": counter.offer_id,
                "asset_id": offer.asset_id,
                "seller_user_id": offer.seller_user_id,
                "buyer_user_id": offer.buyer_user_id,
                "listing_id": offer.listing_id,
                "cash_amount": cash_amount,
            },
        )
        return counter

    def accept_offer(self, *, offer_id: str, acting_user_id: str) -> Offer:
        offer = self.get_offer(offer_id)
        if offer.status != OfferStatus.PENDING:
            raise MarketConflictError("only pending offers can be accepted")
        if offer.recipient_user_id != acting_user_id:
            raise MarketPermissionError("only the recipient can accept the offer")

        accepted_offer = self._store_offer(replace(offer, status=OfferStatus.ACCEPTED, updated_at=utcnow()))

        if offer.listing_id is not None:
            listing = self.get_listing(offer.listing_id)
            if listing.status == ListingStatus.OPEN:
                self._store_listing(
                    replace(listing, status=ListingStatus.COMPLETED, updated_at=utcnow())
                )

        self._reject_pending_offers(
            asset_id=offer.asset_id,
            seller_user_id=offer.seller_user_id,
            exclude_offer_id=offer.offer_id,
        )
        self._fulfill_trade_intents(offer)
        self._after_asset_mutation(
            asset_id=offer.asset_id,
            event_name="market.offer.accepted",
            payload={
                "offer_id": offer.offer_id,
                "asset_id": offer.asset_id,
                "seller_user_id": offer.seller_user_id,
                "buyer_user_id": offer.buyer_user_id,
                "listing_id": offer.listing_id,
            },
        )
        return accepted_offer

    def reject_offer(self, *, offer_id: str, acting_user_id: str) -> Offer:
        offer = self.get_offer(offer_id)
        if offer.status != OfferStatus.PENDING:
            raise MarketConflictError("only pending offers can be rejected")
        if offer.recipient_user_id != acting_user_id:
            raise MarketPermissionError("only the recipient can reject the offer")
        rejected_offer = self._store_offer(replace(offer, status=OfferStatus.REJECTED, updated_at=utcnow()))
        self._after_asset_mutation(
            asset_id=offer.asset_id,
            event_name="market.offer.rejected",
            payload={
                "offer_id": offer.offer_id,
                "asset_id": offer.asset_id,
                "seller_user_id": offer.seller_user_id,
                "buyer_user_id": offer.buyer_user_id,
                "listing_id": offer.listing_id,
            },
        )
        return rejected_offer

    def create_trade_intent(
        self,
        *,
        user_id: str,
        asset_id: str,
        direction: TradeIntentDirection | str,
        price_floor: int | None = None,
        price_ceiling: int | None = None,
        offered_asset_ids: tuple[str, ...] | list[str] = (),
        note: str | None = None,
    ) -> TradeIntent:
        normalized_direction = TradeIntentDirection(direction)
        normalized_offered_asset_ids = self._normalize_asset_ids(offered_asset_ids)
        self._validate_trade_intent_terms(
            direction=normalized_direction,
            price_floor=price_floor,
            price_ceiling=price_ceiling,
            offered_asset_ids=normalized_offered_asset_ids,
        )

        for intent in self.repository.iter_trade_intents():
            if (
                intent.user_id == user_id
                and intent.asset_id == asset_id
                and intent.direction == normalized_direction
                and intent.status == TradeIntentStatus.ACTIVE
            ):
                raise MarketConflictError("an active trade intent already exists for this user and asset")

        now = utcnow()
        trade_intent = TradeIntent(
            intent_id=self._new_id("int"),
            user_id=user_id,
            asset_id=asset_id,
            direction=normalized_direction,
            price_floor=price_floor,
            price_ceiling=price_ceiling,
            offered_asset_ids=normalized_offered_asset_ids,
            note=note,
            status=TradeIntentStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_trade_intent(trade_intent)
        self._after_asset_mutation(
            asset_id=asset_id,
            event_name="market.trade_intent.created",
            payload={
                "intent_id": trade_intent.intent_id,
                "asset_id": asset_id,
                "user_id": user_id,
                "direction": trade_intent.direction.value,
            },
        )
        return trade_intent

    def withdraw_trade_intent(self, *, intent_id: str, acting_user_id: str) -> TradeIntent:
        intent = self.get_trade_intent(intent_id)
        if intent.user_id != acting_user_id:
            raise MarketPermissionError("only the owner can withdraw the trade intent")
        if intent.status != TradeIntentStatus.ACTIVE:
            raise MarketConflictError("trade intent is not active")
        withdrawn_intent = self._store_trade_intent(
            replace(intent, status=TradeIntentStatus.WITHDRAWN, updated_at=utcnow())
        )
        self._after_asset_mutation(
            asset_id=intent.asset_id,
            event_name="market.trade_intent.withdrawn",
            payload={
                "intent_id": intent.intent_id,
                "asset_id": intent.asset_id,
                "user_id": intent.user_id,
            },
        )
        return withdrawn_intent

    def match_trade_intents(self, *, listing_id: str) -> tuple[TradeIntent, ...]:
        listing = self.get_listing(listing_id)
        matches: list[TradeIntent] = []
        for intent in self.repository.iter_trade_intents():
            if intent.status != TradeIntentStatus.ACTIVE:
                continue
            if intent.asset_id != listing.asset_id:
                continue
            if intent.user_id == listing.seller_user_id:
                continue
            if self._listing_matches_intent(listing, intent):
                matches.append(intent)
        matches.sort(key=lambda item: item.created_at)
        return tuple(matches)

    def get_listing(self, listing_id: str) -> Listing:
        listing = self.repository.get_listing(listing_id)
        if listing is None:
            raise MarketNotFoundError(f"listing {listing_id} was not found")
        return listing

    def get_offer(self, offer_id: str) -> Offer:
        offer = self.repository.get_offer(offer_id)
        if offer is None:
            raise MarketNotFoundError(f"offer {offer_id} was not found")
        return offer

    def get_trade_intent(self, intent_id: str) -> TradeIntent:
        trade_intent = self.repository.get_trade_intent(intent_id)
        if trade_intent is None:
            raise MarketNotFoundError(f"trade intent {intent_id} was not found")
        return trade_intent

    def list_offers_for_listing(self, *, listing_id: str) -> tuple[Offer, ...]:
        return self.repository.list_offers_for_listing(listing_id)

    def list_offers_for_asset(self, *, asset_id: str, seller_user_id: str) -> tuple[Offer, ...]:
        return self.repository.list_offers_for_asset(asset_id, seller_user_id)

    def _reject_pending_offers(
        self,
        *,
        asset_id: str,
        seller_user_id: str,
        exclude_offer_id: str | None = None,
        listing_id: str | None = None,
    ) -> None:
        for offer in self.repository.iter_offers():
            if offer.offer_id == exclude_offer_id:
                continue
            if offer.asset_id != asset_id or offer.seller_user_id != seller_user_id:
                continue
            if listing_id is not None and offer.listing_id != listing_id:
                continue
            if offer.status != OfferStatus.PENDING:
                continue
            self._store_offer(replace(offer, status=OfferStatus.REJECTED, updated_at=utcnow()))

    def _fulfill_trade_intents(self, offer: Offer) -> None:
        for intent in self.repository.iter_trade_intents():
            if intent.status != TradeIntentStatus.ACTIVE or intent.asset_id != offer.asset_id:
                continue
            if intent.user_id == offer.buyer_user_id and intent.direction in {
                TradeIntentDirection.BUY,
                TradeIntentDirection.SWAP,
            }:
                self._store_trade_intent(
                    replace(intent, status=TradeIntentStatus.FULFILLED, updated_at=utcnow())
                )
            if intent.user_id == offer.seller_user_id and intent.direction in {
                TradeIntentDirection.SELL,
                TradeIntentDirection.SWAP,
            }:
                self._store_trade_intent(
                    replace(intent, status=TradeIntentStatus.FULFILLED, updated_at=utcnow())
                )

    def _listing_matches_intent(self, listing: Listing, intent: TradeIntent) -> bool:
        if intent.direction == TradeIntentDirection.BUY:
            if listing.listing_type == ListingType.SWAP or listing.ask_price is None:
                return False
            return intent.price_ceiling is None or listing.ask_price <= intent.price_ceiling

        if intent.direction == TradeIntentDirection.SELL:
            return False

        if listing.listing_type == ListingType.TRANSFER:
            return False

        if listing.desired_asset_ids and intent.offered_asset_ids:
            if not set(listing.desired_asset_ids).intersection(intent.offered_asset_ids):
                return False

        if listing.ask_price is not None and intent.price_ceiling is not None:
            return listing.ask_price <= intent.price_ceiling

        return True

    def _store_listing(self, listing: Listing) -> Listing:
        return self.repository.save_listing(listing)

    def _store_offer(self, offer: Offer) -> Offer:
        return self.repository.save_offer(offer)

    def _store_trade_intent(self, trade_intent: TradeIntent) -> TradeIntent:
        return self.repository.save_trade_intent(trade_intent)

    def _has_open_listing(self, *, asset_id: str, seller_user_id: str) -> bool:
        return any(
            listing.asset_id == asset_id
            and listing.seller_user_id == seller_user_id
            and listing.status == ListingStatus.OPEN
            for listing in self.repository.iter_listings()
        )

    def _has_pending_negotiation(
        self,
        *,
        asset_id: str,
        seller_user_id: str,
        buyer_user_id: str,
        listing_id: str | None,
    ) -> bool:
        return any(
            offer.asset_id == asset_id
            and offer.seller_user_id == seller_user_id
            and offer.buyer_user_id == buyer_user_id
            and offer.listing_id == listing_id
            and offer.status == OfferStatus.PENDING
            for offer in self.repository.iter_offers()
        )

    def _validate_listing_payload(
        self,
        *,
        listing_type: ListingType,
        ask_price: int | None,
        desired_asset_ids: tuple[str, ...],
    ) -> None:
        if ask_price is not None and ask_price <= 0:
            raise MarketValidationError("ask price must be positive")

        if listing_type == ListingType.TRANSFER:
            if ask_price is None:
                raise MarketValidationError("transfer listings require an ask price")
            if desired_asset_ids:
                raise MarketValidationError("transfer listings cannot request swap assets")
            return

        if listing_type == ListingType.SWAP:
            if not desired_asset_ids:
                raise MarketValidationError("swap listings require desired assets")
            return

        if ask_price is None and not desired_asset_ids:
            raise MarketValidationError("hybrid listings require a price, desired assets, or both")

    def _validate_offer_terms(self, *, cash_amount: int, offered_asset_ids: tuple[str, ...]) -> None:
        if cash_amount < 0:
            raise MarketValidationError("cash amount cannot be negative")
        if cash_amount == 0 and not offered_asset_ids:
            raise MarketValidationError("offers must include cash, assets, or both")
        if len(offered_asset_ids) > 2:
            raise MarketValidationError("offers can include at most two player assets")

    def _validate_trade_intent_terms(
        self,
        *,
        direction: TradeIntentDirection,
        price_floor: int | None,
        price_ceiling: int | None,
        offered_asset_ids: tuple[str, ...],
    ) -> None:
        if price_floor is not None and price_floor <= 0:
            raise MarketValidationError("price floor must be positive")
        if price_ceiling is not None and price_ceiling <= 0:
            raise MarketValidationError("price ceiling must be positive")
        if price_floor is not None and price_ceiling is not None and price_floor > price_ceiling:
            raise MarketValidationError("price floor cannot exceed price ceiling")
        if len(offered_asset_ids) > 2:
            raise MarketValidationError("trade intents can reference at most two player assets")

        if direction == TradeIntentDirection.BUY and price_floor is not None:
            raise MarketValidationError("buy intents cannot set a price floor")

        if direction == TradeIntentDirection.SELL and price_ceiling is not None:
            raise MarketValidationError("sell intents cannot set a price ceiling")

        if direction == TradeIntentDirection.SWAP and not offered_asset_ids and price_ceiling is None:
            raise MarketValidationError("swap intents require offered assets or a cash ceiling")

    def _normalize_asset_ids(self, asset_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for asset_id in asset_ids:
            if not asset_id or not asset_id.strip():
                raise MarketValidationError("asset ids must be non-empty strings")
            value = asset_id.strip()
            if value not in seen:
                normalized.append(value)
                seen.add(value)
        return tuple(normalized)

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    def _after_asset_mutation(self, *, asset_id: str, event_name: str, payload: dict[str, Any]) -> None:
        self._project_asset_summary(asset_id)
        self.event_publisher.publish(DomainEvent(name=event_name, payload=payload))

    def _project_asset_summary(self, asset_id: str) -> None:
        if self.summary_projector is None:
            return
        self.summary_projector.rebuild_asset_summary(
            asset_id=asset_id,
            listings=self.repository.list_listings_for_asset(asset_id),
            offers=self.repository.list_offers_for_asset(asset_id),
            trade_intents=self.repository.list_trade_intents_for_asset(asset_id),
        )
