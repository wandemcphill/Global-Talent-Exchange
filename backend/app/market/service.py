from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app.core.cache import CacheBackend, NullCacheBackend
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.football_events_engine.service import PlayerRealWorldImpact, RealWorldFootballEventService
from app.market.player_eligibility_policy import is_transfer_market_eligible
from app.market.models import (
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
from app.market.projections import MarketSummaryProjector
from app.market.repositories import (
    InMemoryMarketRepository,
    MarketPlayerRecord,
    MarketRepository,
    SqlAlchemyMarketPlayerRepository,
)
from app.models.transfer_market import TransferListing
from app.pricing.models import CandleSeries, MarketMoverItem, MarketMovers, PlayerExecution, PlayerPricingSnapshot
from app.pricing.service import MarketPricingService, PricingValidationError
from app.schemas.avatar import PlayerAvatarView
from app.services.avatar_service import AvatarIdentityInput, AvatarService
from app.services.runtime_control_service import RuntimeControlService
from app.value_engine.authority import authoritative_reference_credits
from app.value_engine.pricing_curve import round_gtex_display_value
from app.value_engine.scoring import credits_from_real_world_value
from sqlalchemy import select
from sqlalchemy.orm import Session


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


PLAYER_DISCOVERY_SORTS = frozenset({"current_value", "trend_score", "age", "name"})


class MarketEngine:
    def __init__(
        self,
        *,
        repository: MarketRepository | None = None,
        summary_projector: MarketSummaryProjector | None = None,
        event_publisher: EventPublisher | None = None,
        pricing_service: MarketPricingService | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.repository = repository or InMemoryMarketRepository()
        self.summary_projector = summary_projector
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        session_factory = self.summary_projector.session_factory if self.summary_projector is not None else None
        self.pricing_service = pricing_service or MarketPricingService(
            session_factory=session_factory,
            cache_backend=cache_backend or NullCacheBackend(),
        )

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

        updated_listing = self._store_listing(replace(listing, status=ListingStatus.CANCELLED, updated_at=utcnow()))
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
                self._store_listing(replace(listing, status=ListingStatus.COMPLETED, updated_at=utcnow()))

        self._reject_pending_offers(
            asset_id=offer.asset_id,
            seller_user_id=offer.seller_user_id,
            exclude_offer_id=offer.offer_id,
        )
        self._fulfill_trade_intents(offer)
        execution: PlayerExecution | None = None
        if offer.cash_amount > 0:
            execution = self.pricing_service.record_execution(
                player_id=offer.asset_id,
                price=float(offer.cash_amount),
                quantity=1.0,
                seller_user_id=offer.seller_user_id,
                buyer_user_id=offer.buyer_user_id,
                occurred_at=accepted_offer.updated_at,
                source="offer.accepted",
            )
        self._after_asset_mutation(
            asset_id=offer.asset_id,
            event_name="market.offer.accepted",
            payload={
                "offer_id": offer.offer_id,
                "asset_id": offer.asset_id,
                "seller_user_id": offer.seller_user_id,
                "buyer_user_id": offer.buyer_user_id,
                "listing_id": offer.listing_id,
                "execution_id": execution.execution_id if execution is not None else None,
            },
            occurred_at=accepted_offer.updated_at,
            execution=execution,
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

    def record_execution(
        self,
        *,
        asset_id: str,
        price: float,
        quantity: float = 1.0,
        seller_user_id: str | None = None,
        buyer_user_id: str | None = None,
        occurred_at: datetime | None = None,
        source: str = "manual",
    ) -> PlayerExecution:
        execution = self.pricing_service.record_execution(
            player_id=asset_id,
            price=price,
            quantity=quantity,
            seller_user_id=seller_user_id,
            buyer_user_id=buyer_user_id,
            occurred_at=occurred_at,
            source=source,
        )
        self._after_asset_mutation(
            asset_id=asset_id,
            event_name="market.execution.recorded",
            payload={
                "execution_id": execution.execution_id,
                "asset_id": asset_id,
                "price": execution.price,
                "quantity": execution.quantity,
                "source": source,
            },
            occurred_at=execution.occurred_at,
            execution=execution,
        )
        return execution

    def get_player_pricing_snapshot(
        self,
        *,
        asset_id: str,
        reference_price: float | None = None,
        symbol: str | None = None,
    ) -> PlayerPricingSnapshot:
        return self.pricing_service.get_snapshot(
            player_id=asset_id,
            listings=self.repository.list_listings_for_asset(asset_id),
            offers=self.repository.list_offers_for_asset(asset_id),
            trade_intents=self.repository.list_trade_intents_for_asset(asset_id),
            reference_price=reference_price,
            symbol=symbol,
        )

    def get_player_candles(
        self,
        *,
        asset_id: str,
        interval: str,
        limit: int,
        reference_price: float | None = None,
        symbol: str | None = None,
    ) -> CandleSeries:
        return self.pricing_service.get_candles(
            player_id=asset_id,
            interval=interval,
            limit=limit,
            listings=self.repository.list_listings_for_asset(asset_id),
            offers=self.repository.list_offers_for_asset(asset_id),
            trade_intents=self.repository.list_trade_intents_for_asset(asset_id),
            reference_price=reference_price,
            symbol=symbol,
        )

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
                self._store_trade_intent(replace(intent, status=TradeIntentStatus.FULFILLED, updated_at=utcnow()))
            if intent.user_id == offer.seller_user_id and intent.direction in {
                TradeIntentDirection.SELL,
                TradeIntentDirection.SWAP,
            }:
                self._store_trade_intent(replace(intent, status=TradeIntentStatus.FULFILLED, updated_at=utcnow()))

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

    def _after_asset_mutation(
        self,
        *,
        asset_id: str,
        event_name: str,
        payload: dict[str, Any],
        occurred_at: datetime | None = None,
        execution: PlayerExecution | None = None,
    ) -> None:
        self._project_asset_summary(asset_id)
        self._project_asset_pricing(
            asset_id=asset_id,
            event_name=event_name,
            occurred_at=occurred_at,
            execution=execution,
        )
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

    def _project_asset_pricing(
        self,
        *,
        asset_id: str,
        event_name: str,
        occurred_at: datetime | None,
        execution: PlayerExecution | None,
    ) -> None:
        self.pricing_service.refresh_player_snapshot(
            player_id=asset_id,
            listings=self.repository.list_listings_for_asset(asset_id),
            offers=self.repository.list_offers_for_asset(asset_id),
            trade_intents=self.repository.list_trade_intents_for_asset(asset_id),
            occurred_at=occurred_at,
            event_name=event_name,
            execution=execution,
        )


@dataclass(frozen=True, slots=True)
class MarketPlayerListItem:
    player_id: str
    player_name: str
    position: str | None
    secondary_positions: list[str]
    nationality: str | None
    nationality_code: str | None
    current_club_id: str | None
    current_club_name: str | None
    current_competition_id: str | None
    current_competition_name: str | None
    current_competition_country_name: str | None
    current_division_id: str | None
    current_division_name: str | None
    age: int | None
    height_cm: int | None
    preferred_foot: str | None
    market_value_eur: float | None
    current_value_credits: float | None
    movement_pct: float | None
    trend_score: float | None
    market_interest_score: int | None
    average_rating: float | None
    global_scouting_index: float | None
    previous_global_scouting_index: float | None
    global_scouting_index_movement_pct: float | None
    transfer_listing_id: str | None
    transfer_listing_status: str | None
    selling_club_id: str | None
    availability_label: str
    asking_type: str
    salary_amount: float | None
    contract_years_remaining: float | None
    buy_clause_amount: float | None
    loan_terms: dict[str, Any]
    swap_terms: dict[str, Any]
    availability: dict[str, Any]
    is_tradable: bool
    image_url: str | None
    avatar: PlayerAvatarView


@dataclass(frozen=True, slots=True)
class MarketPlayerListResult:
    items: tuple[MarketPlayerListItem, ...]
    limit: int
    next_cursor: str | None
    has_more: bool
    total: int
    offset: int = 0


@dataclass(frozen=True, slots=True)
class MarketBrowseOption:
    id: str
    label: str
    count: int
    subtitle: str | None = None
    parent_id: str | None = None
    country_id: str | None = None
    league_id: str | None = None
    division_id: str | None = None


@dataclass(frozen=True, slots=True)
class MarketBrowseCatalog:
    total: int
    countries: tuple[MarketBrowseOption, ...]
    leagues: tuple[MarketBrowseOption, ...]
    divisions: tuple[MarketBrowseOption, ...]
    clubs: tuple[MarketBrowseOption, ...]


@dataclass(frozen=True, slots=True)
class MarketPlayerIdentity:
    player_name: str
    first_name: str | None
    last_name: str | None
    short_name: str | None
    position: str | None
    normalized_position: str | None
    secondary_positions: list[str]
    nationality: str | None
    nationality_code: str | None
    age: int | None
    date_of_birth: date | None
    preferred_foot: str | None
    shirt_number: int | None
    height_cm: int | None
    weight_kg: int | None
    current_club_id: str | None
    current_club_name: str | None
    current_competition_id: str | None
    current_competition_name: str | None
    image_url: str | None
    avatar: PlayerAvatarView


@dataclass(frozen=True, slots=True)
class MarketPlayerMarketProfile:
    is_tradable: bool
    market_value_eur: float | None
    supply_tier: dict[str, Any] | None
    liquidity_band: dict[str, Any] | None
    holder_count: int | None
    top_holder_share_pct: float | None
    top_3_holder_share_pct: float | None
    snapshot_market_price_credits: float | None
    quoted_market_price_credits: float | None
    trusted_trade_price_credits: float | None
    trade_trust_score: float | None


@dataclass(frozen=True, slots=True)
class MarketPlayerValueProfile:
    last_snapshot_id: str | None
    last_snapshot_at: Any | None
    current_value_credits: float | None
    previous_value_credits: float | None
    movement_pct: float | None
    football_truth_value_credits: float | None
    market_signal_value_credits: float | None
    published_card_value_credits: float | None


@dataclass(frozen=True, slots=True)
class MarketPlayerTrendProfile:
    trend_score: float | None
    market_interest_score: int | None
    average_rating: float | None
    global_scouting_index: float | None
    previous_global_scouting_index: float | None
    global_scouting_index_movement_pct: float | None
    drivers: tuple[str, ...]
    active_real_world_flags: tuple[str, ...] = ()
    recommendation_priority_delta: float = 0.0
    market_buzz_score: float = 0.0
    temporary_form_boost: float = 0.0


@dataclass(frozen=True, slots=True)
class MarketPlayerDetail:
    player_id: str
    identity: MarketPlayerIdentity
    market_profile: MarketPlayerMarketProfile
    value: MarketPlayerValueProfile
    trend: MarketPlayerTrendProfile
    attributes: "MarketPlayerAttributes"


@dataclass(frozen=True, slots=True)
class MarketPlayerAttributes:
    overall: int
    potential: int
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int


_ATTRIBUTE_ARCHETYPES: dict[str, dict[str, int]] = {
    "GK": {"pace": 44, "shooting": 18, "passing": 58, "dribbling": 32, "defending": 78, "physical": 72},
    "DF": {"pace": 62, "shooting": 34, "passing": 58, "dribbling": 50, "defending": 75, "physical": 76},
    "MF": {"pace": 66, "shooting": 58, "passing": 75, "dribbling": 72, "defending": 60, "physical": 68},
    "FW": {"pace": 76, "shooting": 75, "passing": 62, "dribbling": 74, "defending": 35, "physical": 68},
}

_ATTRIBUTE_KEYS: tuple[str, ...] = ("pace", "shooting", "passing", "dribbling", "defending", "physical")


def _attribute_bucket(position: str | None) -> str:
    text = (position or "").strip().lower()
    if not text:
        return "MF"
    if "goal" in text or text in {"gk", "g"}:
        return "GK"
    if any(token in text for token in ("back", "def", "cb", "rb", "lb", "wb")):
        return "DF"
    if any(token in text for token in ("forward", "strik", "wing", "att", "cf", "st", "fw")):
        return "FW"
    return "MF"


def derive_player_attributes(player: Player, overall: int | None) -> MarketPlayerAttributes:
    """Derive the 6 FIFA-style stats from GSI + position archetype, preferring any
    values stored in dna_profile. Mirrors services/player-ingestion footballAttributes."""
    base_overall = int(max(1, min(99, overall if overall and overall > 0 else 60)))
    archetype = _ATTRIBUTE_ARCHETYPES[_attribute_bucket(player.normalized_position or player.position)]
    dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
    archetype_mean = sum(archetype.values()) / len(archetype)
    shift = round((base_overall - archetype_mean) * 0.6)

    def _stat(name: str) -> int:
        stored = dna.get(name)
        if isinstance(stored, (int, float)) and stored > 0:
            value = float(stored)
            if value <= 1:
                value *= 100
            return int(max(1, min(99, round(value))))
        return int(max(1, min(99, archetype[name] + shift)))

    stored_potential = dna.get("potential")
    if isinstance(stored_potential, (int, float)) and stored_potential > 0:
        potential = int(max(base_overall, min(99, round(float(stored_potential)))))
    else:
        potential = int(min(99, base_overall + 6))

    return MarketPlayerAttributes(
        overall=base_overall,
        potential=potential,
        **{name: _stat(name) for name in _ATTRIBUTE_KEYS},
    )


@dataclass(frozen=True, slots=True)
class MarketPlayerHistoryPoint:
    snapshot_id: str
    as_of: Any
    current_value_credits: float
    previous_value_credits: float
    movement_pct: float
    football_truth_value_credits: float
    market_signal_value_credits: float
    published_card_value_credits: float | None
    trend_score: float | None
    global_scouting_index: float | None
    previous_global_scouting_index: float | None
    global_scouting_index_movement_pct: float | None
    drivers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MarketPlayerHistory:
    player_id: str
    history: tuple[MarketPlayerHistoryPoint, ...]


@dataclass(slots=True)
class MarketPlayerQueryService:
    session: Session
    repository: SqlAlchemyMarketPlayerRepository | None = None
    market_engine: MarketEngine | None = None
    today: date | None = None
    avatar_service: AvatarService | None = None
    runtime_controls: RuntimeControlService | None = None
    _real_world_impact_cache: dict[str, PlayerRealWorldImpact] = field(init=False, default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = SqlAlchemyMarketPlayerRepository(self.session)
        if self.market_engine is None:
            self.market_engine = MarketEngine()
        if self.today is None:
            self.today = date.today()
        if self.avatar_service is None:
            self.avatar_service = AvatarService()

    def list_players(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        offset: int | None = 0,
        position: str | None = None,
        country: str | None = None,
        nationality: str | None = None,
        national_team: str | None = None,
        club: str | None = None,
        league: str | None = None,
        division: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        availability: str | None = None,
        search: str | None = None,
        sort: str = "current_value",
    ) -> MarketPlayerListResult:
        normalized_position = self._normalize_optional_text(position)
        normalized_country = self._normalize_optional_text(country)
        normalized_nationality = self._normalize_optional_text(nationality)
        normalized_national_team = self._normalize_optional_text(national_team)
        normalized_club = self._normalize_optional_text(club)
        normalized_league = self._normalize_optional_text(league)
        normalized_division = self._normalize_optional_text(division)
        normalized_availability = self._normalize_optional_text(availability)
        normalized_search = self._normalize_optional_text(search)
        normalized_offset = 0 if offset is None else offset
        self._validate_player_query(
            limit=limit,
            offset=normalized_offset,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            sort=sort,
        )

        records = self.repository.list_player_records()
        open_listings_by_player_id = self._open_transfer_listings_by_player_id(records)
        filtered_records = [
            record
            for record in records
            if self._matches_position(record, normalized_position)
            and self._matches_market_country(record, normalized_country)
            and self._matches_nationality(record, normalized_nationality)
            and self._matches_national_team(record, normalized_national_team)
            and self._matches_club(record, normalized_club)
            and self._matches_league(record, normalized_league)
            and self._matches_division(record, normalized_division)
            and self._matches_age(record, min_age=min_age, max_age=max_age)
            and self._matches_value(record, min_value=min_value, max_value=max_value)
            and self._matches_availability(
                record,
                normalized_availability,
                open_listings_by_player_id.get(record.player.id),
            )
            and self._matches_search(record, normalized_search)
        ]
        sorted_records = self._sort_player_records(filtered_records, sort=sort)
        total = len(sorted_records)
        query_signature = self._player_query_signature(
            sort=sort,
            position=normalized_position,
            country=normalized_country,
            nationality=normalized_nationality,
            national_team=normalized_national_team,
            club=normalized_club,
            league=normalized_league,
            division=normalized_division,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=normalized_availability,
            search=normalized_search,
        )
        start_index = (
            self._cursor_start_index(
                sorted_records,
                cursor=cursor,
                sort=sort,
                query_signature=query_signature,
            )
            if cursor
            else normalized_offset
        )
        paginated_records = sorted_records[start_index : start_index + limit + 1]
        page_records = paginated_records[:limit]
        has_more = len(paginated_records) > limit
        next_cursor = (
            self._encode_player_cursor(
                page_records[-1],
                sort=sort,
                query_signature=query_signature,
            )
            if has_more and page_records
            else None
        )
        return MarketPlayerListResult(
            items=tuple(
                self._build_list_item(
                    record,
                    open_listing=open_listings_by_player_id.get(record.player.id),
                )
                for record in page_records
            ),
            limit=limit,
            next_cursor=next_cursor,
            has_more=has_more,
            total=total,
            offset=start_index,
        )

    def browse_catalog(self) -> MarketBrowseCatalog:
        records = self.repository.list_player_records()
        countries: dict[str, dict[str, Any]] = {}
        leagues: dict[str, dict[str, Any]] = {}
        divisions: dict[str, dict[str, Any]] = {}
        clubs: dict[str, dict[str, Any]] = {}

        for record in records:
            country = self._catalog_country(record)
            country_id = self._country_id(country) or self._catalog_country_id(record)
            country_label = country.name if country is not None else None
            self._bump_catalog_option(
                countries,
                option_id=country_id,
                label=country_label,
                country_id=country_id,
            )

            league_id = self._catalog_league_id(record)
            league_label = self._catalog_league_label(record)
            self._bump_catalog_option(
                leagues,
                option_id=league_id,
                label=league_label,
                subtitle=country_label,
                parent_id=country_id,
                country_id=country_id,
                league_id=league_id,
            )

            division_id = self._current_division_id(record)
            division_label = self._current_division_name(record)
            self._bump_catalog_option(
                divisions,
                option_id=division_id,
                label=division_label,
                subtitle=league_label,
                parent_id=league_id,
                country_id=country_id,
                league_id=league_id,
                division_id=division_id,
            )

            club_id = self._catalog_club_id(record)
            club_label = self._catalog_club_label(record)
            self._bump_catalog_option(
                clubs,
                option_id=club_id,
                label=club_label,
                subtitle=league_label or country_label,
                parent_id=division_id or league_id,
                country_id=country_id,
                league_id=league_id,
                division_id=division_id,
            )

        return MarketBrowseCatalog(
            total=len(records),
            countries=self._catalog_options(countries),
            leagues=self._catalog_options(leagues),
            divisions=self._catalog_options(divisions),
            clubs=self._catalog_options(clubs),
        )

    def get_player_detail(self, player_id: str) -> MarketPlayerDetail:
        record = self.repository.get_player_record(player_id)
        if record is None:
            raise MarketNotFoundError(f"player {player_id} was not found")

        player = record.player
        breakdown_payload = self._breakdown_payload(record)
        real_world_impact = self._real_world_impact(player.id)

        return MarketPlayerDetail(
            player_id=player.id,
            identity=MarketPlayerIdentity(
                player_name=player.full_name,
                first_name=player.first_name,
                last_name=player.last_name,
                short_name=player.short_name,
                position=player.position,
                normalized_position=player.normalized_position,
                secondary_positions=list(player.secondary_positions_json or []),
                nationality=player.country.name if player.country is not None else None,
                nationality_code=self._nationality_code(record),
                age=self._player_age(player.date_of_birth),
                date_of_birth=player.date_of_birth,
                preferred_foot=player.preferred_foot,
                shirt_number=player.shirt_number,
                height_cm=player.height_cm,
                weight_kg=player.weight_kg,
                current_club_id=self._catalog_club_id(record),
                current_club_name=self._catalog_club_label(record),
                current_competition_id=self._catalog_league_id(record),
                current_competition_name=self._catalog_league_label(record),
                image_url=self._image_url(record),
                avatar=self._avatar(record),
            ),
            market_profile=MarketPlayerMarketProfile(
                is_tradable=is_transfer_market_eligible(player),
                market_value_eur=player.current_market_reference_value or player.market_value_eur,
                supply_tier=self._supply_tier_payload(record),
                liquidity_band=self._liquidity_band_payload(record),
                holder_count=self._coerce_int(breakdown_payload.get("holder_count")),
                top_holder_share_pct=self._coerce_float(breakdown_payload.get("top_holder_share_pct")),
                top_3_holder_share_pct=self._coerce_float(breakdown_payload.get("top_3_holder_share_pct")),
                snapshot_market_price_credits=round_gtex_display_value(
                    self._coerce_float(breakdown_payload.get("snapshot_market_price_credits"))
                ),
                quoted_market_price_credits=round_gtex_display_value(
                    self._coerce_float(breakdown_payload.get("quoted_market_price_credits"))
                ),
                trusted_trade_price_credits=round_gtex_display_value(
                    self._coerce_float(breakdown_payload.get("trusted_trade_price_credits"))
                ),
                trade_trust_score=self._coerce_float(breakdown_payload.get("trade_trust_score")),
            ),
            value=MarketPlayerValueProfile(
                last_snapshot_id=self._last_snapshot_id(record),
                last_snapshot_at=self._last_snapshot_at(record),
                current_value_credits=self._current_value_credits(record),
                previous_value_credits=self._previous_value_credits(record),
                movement_pct=self._movement_pct(record),
                football_truth_value_credits=self._football_truth_value_credits(record),
                market_signal_value_credits=self._market_signal_value_credits(record),
                published_card_value_credits=self._published_card_value_credits(record),
            ),
            trend=MarketPlayerTrendProfile(
                trend_score=self._trend_score(record),
                market_interest_score=(record.summary.market_interest_score if record.summary is not None else None),
                average_rating=(record.summary.average_rating if record.summary is not None else None),
                global_scouting_index=self._global_scouting_index(record),
                previous_global_scouting_index=self._previous_global_scouting_index(record),
                global_scouting_index_movement_pct=self._global_scouting_index_movement_pct(record),
                drivers=self._drivers(record),
                active_real_world_flags=real_world_impact.active_flag_codes,
                recommendation_priority_delta=real_world_impact.recommendation_priority_delta,
                market_buzz_score=real_world_impact.market_buzz_score,
                temporary_form_boost=real_world_impact.gameplay_effect_total,
            ),
            attributes=derive_player_attributes(
                player,
                self._coerce_int(self._global_scouting_index(record)),
            ),
        )

    def get_player_history(self, player_id: str) -> MarketPlayerHistory:
        if not self.repository.player_exists(player_id):
            raise MarketNotFoundError(f"player {player_id} was not found")

        history = tuple(
            self._build_history_point(snapshot) for snapshot in self.repository.list_player_history(player_id)
        )
        return MarketPlayerHistory(player_id=player_id, history=history)

    def get_player_ticker(self, player_id: str) -> PlayerPricingSnapshot:
        record = self.repository.get_player_record(player_id)
        if record is None:
            raise MarketNotFoundError(f"player {player_id} was not found")

        return self.market_engine.get_player_pricing_snapshot(
            asset_id=player_id,
            reference_price=self._require_reference_price(record),
            symbol=self._pricing_symbol(record),
        )

    def get_player_candles(self, player_id: str, *, interval: str = "1h", limit: int = 30) -> CandleSeries:
        record = self.repository.get_player_record(player_id)
        if record is None:
            raise MarketNotFoundError(f"player {player_id} was not found")

        try:
            return self.market_engine.get_player_candles(
                asset_id=player_id,
                interval=interval,
                limit=limit,
                reference_price=self._require_reference_price(record),
                symbol=self._pricing_symbol(record),
            )
        except PricingValidationError as exc:
            raise MarketValidationError(str(exc)) from exc

    def get_market_movers(self, *, limit: int = 5) -> MarketMovers:
        if limit < 1:
            raise MarketValidationError("limit must be at least 1")

        mover_items: list[MarketMoverItem] = []
        for record in self.repository.list_player_records():
            reference_price = self._reference_price(record)
            if reference_price is None and record.player.is_real_player:
                continue
            snapshot = self.market_engine.get_player_pricing_snapshot(
                asset_id=record.player.id,
                reference_price=reference_price,
                symbol=self._pricing_symbol(record),
            )
            mover_items.append(
                MarketMoverItem(
                    player_id=record.player.id,
                    player_name=record.player.full_name,
                    symbol=snapshot.symbol,
                    last_price=snapshot.last_price,
                    day_change=snapshot.day_change,
                    day_change_percent=snapshot.day_change_percent,
                    volume_24h=snapshot.volume_24h,
                    trend_score=self._trending_rank(record, snapshot),
                )
            )

        top_gainers = tuple(
            sorted(
                mover_items,
                key=lambda item: (item.day_change_percent, item.volume_24h, item.player_name),
                reverse=True,
            )[:limit]
        )
        top_losers = tuple(
            sorted(
                mover_items,
                key=lambda item: (item.day_change_percent, -item.volume_24h, item.player_name),
            )[:limit]
        )
        most_traded = tuple(
            sorted(
                mover_items,
                key=lambda item: (item.volume_24h, abs(item.day_change_percent), item.player_name),
                reverse=True,
            )[:limit]
        )
        trending = tuple(
            sorted(
                mover_items,
                key=lambda item: (
                    (item.trend_score or 0.0),
                    item.volume_24h,
                    abs(item.day_change_percent),
                    item.player_name,
                ),
                reverse=True,
            )[:limit]
        )
        return MarketMovers(
            top_gainers=top_gainers,
            top_losers=top_losers,
            most_traded=most_traded,
            trending=trending,
        )

    def list_leagues(self) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for record in self.repository.list_player_records():
            league_id = record.player.current_competition_id or record.player.internal_league_id
            if not league_id:
                continue
            competition = record.player.current_competition
            internal_league = record.player.internal_league
            name = (
                competition.name
                if competition is not None
                else (
                    internal_league.name
                    if internal_league is not None
                    else record.player.real_world_league_name or "Unknown league"
                )
            )
            item = grouped.setdefault(
                league_id,
                {
                    "league_id": league_id,
                    "slug": self._slug(name),
                    "display_name": name,
                    "country": competition.country.name if competition is not None and competition.country else None,
                    "country_code": (
                        self._country_code(competition.country)
                        if competition is not None and competition.country is not None
                        else None
                    ),
                    "crest_url": None,
                    "player_count": 0,
                    "club_count": 0,
                    "_clubs": set(),
                },
            )
            item["player_count"] += 1
            if record.player.current_club_id:
                item["_clubs"].add(record.player.current_club_id)
        return [
            self._finalize_count_item(item) for item in sorted(grouped.values(), key=lambda row: row["display_name"])
        ]

    def list_league_clubs(self, league_id: str) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for record in self.repository.list_player_records():
            player_league_id = record.player.current_competition_id or record.player.internal_league_id
            if player_league_id != league_id or record.player.current_club is None:
                continue
            club = record.player.current_club
            item = grouped.setdefault(
                club.id,
                {
                    "club_id": club.id,
                    "slug": club.slug,
                    "display_name": club.name,
                    "short_name": club.short_name,
                    "crest_url": club.crest_url,
                    "country": club.country.name if club.country is not None else None,
                    "country_code": self._country_code(club.country),
                    "player_count": 0,
                },
            )
            item["player_count"] += 1
        return list(sorted(grouped.values(), key=lambda row: row["display_name"]))

    def list_club_players(self, club_id: str, *, limit: int = 100) -> MarketPlayerListResult:
        records = [
            record for record in self.repository.list_player_records() if record.player.current_club_id == club_id
        ]
        sorted_records = self._sort_player_records(records, sort="current_value")[:limit]
        return MarketPlayerListResult(
            items=tuple(self._build_list_item(record) for record in sorted_records),
            limit=limit,
            next_cursor=None,
            has_more=len(records) > limit,
            total=len(records),
            offset=0,
        )

    def list_nationalities(self) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for record in self.repository.list_player_records():
            country = record.player.country
            code = self._country_code(country) or self._nationality_code(record)
            if not code:
                continue
            display_name = country.name if country is not None else code
            item = grouped.setdefault(
                code,
                {
                    "country_code": code,
                    "slug": self._slug(display_name),
                    "display_name": display_name,
                    "flag_url": None,
                    "eligible_player_count": 0,
                },
            )
            item["eligible_player_count"] += 1
        return list(sorted(grouped.values(), key=lambda row: row["display_name"]))

    def list_nationality_players(self, country_code: str, *, limit: int = 100) -> MarketPlayerListResult:
        normalized_code = self._normalize_text(country_code)
        records = [
            record
            for record in self.repository.list_player_records()
            if self._normalize_text(self._nationality_code(record)) == normalized_code
            or self._normalize_text(record.player.country.name if record.player.country else None) == normalized_code
        ]
        sorted_records = self._sort_player_records(records, sort="current_value")[:limit]
        return MarketPlayerListResult(
            items=tuple(self._build_list_item(record) for record in sorted_records),
            limit=limit,
            next_cursor=None,
            has_more=len(records) > limit,
            total=len(records),
            offset=0,
        )

    def list_national_teams(self) -> list[dict[str, Any]]:
        return [
            {
                "team_id": item["country_code"],
                "country_code": item["country_code"],
                "slug": item["slug"],
                "display_name": f"{item['display_name']} National Team",
                "flag_url": item["flag_url"],
                "eligible_player_count": item["eligible_player_count"],
            }
            for item in self.list_nationalities()
        ]

    def _catalog_country_id(self, record: MarketPlayerRecord) -> str | None:
        return self._nationality_code(record) or (
            record.player.country.id if record.player.country is not None else None
        )

    def _catalog_country(self, record: MarketPlayerRecord) -> Any | None:
        competition = record.player.current_competition
        if competition is not None and competition.country is not None:
            return competition.country
        club = record.player.current_club
        if club is not None and club.country is not None:
            return club.country
        return record.player.country

    def _catalog_league_id(self, record: MarketPlayerRecord) -> str | None:
        competition = record.player.current_competition
        if competition is not None:
            return competition.id
        if record.summary is not None and record.summary.current_competition_id:
            return record.summary.current_competition_id
        league_name = (record.player.real_world_league_name or "").strip()
        return self._slug(league_name) if league_name else None

    def _catalog_league_label(self, record: MarketPlayerRecord) -> str | None:
        competition = record.player.current_competition
        if competition is not None:
            return competition.name
        if record.summary is not None and record.summary.current_competition_name:
            return record.summary.current_competition_name
        league_name = (record.player.real_world_league_name or "").strip()
        return league_name or None

    def _catalog_club_id(self, record: MarketPlayerRecord) -> str | None:
        club = record.player.current_club
        if club is not None:
            return club.id
        if record.summary is not None and record.summary.current_club_id:
            return record.summary.current_club_id
        club_name = (record.player.real_world_club_name or "").strip()
        return self._slug(club_name) if club_name else None

    def _catalog_club_label(self, record: MarketPlayerRecord) -> str | None:
        club = record.player.current_club
        if club is not None:
            return club.name
        if record.summary is not None and record.summary.current_club_name:
            return record.summary.current_club_name
        club_name = (record.player.real_world_club_name or "").strip()
        return club_name or None

    def _current_division_id(self, record: MarketPlayerRecord) -> str | None:
        competition = record.player.current_competition
        if competition is not None and competition.domestic_level is not None:
            return f"division-{competition.domestic_level}"
        internal_league = record.player.internal_league or (
            competition.internal_league if competition is not None else None
        )
        if internal_league is not None:
            return internal_league.id
        return None

    def _current_division_name(self, record: MarketPlayerRecord) -> str | None:
        competition = record.player.current_competition
        if competition is not None and competition.domestic_level is not None:
            return f"Division {competition.domestic_level}"
        internal_league = record.player.internal_league or (
            competition.internal_league if competition is not None else None
        )
        if internal_league is not None:
            return internal_league.name
        return None

    def _current_competition_country_name(self, record: MarketPlayerRecord) -> str | None:
        competition = record.player.current_competition
        if competition is not None and competition.country is not None:
            return competition.country.name
        return None

    def _bump_catalog_option(
        self,
        groups: dict[str, dict[str, Any]],
        *,
        option_id: str | None,
        label: str | None,
        subtitle: str | None = None,
        parent_id: str | None = None,
        country_id: str | None = None,
        league_id: str | None = None,
        division_id: str | None = None,
    ) -> None:
        normalized_id = (option_id or "").strip()
        normalized_label = (label or "").strip()
        if not normalized_id or not normalized_label:
            return
        current = groups.get(normalized_id)
        if current is None:
            groups[normalized_id] = {
                "id": normalized_id,
                "label": normalized_label,
                "count": 1,
                "subtitle": subtitle.strip() if isinstance(subtitle, str) and subtitle.strip() else None,
                "parent_id": parent_id.strip() if isinstance(parent_id, str) and parent_id.strip() else None,
                "country_id": country_id.strip() if isinstance(country_id, str) and country_id.strip() else None,
                "league_id": league_id.strip() if isinstance(league_id, str) and league_id.strip() else None,
                "division_id": division_id.strip() if isinstance(division_id, str) and division_id.strip() else None,
            }
            return
        current["count"] = int(current["count"]) + 1

    def _catalog_options(self, groups: dict[str, dict[str, Any]]) -> tuple[MarketBrowseOption, ...]:
        sorted_options = sorted(
            groups.values(),
            key=lambda value: (-int(value["count"]), str(value["label"]).lower(), str(value["id"])),
        )
        return tuple(MarketBrowseOption(**option) for option in sorted_options)

    def _build_list_item(
        self,
        record: MarketPlayerRecord,
        *,
        open_listing: TransferListing | None = None,
    ) -> MarketPlayerListItem:
        return MarketPlayerListItem(
            player_id=record.player.id,
            player_name=record.player.full_name,
            position=record.player.normalized_position or record.player.position,
            secondary_positions=list(record.player.secondary_positions_json or []),
            nationality=record.player.country.name if record.player.country is not None else None,
            nationality_code=self._nationality_code(record),
            current_club_id=self._catalog_club_id(record),
            current_club_name=self._catalog_club_label(record),
            current_competition_id=self._catalog_league_id(record),
            current_competition_name=self._catalog_league_label(record),
            current_competition_country_name=self._current_competition_country_name(record),
            current_division_id=self._current_division_id(record),
            current_division_name=self._current_division_name(record),
            age=self._player_age(record.player.date_of_birth),
            height_cm=record.player.height_cm,
            preferred_foot=record.player.preferred_foot,
            market_value_eur=self._real_world_market_value_eur(record),
            current_value_credits=self._current_value_credits(record),
            movement_pct=self._movement_pct(record),
            trend_score=self._trend_score(record),
            market_interest_score=(record.summary.market_interest_score if record.summary is not None else None),
            average_rating=record.summary.average_rating if record.summary is not None else None,
            global_scouting_index=self._global_scouting_index(record),
            previous_global_scouting_index=self._previous_global_scouting_index(record),
            global_scouting_index_movement_pct=self._global_scouting_index_movement_pct(record),
            transfer_listing_id=open_listing.id if open_listing is not None else None,
            transfer_listing_status=open_listing.status if open_listing is not None else None,
            selling_club_id=open_listing.selling_club_id if open_listing is not None else None,
            availability_label=self._availability_label(record, open_listing),
            asking_type=self._asking_type(record, open_listing),
            salary_amount=self._decimal_float(open_listing.salary_amount if open_listing is not None else None),
            contract_years_remaining=self._decimal_float(
                open_listing.contract_years_remaining if open_listing is not None else None
            ),
            buy_clause_amount=self._decimal_float(open_listing.buy_clause_amount if open_listing is not None else None),
            loan_terms=self._json_object(open_listing.loan_terms_json if open_listing is not None else None),
            swap_terms=self._json_object(open_listing.swap_terms_json if open_listing is not None else None),
            availability=self._json_object(open_listing.availability_json if open_listing is not None else None),
            is_tradable=record.player.is_tradable,
            image_url=self._image_url(record),
            avatar=self._avatar(record),
        )

    def _open_transfer_listings_by_player_id(
        self,
        records: list[MarketPlayerRecord],
    ) -> dict[str, TransferListing]:
        player_ids = [record.player.id for record in records if record.player.id]
        if not player_ids:
            return {}
        listings = self.session.scalars(
            select(TransferListing)
            .where(
                TransferListing.player_id.in_(player_ids),
                TransferListing.status.in_(("open", "countered", "negotiated")),
            )
            .order_by(TransferListing.created_at.desc())
        ).all()
        by_player_id: dict[str, TransferListing] = {}
        for listing in listings:
            by_player_id.setdefault(listing.player_id, listing)
        return by_player_id

    def _matches_availability(
        self,
        record: MarketPlayerRecord,
        availability: str | None,
        open_listing: TransferListing | None,
    ) -> bool:
        if availability is None:
            return True
        if availability == "free_agent":
            club_name = self._normalize_text(self._catalog_club_label(record))
            return club_name in {"free agent", "unattached"}
        if open_listing is None:
            return False
        asking_type = self._asking_type(record, open_listing)
        return asking_type == availability

    def _asking_type(self, record: MarketPlayerRecord, open_listing: TransferListing | None) -> str:
        if open_listing is not None:
            return open_listing.listing_type or "transfer"
        return "transfer_eligible" if record.player.is_tradable else "unavailable"

    def _availability_label(self, record: MarketPlayerRecord, open_listing: TransferListing | None) -> str:
        if open_listing is not None:
            return self._label_from_token(open_listing.listing_type or "transfer")
        if record.player.is_tradable:
            return "Transfer eligible"
        return "Not tradable"

    def _label_from_token(self, value: str) -> str:
        normalized = value.replace("_", " ").strip()
        if not normalized:
            return "Pending"
        return " ".join(word.capitalize() for word in normalized.split())

    def _decimal_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _json_object(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _build_history_point(self, snapshot: Any) -> MarketPlayerHistoryPoint:
        breakdown_payload = snapshot.breakdown_json if isinstance(snapshot.breakdown_json, dict) else {}
        global_scouting_index = self._coerce_float(breakdown_payload.get("global_scouting_index"))
        return MarketPlayerHistoryPoint(
            snapshot_id=snapshot.id,
            as_of=snapshot.as_of,
            current_value_credits=round_gtex_display_value(snapshot.target_credits) or snapshot.target_credits,
            previous_value_credits=round_gtex_display_value(snapshot.previous_credits) or snapshot.previous_credits,
            movement_pct=snapshot.movement_pct,
            football_truth_value_credits=(
                round_gtex_display_value(snapshot.football_truth_value_credits) or snapshot.football_truth_value_credits
            ),
            market_signal_value_credits=(
                round_gtex_display_value(snapshot.market_signal_value_credits) or snapshot.market_signal_value_credits
            ),
            published_card_value_credits=round_gtex_display_value(
                self._coerce_float(breakdown_payload.get("published_card_value_credits"))
            )
            or snapshot.target_credits,
            trend_score=global_scouting_index,
            global_scouting_index=global_scouting_index,
            previous_global_scouting_index=self._coerce_float(breakdown_payload.get("previous_global_scouting_index")),
            global_scouting_index_movement_pct=self._coerce_float(
                breakdown_payload.get("global_scouting_index_movement_pct")
            ),
            drivers=self._string_tuple(snapshot.drivers_json),
        )

    def _validate_player_query(
        self,
        *,
        limit: int,
        offset: int,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        sort: str,
    ) -> None:
        if limit < 1:
            raise MarketValidationError("limit must be at least 1")
        if offset < 0:
            raise MarketValidationError("offset cannot be negative")
        if min_age is not None and min_age < 0:
            raise MarketValidationError("min_age cannot be negative")
        if max_age is not None and max_age < 0:
            raise MarketValidationError("max_age cannot be negative")
        if min_age is not None and max_age is not None and min_age > max_age:
            raise MarketValidationError("min_age cannot exceed max_age")
        if min_value is not None and min_value < 0:
            raise MarketValidationError("min_value cannot be negative")
        if max_value is not None and max_value < 0:
            raise MarketValidationError("max_value cannot be negative")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise MarketValidationError("min_value cannot exceed max_value")
        if sort not in PLAYER_DISCOVERY_SORTS:
            raise MarketValidationError("sort must be one of: age, current_value, name, trend_score")

    def _matches_position(self, record: MarketPlayerRecord, position: str | None) -> bool:
        if position is None:
            return True
        candidate = record.player.normalized_position or record.player.position
        return self._normalize_text(candidate) == position

    def _matches_market_country(self, record: MarketPlayerRecord, country: str | None) -> bool:
        if country is None:
            return True
        market_country = self._catalog_country(record)
        if market_country is None:
            return False
        candidates = {
            self._normalize_text(self._country_id(market_country)),
            self._normalize_text(market_country.id),
            self._normalize_text(market_country.name),
            self._normalize_text(getattr(market_country, "alpha2_code", None)),
            self._normalize_text(getattr(market_country, "alpha3_code", None)),
            self._normalize_text(getattr(market_country, "fifa_code", None)),
        }
        return country in candidates

    def _matches_nationality(self, record: MarketPlayerRecord, nationality: str | None) -> bool:
        if nationality is None:
            return True
        if record.player.country is None:
            return False
        candidates = {
            self._normalize_text(record.player.country.id),
            self._normalize_text(record.player.country.name),
            self._normalize_text(record.player.country.alpha2_code),
            self._normalize_text(record.player.country.alpha3_code),
            self._normalize_text(record.player.country.fifa_code),
        }
        return nationality in candidates

    def _matches_national_team(self, record: MarketPlayerRecord, national_team: str | None) -> bool:
        if national_team is None:
            return True
        payload = self._national_team_payload(record)
        candidates = self._national_team_candidates(record)
        if not candidates:
            return False
        if national_team in candidates:
            return True
        name = self._normalize_text(payload.get("name"))
        code = self._normalize_text(payload.get("code"))
        return bool((name and national_team.startswith(f"{name} ")) or (code and national_team.startswith(f"{code} ")))

    def _matches_club(self, record: MarketPlayerRecord, club: str | None) -> bool:
        if club is None:
            return True
        if record.player.current_club is None:
            candidates = {
                self._normalize_text(self._catalog_club_id(record)),
                self._normalize_text(self._catalog_club_label(record)),
                self._normalize_text(record.player.real_world_club_name),
            }
            return club in candidates
        candidates = {
            self._normalize_text(record.player.current_club.id),
            self._normalize_text(record.player.current_club.name),
            self._normalize_text(record.player.current_club.short_name),
            self._normalize_text(record.player.current_club.code),
            self._normalize_text(record.player.current_club.slug),
            self._normalize_text(record.summary.current_club_id if record.summary is not None else None),
            self._normalize_text(record.summary.current_club_name if record.summary is not None else None),
            self._normalize_text(record.player.real_world_club_name),
        }
        return club in candidates

    def _matches_league(self, record: MarketPlayerRecord, league: str | None) -> bool:
        if league is None:
            return True
        if record.player.current_competition is None:
            candidates = {
                self._normalize_text(self._catalog_league_id(record)),
                self._normalize_text(self._catalog_league_label(record)),
                self._normalize_text(record.player.real_world_league_name),
            }
            return league in candidates
        competition = record.player.current_competition
        candidates = {
            self._normalize_text(competition.id),
            self._normalize_text(competition.name),
            self._normalize_text(getattr(competition, "short_name", None)),
            self._normalize_text(getattr(competition, "code", None)),
            self._normalize_text(getattr(competition, "slug", None)),
            self._normalize_text(record.summary.current_competition_id if record.summary is not None else None),
            self._normalize_text(record.summary.current_competition_name if record.summary is not None else None),
            self._normalize_text(record.player.real_world_league_name),
        }
        return league in candidates

    def _matches_division(self, record: MarketPlayerRecord, division: str | None) -> bool:
        if division is None:
            return True
        candidates = {
            self._normalize_text(self._current_division_id(record)),
            self._normalize_text(self._current_division_name(record)),
        }
        internal_league = record.player.internal_league
        if internal_league is not None:
            candidates.update(
                {
                    self._normalize_text(internal_league.id),
                    self._normalize_text(internal_league.code),
                    self._normalize_text(internal_league.name),
                }
            )
        competition = record.player.current_competition
        if competition is not None and competition.internal_league is not None:
            candidates.update(
                {
                    self._normalize_text(competition.internal_league.id),
                    self._normalize_text(competition.internal_league.code),
                    self._normalize_text(competition.internal_league.name),
                }
            )
        if competition is not None and competition.domestic_level is not None:
            level = str(competition.domestic_level)
            candidates.update({level, f"division {level}", f"level {level}"})
        return division in candidates

    def _matches_age(
        self,
        record: MarketPlayerRecord,
        *,
        min_age: int | None,
        max_age: int | None,
    ) -> bool:
        if min_age is None and max_age is None:
            return True
        age = self._player_age(record.player.date_of_birth)
        if age is None:
            return False
        if min_age is not None and age < min_age:
            return False
        if max_age is not None and age > max_age:
            return False
        return True

    def _matches_value(
        self,
        record: MarketPlayerRecord,
        *,
        min_value: float | None,
        max_value: float | None,
    ) -> bool:
        if min_value is None and max_value is None:
            return True
        current_value = self._current_value_credits(record)
        if current_value is None:
            return False
        if min_value is not None and current_value < min_value:
            return False
        if max_value is not None and current_value > max_value:
            return False
        return True

    def _matches_search(self, record: MarketPlayerRecord, search: str | None) -> bool:
        if search is None:
            return True
        haystacks = [
            record.player.full_name,
            record.player.first_name,
            record.player.last_name,
            record.player.short_name,
            record.player.current_club.name if record.player.current_club is not None else None,
            (record.player.current_competition.name if record.player.current_competition is not None else None),
            self._catalog_club_label(record),
            self._catalog_league_label(record),
            record.player.country.name if record.player.country is not None else None,
            *self._national_team_search_terms(record),
        ]
        return any(search in self._normalize_text(candidate) for candidate in haystacks)

    def _sort_player_records(
        self,
        records: list[MarketPlayerRecord],
        *,
        sort: str,
    ) -> list[MarketPlayerRecord]:
        return sorted(records, key=lambda record: self._player_sort_key(record, sort=sort))

    def _player_query_signature(
        self,
        *,
        sort: str,
        position: str | None,
        country: str | None,
        nationality: str | None,
        national_team: str | None,
        club: str | None,
        league: str | None,
        division: str | None,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        availability: str | None,
        search: str | None,
    ) -> dict[str, Any]:
        return {
            "sort": sort,
            "position": position,
            "country": country,
            "nationality": nationality,
            "national_team": national_team,
            "club": club,
            "league": league,
            "division": division,
            "min_age": min_age,
            "max_age": max_age,
            "min_value": min_value,
            "max_value": max_value,
            "availability": availability,
            "search": search,
        }

    def _player_sort_key(
        self,
        record: MarketPlayerRecord,
        *,
        sort: str,
    ) -> tuple[Any, ...]:
        normalized_name = self._normalize_text(record.player.full_name)
        if sort == "current_value":
            current_value = self._current_value_credits(record)
            return (
                current_value is None,
                -(current_value or 0.0),
                normalized_name,
                record.player.id,
            )
        if sort == "trend_score":
            trend_score = self._trend_score(record)
            current_value = self._current_value_credits(record)
            return (
                trend_score is None,
                -(trend_score or 0.0),
                -(current_value or 0.0),
                normalized_name,
                record.player.id,
            )
        if sort == "age":
            player_age = self._player_age(record.player.date_of_birth)
            return (
                player_age is None,
                player_age or 10_000,
                normalized_name,
                record.player.id,
            )
        return (
            normalized_name,
            record.player.id,
        )

    def _encode_player_cursor(
        self,
        record: MarketPlayerRecord,
        *,
        sort: str,
        query_signature: dict[str, Any],
    ) -> str:
        payload = {
            "v": 1,
            "query": query_signature,
            "key": list(self._player_sort_key(record, sort=sort)),
        }
        raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")

    def _decode_player_cursor(
        self,
        cursor: str,
        *,
        query_signature: dict[str, Any],
    ) -> tuple[Any, ...]:
        try:
            raw_cursor = cursor.strip()
            if not raw_cursor:
                raise ValueError("empty cursor")
            padding = "=" * (-len(raw_cursor) % 4)
            payload = json.loads(base64.urlsafe_b64decode(f"{raw_cursor}{padding}".encode("ascii")).decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise MarketValidationError("cursor is invalid") from exc

        if not isinstance(payload, dict) or payload.get("v") != 1:
            raise MarketValidationError("cursor is invalid")
        if payload.get("query") != query_signature:
            raise MarketValidationError("cursor does not match the current player query")

        cursor_key = payload.get("key")
        if not isinstance(cursor_key, list) or not cursor_key:
            raise MarketValidationError("cursor is invalid")
        return tuple(cursor_key)

    def _cursor_start_index(
        self,
        sorted_records: list[MarketPlayerRecord],
        *,
        cursor: str,
        sort: str,
        query_signature: dict[str, Any],
    ) -> int:
        cursor_key = self._decode_player_cursor(cursor, query_signature=query_signature)
        start_index = 0
        for record in sorted_records:
            if self._player_sort_key(record, sort=sort) <= cursor_key:
                start_index += 1
                continue
            break
        return start_index

    def _summary_payload(self, record: MarketPlayerRecord) -> dict[str, Any]:
        if record.summary is None or not isinstance(record.summary.summary_json, dict):
            return {}
        return record.summary.summary_json

    def _national_team_payload(self, record: MarketPlayerRecord) -> dict[str, Any]:
        summary_payload = self._summary_payload(record)
        national_team = summary_payload.get("national_team")
        if isinstance(national_team, dict):
            return national_team
        real_player_profile = summary_payload.get("real_player_profile")
        if isinstance(real_player_profile, dict):
            nested_payload = real_player_profile.get("national_team")
            if isinstance(nested_payload, dict):
                return nested_payload
        return {}

    def _national_team_candidates(self, record: MarketPlayerRecord) -> set[str]:
        national_team = self._national_team_payload(record)
        if not national_team:
            return set()
        candidates = {
            self._normalize_text(national_team.get("name")),
            self._normalize_text(national_team.get("code")),
            self._normalize_text(national_team.get("label")),
        }
        name = self._normalize_text(national_team.get("name"))
        code = self._normalize_text(national_team.get("code"))
        age_group = self._normalize_text(national_team.get("age_group"))
        if name and age_group:
            candidates.add(self._normalize_text(f"{name} {age_group}"))
        if code and age_group:
            candidates.add(self._normalize_text(f"{code} {age_group}"))
        return {candidate for candidate in candidates if candidate}

    def _national_team_search_terms(self, record: MarketPlayerRecord) -> list[str | None]:
        national_team = self._national_team_payload(record)
        if not national_team:
            return []
        return [
            national_team.get("name"),
            national_team.get("code"),
            national_team.get("age_group"),
            national_team.get("label"),
        ]

    def _breakdown_payload(self, record: MarketPlayerRecord) -> dict[str, Any]:
        if record.latest_snapshot is None or not isinstance(record.latest_snapshot.breakdown_json, dict):
            return {}
        return record.latest_snapshot.breakdown_json

    def _current_value_credits(self, record: MarketPlayerRecord) -> float | None:
        override = self._manual_price_override(record.player.id)
        if override is not None:
            return override
        if record.summary is not None:
            summary_value = self._positive_display_value(record.summary.current_value_credits)
            if summary_value is not None:
                return summary_value
        if record.latest_snapshot is not None:
            snapshot_value = self._positive_display_value(record.latest_snapshot.target_credits)
            if snapshot_value is not None:
                return snapshot_value
        real_world_value = self._real_world_value_credits(record)
        if real_world_value is not None:
            return real_world_value
        return None

    def _previous_value_credits(self, record: MarketPlayerRecord) -> float | None:
        if record.summary is not None:
            return round_gtex_display_value(record.summary.previous_value_credits)
        if record.latest_snapshot is not None:
            return round_gtex_display_value(record.latest_snapshot.previous_credits)
        return None

    def _movement_pct(self, record: MarketPlayerRecord) -> float | None:
        override = self._manual_price_override(record.player.id)
        if override is not None:
            previous_value = self._previous_value_credits(record)
            if previous_value in {None, 0}:
                return None
            return round(((override - previous_value) / previous_value) * 100.0, 4)
        if record.summary is not None:
            return record.summary.movement_pct
        if record.latest_snapshot is not None:
            return record.latest_snapshot.movement_pct
        return None

    def _football_truth_value_credits(self, record: MarketPlayerRecord) -> float | None:
        summary_payload = self._summary_payload(record)
        value = round_gtex_display_value(self._coerce_float(summary_payload.get("football_truth_value_credits")))
        if value is not None:
            return value
        if record.latest_snapshot is not None:
            return round_gtex_display_value(record.latest_snapshot.football_truth_value_credits)
        return None

    def _market_signal_value_credits(self, record: MarketPlayerRecord) -> float | None:
        summary_payload = self._summary_payload(record)
        value = round_gtex_display_value(self._coerce_float(summary_payload.get("market_signal_value_credits")))
        if value is not None:
            return value
        if record.latest_snapshot is not None:
            return round_gtex_display_value(record.latest_snapshot.market_signal_value_credits)
        return None

    def _published_card_value_credits(self, record: MarketPlayerRecord) -> float | None:
        override = self._manual_price_override(record.player.id)
        if override is not None:
            return override
        summary_payload = self._summary_payload(record)
        value = round_gtex_display_value(self._coerce_float(summary_payload.get("published_card_value_credits")))
        if value is not None:
            return value
        breakdown_payload = self._breakdown_payload(record)
        breakdown_value = round_gtex_display_value(
            self._coerce_float(breakdown_payload.get("published_card_value_credits"))
        )
        if breakdown_value is not None:
            return breakdown_value
        return self._current_value_credits(record)

    def _global_scouting_index(self, record: MarketPlayerRecord) -> float | None:
        summary_payload = self._summary_payload(record)
        value = self._coerce_float(summary_payload.get("global_scouting_index"))
        if value is not None:
            return value
        breakdown_payload = self._breakdown_payload(record)
        return self._coerce_float(breakdown_payload.get("global_scouting_index"))

    def _previous_global_scouting_index(self, record: MarketPlayerRecord) -> float | None:
        summary_payload = self._summary_payload(record)
        value = self._coerce_float(summary_payload.get("previous_global_scouting_index"))
        if value is not None:
            return value
        breakdown_payload = self._breakdown_payload(record)
        return self._coerce_float(breakdown_payload.get("previous_global_scouting_index"))

    def _global_scouting_index_movement_pct(self, record: MarketPlayerRecord) -> float | None:
        summary_payload = self._summary_payload(record)
        value = self._coerce_float(summary_payload.get("global_scouting_index_movement_pct"))
        if value is not None:
            return value
        breakdown_payload = self._breakdown_payload(record)
        return self._coerce_float(breakdown_payload.get("global_scouting_index_movement_pct"))

    def _trend_score(self, record: MarketPlayerRecord) -> float | None:
        scouting_index = self._global_scouting_index(record)
        if scouting_index is not None:
            return scouting_index
        if record.summary is None:
            return None
        return float(record.summary.market_interest_score)

    def _drivers(self, record: MarketPlayerRecord) -> tuple[str, ...]:
        summary_payload = self._summary_payload(record)
        if "drivers" in summary_payload:
            return self._string_tuple(summary_payload.get("drivers"))
        if record.latest_snapshot is not None:
            return self._string_tuple(record.latest_snapshot.drivers_json)
        return ()

    def _reference_price(self, record: MarketPlayerRecord) -> float | None:
        override = self._manual_price_override(record.player.id)
        if override is not None:
            return override
        authoritative_value = authoritative_reference_credits(
            summary=record.summary,
            latest_snapshot=record.latest_snapshot,
            summary_payload=self._summary_payload(record),
            breakdown_payload=self._breakdown_payload(record),
        )
        if authoritative_value is not None:
            display_value = self._positive_display_value(authoritative_value)
            if display_value is not None:
                return display_value
        real_world_value = self._real_world_value_credits(record)
        if real_world_value is not None:
            return real_world_value
        return None

    def _require_reference_price(self, record: MarketPlayerRecord) -> float | None:
        reference_price = self._reference_price(record)
        if reference_price is None and record.player.is_real_player:
            raise MarketValidationError(f"Authoritative pricing is unavailable for real player '{record.player.id}'.")
        return reference_price

    def _real_world_value_credits(self, record: MarketPlayerRecord) -> float | None:
        for value in (record.player.current_market_reference_value, record.player.market_value_eur):
            if value is None or value <= 0:
                continue
            return self._positive_display_value(credits_from_real_world_value(value))
        return None

    def _real_world_market_value_eur(self, record: MarketPlayerRecord) -> float | None:
        for value in (record.player.current_market_reference_value, record.player.market_value_eur):
            if value is None or value <= 0:
                continue
            return float(value)
        return None

    @staticmethod
    def _positive_display_value(value: float | None) -> float | None:
        if value is None or value <= 0:
            return None
        return round_gtex_display_value(value)

    def _pricing_symbol(self, record: MarketPlayerRecord) -> str | None:
        return record.player.short_name

    def _trending_rank(self, record: MarketPlayerRecord, snapshot: PlayerPricingSnapshot) -> float:
        market_interest = float(record.summary.market_interest_score) if record.summary is not None else 0.0
        discovery_trend = self._trend_score(record) or 0.0
        book_signal = float(snapshot.best_bid is not None) + float(snapshot.best_ask is not None)
        real_world_impact = self._real_world_impact(record.player.id)
        return round(
            (snapshot.volume_24h * 5.0)
            + abs(snapshot.day_change_percent)
            + (market_interest / 10.0)
            + (discovery_trend / 10.0)
            + book_signal,
            4,
        ) + round(
            (len(real_world_impact.active_flag_codes) * 2.0)
            + max(real_world_impact.market_buzz_score, 0.0)
            + max(real_world_impact.recommendation_priority_delta, 0.0)
            + max(real_world_impact.market_effect_total, 0.0),
            4,
        )

    def _real_world_impact(self, player_id: str) -> PlayerRealWorldImpact:
        cached = self._real_world_impact_cache.get(player_id)
        if cached is not None:
            return cached
        impact = RealWorldFootballEventService(self.session).get_player_impact(player_id)
        self._real_world_impact_cache[player_id] = impact
        return impact

    def _supply_tier_payload(self, record: MarketPlayerRecord) -> dict[str, Any] | None:
        summary_payload = self._summary_payload(record)
        supply_tier = summary_payload.get("supply_tier")
        if isinstance(supply_tier, dict):
            return supply_tier
        if record.player.supply_tier is None:
            return None
        return {
            "code": record.player.supply_tier.code,
            "name": record.player.supply_tier.name,
            "circulating_supply": record.player.supply_tier.circulating_supply,
            "daily_pack_supply": record.player.supply_tier.daily_pack_supply,
            "season_mint_cap": record.player.supply_tier.season_mint_cap,
        }

    def _liquidity_band_payload(self, record: MarketPlayerRecord) -> dict[str, Any] | None:
        summary_payload = self._summary_payload(record)
        liquidity_band = summary_payload.get("liquidity_band")
        if isinstance(liquidity_band, dict):
            return liquidity_band
        if record.player.liquidity_band is None:
            return None
        return {
            "code": record.player.liquidity_band.code,
            "name": record.player.liquidity_band.name,
            "max_spread_bps": record.player.liquidity_band.max_spread_bps,
            "maker_inventory_target": record.player.liquidity_band.maker_inventory_target,
            "instant_sell_fee_bps": record.player.liquidity_band.instant_sell_fee_bps,
        }

    def _player_age(self, date_of_birth: date | None) -> int | None:
        if date_of_birth is None:
            return None
        reference_date = self.today or date.today()
        return (
            reference_date.year
            - date_of_birth.year
            - ((reference_date.month, reference_date.day) < (date_of_birth.month, date_of_birth.day))
        )

    def _nationality_code(self, record: MarketPlayerRecord) -> str | None:
        if record.player.country is None:
            return None
        return record.player.country.alpha3_code or record.player.country.fifa_code or record.player.country.alpha2_code

    def _last_snapshot_id(self, record: MarketPlayerRecord) -> str | None:
        if record.summary is not None and record.summary.last_snapshot_id is not None:
            return record.summary.last_snapshot_id
        if record.latest_snapshot is not None:
            return record.latest_snapshot.id
        return None

    def _last_snapshot_at(self, record: MarketPlayerRecord) -> Any | None:
        if record.summary is not None:
            return record.summary.last_snapshot_at
        if record.latest_snapshot is not None:
            return record.latest_snapshot.as_of
        return None

    def _avatar(self, record: MarketPlayerRecord) -> PlayerAvatarView:
        summary_payload = self._summary_payload(record)
        return self.avatar_service.build_from_payload(
            AvatarIdentityInput(
                player_id=record.player.id,
                player_name=record.player.full_name,
                position=record.player.position,
                normalized_position=record.player.normalized_position,
                nationality=record.player.country.name if record.player.country is not None else None,
                nationality_code=self._nationality_code(record),
                birth_year=record.player.date_of_birth.year if record.player.date_of_birth is not None else None,
                preferred_foot=record.player.preferred_foot,
                avatar_seed_token=summary_payload.get("avatar_seed_token"),
                avatar_dna_seed=summary_payload.get("avatar_dna_seed"),
            )
        )

    def _image_url(self, record: MarketPlayerRecord) -> str | None:
        candidates = sorted(
            record.player.image_metadata,
            key=lambda image: (
                not image.is_primary,
                image.moderation_status != "approved",
                image.created_at,
                image.id,
            ),
        )
        for image in candidates:
            if image.source_url:
                return image.source_url
            if image.storage_key:
                return image.storage_key
        return None

    def _country_code(self, country: Any | None) -> str | None:
        if country is None:
            return None
        return country.alpha3_code or country.fifa_code or country.alpha2_code

    def _country_id(self, country: Any | None) -> str | None:
        if country is None:
            return None
        return country.alpha3_code or country.fifa_code or country.alpha2_code or country.id

    def _slug(self, value: str) -> str:
        normalized = self._normalize_text(value).replace(" ", "-")
        return normalized or "unknown"

    def _finalize_count_item(self, item: dict[str, Any]) -> dict[str, Any]:
        clubs = item.pop("_clubs", None)
        if clubs is not None:
            item["club_count"] = len(clubs)
        return item

    def _normalize_optional_text(self, value: str | None) -> str | None:
        normalized = self._normalize_text(value)
        return normalized or None

    def _normalize_text(self, value: str | None) -> str:
        if value is None:
            return ""
        return " ".join(value.strip().lower().split())

    def _string_tuple(self, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(str(item) for item in value if item is not None and str(item).strip())

    def _coerce_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _coerce_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def _manual_price_override(self, player_id: str) -> float | None:
        if self.runtime_controls is None:
            return None
        for asset_type in ("player", "player_card", "market_player"):
            override = self.runtime_controls.get_price_override(asset_type=asset_type, asset_id=player_id)
            if override is None:
                continue
            return self._coerce_float(override.override_price)
        return None
