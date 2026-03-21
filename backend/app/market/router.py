from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_session
from app.market.read_models import MarketSummaryReadModel
from app.market.projections import MarketSummaryProjector
from app.market.schemas import (
    ListingCreate,
    ListingView,
    MarketPlayerDetailView,
    MarketPlayerHistoryView,
    MarketPlayerListView,
    MarketSummaryView,
    OfferCounterCreate,
    OfferCreate,
    OfferView,
    TradeIntentCreate,
    TradeIntentView,
)
from app.pricing.schemas import MarketCandlesView, MarketMoversView, MarketTickerView
from app.market.service import (
    MarketConflictError,
    MarketEngine,
    MarketError,
    MarketNotFoundError,
    MarketPlayerQueryService,
    MarketPermissionError,
    MarketValidationError,
)
from app.models.user import User

router = APIRouter(prefix="/market", tags=["market"])


def get_market_engine(request: Request) -> MarketEngine:
    market_engine = getattr(request.app.state, "market_engine", None)
    if market_engine is None:
        session_factory = getattr(request.app.state, "session_factory", None)
        summary_projector = MarketSummaryProjector(session_factory) if session_factory is not None else None
        market_engine = MarketEngine(summary_projector=summary_projector)
        request.app.state.market_engine = market_engine
    return market_engine


def get_market_player_query_service(
    request: Request,
    session: Session = Depends(get_session),
) -> MarketPlayerQueryService:
    return MarketPlayerQueryService(session=session, market_engine=get_market_engine(request))


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


@router.get("/summary/{asset_id}", response_model=MarketSummaryView)
def get_market_summary(
    asset_id: str,
    session: Session = Depends(get_session),
) -> MarketSummaryView:
    summary = session.get(MarketSummaryReadModel, asset_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Market summary for {asset_id} was not found")
    return MarketSummaryView.model_validate(summary)


@router.get("/players", response_model=MarketPlayerListView)
def list_market_players(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    position: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    club: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    sort: str = Query(default="current_value"),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerListView:
    try:
        result = service.list_players(
            limit=limit,
            offset=offset,
            position=position,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            search=search,
            sort=sort,
        )
    except MarketError as exc:
        raise_market_http_exception(exc)

    return MarketPlayerListView.model_validate(result)


@router.get("/players/{player_id}", response_model=MarketPlayerDetailView)
def get_market_player_detail(
    player_id: str,
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerDetailView:
    try:
        result = service.get_player_detail(player_id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return MarketPlayerDetailView.model_validate(result)


@router.get("/players/{player_id}/history", response_model=MarketPlayerHistoryView)
def get_market_player_history(
    player_id: str,
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerHistoryView:
    try:
        result = service.get_player_history(player_id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return MarketPlayerHistoryView.model_validate(result)


@router.get("/players/{player_id}/candles", response_model=MarketCandlesView)
def get_market_player_candles(
    player_id: str,
    interval: str = Query(default="1h"),
    limit: int = Query(default=30, ge=1, le=500),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketCandlesView:
    try:
        result = service.get_player_candles(player_id, interval=interval, limit=limit)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return MarketCandlesView.model_validate(result)


@router.get("/ticker/{player_id}", response_model=MarketTickerView)
def get_market_ticker(
    player_id: str,
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketTickerView:
    try:
        result = service.get_player_ticker(player_id)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return MarketTickerView.model_validate(result)


@router.get("/movers", response_model=MarketMoversView)
def get_market_movers(
    limit: int = Query(default=5, ge=1, le=25),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketMoversView:
    try:
        result = service.get_market_movers(limit=limit)
    except MarketError as exc:
        raise_market_http_exception(exc)

    return MarketMoversView.model_validate(result)


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


api_router = APIRouter(prefix="/api")
api_router.include_router(router)

combined_router = APIRouter(tags=["market"])
combined_router.include_router(router)
combined_router.include_router(api_router)

router = combined_router
