from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.auth.dependencies import get_current_user
from backend.app.market.schemas import (
    ListingCreate,
    ListingView,
    OfferCounterCreate,
    OfferCreate,
    OfferView,
    TradeIntentCreate,
    TradeIntentView,
)
from backend.app.market.service import (
    MarketConflictError,
    MarketEngine,
    MarketError,
    MarketNotFoundError,
    MarketPermissionError,
    MarketValidationError,
)
from backend.app.models.user import User

router = APIRouter(prefix="/market", tags=["market"])


def get_market_engine(request: Request) -> MarketEngine:
    market_engine = getattr(request.app.state, "market_engine", None)
    if market_engine is None:
        market_engine = MarketEngine()
        request.app.state.market_engine = market_engine
    return market_engine


def raise_market_http_exception(exc: MarketError) -> Never:
    if isinstance(exc, MarketNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, MarketPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, MarketConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, MarketValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/listings", response_model=ListingView, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> ListingView:
    try:
        listing = market_engine.create_listing(
            asset_id=payload.asset_id,
            seller_user_id=current_user.id,
            listing_type=payload.listing_type,
            ask_price=payload.ask_price,
            desired_asset_ids=payload.desired_asset_ids,
            note=payload.note,
        )
    except MarketError as exc:
        raise_market_http_exception(exc)

    return ListingView.model_validate(listing)


@router.post("/listings/{listing_id}/cancel", response_model=ListingView)
def cancel_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> ListingView:
    try:
        listing = market_engine.cancel_listing(listing_id=listing_id, acting_user_id=current_user.id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return ListingView.model_validate(listing)


@router.get("/listings/{listing_id}/offers", response_model=list[OfferView])
def list_listing_offers(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> list[OfferView]:
    try:
        market_engine.get_listing(listing_id)
        offers = market_engine.list_offers_for_listing(listing_id=listing_id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return [OfferView.model_validate(offer) for offer in offers]


@router.get("/listings/{listing_id}/matches", response_model=list[TradeIntentView])
def list_trade_intent_matches(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> list[TradeIntentView]:
    try:
        matches = market_engine.match_trade_intents(listing_id=listing_id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return [TradeIntentView.model_validate(intent) for intent in matches]


@router.post("/offers", response_model=OfferView, status_code=status.HTTP_201_CREATED)
def create_offer(
    payload: OfferCreate,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> OfferView:
    try:
        offer = market_engine.create_offer(
            asset_id=payload.asset_id,
            seller_user_id=payload.seller_user_id,
            buyer_user_id=current_user.id,
            cash_amount=payload.cash_amount,
            offered_asset_ids=payload.offered_asset_ids,
            listing_id=payload.listing_id,
            note=payload.note,
        )
    except MarketError as exc:
        raise_market_http_exception(exc)

    return OfferView.model_validate(offer)


@router.post("/offers/{offer_id}/counter", response_model=OfferView, status_code=status.HTTP_201_CREATED)
def counter_offer(
    offer_id: str,
    payload: OfferCounterCreate,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> OfferView:
    try:
        offer = market_engine.counter_offer(
            offer_id=offer_id,
            acting_user_id=current_user.id,
            cash_amount=payload.cash_amount,
            offered_asset_ids=payload.offered_asset_ids,
            note=payload.note,
        )
    except MarketError as exc:
        raise_market_http_exception(exc)

    return OfferView.model_validate(offer)


@router.post("/offers/{offer_id}/accept", response_model=OfferView)
def accept_offer(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> OfferView:
    try:
        offer = market_engine.accept_offer(offer_id=offer_id, acting_user_id=current_user.id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return OfferView.model_validate(offer)


@router.post("/offers/{offer_id}/reject", response_model=OfferView)
def reject_offer(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> OfferView:
    try:
        offer = market_engine.reject_offer(offer_id=offer_id, acting_user_id=current_user.id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return OfferView.model_validate(offer)


@router.post("/trade-intents", response_model=TradeIntentView, status_code=status.HTTP_201_CREATED)
def create_trade_intent(
    payload: TradeIntentCreate,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> TradeIntentView:
    try:
        trade_intent = market_engine.create_trade_intent(
            user_id=current_user.id,
            asset_id=payload.asset_id,
            direction=payload.direction,
            price_floor=payload.price_floor,
            price_ceiling=payload.price_ceiling,
            offered_asset_ids=payload.offered_asset_ids,
            note=payload.note,
        )
    except MarketError as exc:
        raise_market_http_exception(exc)

    return TradeIntentView.model_validate(trade_intent)


@router.post("/trade-intents/{intent_id}/withdraw", response_model=TradeIntentView)
def withdraw_trade_intent(
    intent_id: str,
    current_user: User = Depends(get_current_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> TradeIntentView:
    try:
        trade_intent = market_engine.withdraw_trade_intent(intent_id=intent_id, acting_user_id=current_user.id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return TradeIntentView.model_validate(trade_intent)
