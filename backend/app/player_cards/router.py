from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.user import User
from backend.app.player_cards.schemas import (
    PlayerCardHoldingView,
    PlayerCardListingBuyRequest,
    PlayerCardListingCreateRequest,
    PlayerCardListingView,
    PlayerCardPlayerDetailView,
    PlayerCardPlayerSummaryView,
    PlayerCardSaleView,
    PlayerCardWatchlistCreateRequest,
    PlayerCardWatchlistView,
)
from backend.app.player_cards.service import (
    PlayerCardMarketError,
    PlayerCardMarketService,
    PlayerCardNotFoundError,
    PlayerCardPermissionError,
    PlayerCardValidationError,
)
from backend.app.wallets.service import InsufficientBalanceError, WalletService
from backend.app.core.events import InMemoryEventPublisher

router = APIRouter(prefix="/player-cards", tags=["player-cards"])


def get_service(request: Request, session: Session = Depends(get_session)) -> PlayerCardMarketService:
    event_publisher = getattr(request.app.state, "event_publisher", None)
    wallet_service = WalletService(event_publisher=event_publisher) if event_publisher else WalletService()
    return PlayerCardMarketService(session=session, wallet_service=wallet_service, event_publisher=event_publisher or InMemoryEventPublisher())


def raise_player_card_http(exc: PlayerCardMarketError) -> None:
    if isinstance(exc, PlayerCardNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PlayerCardPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, PlayerCardValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/players", response_model=list[PlayerCardPlayerSummaryView])
def list_players(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: PlayerCardMarketService = Depends(get_service),
) -> list[PlayerCardPlayerSummaryView]:
    results = service.list_players(search=search, limit=limit, offset=offset)
    return [PlayerCardPlayerSummaryView.model_validate(item) for item in results]


@router.get("/players/{player_id}", response_model=PlayerCardPlayerDetailView)
def get_player_detail(player_id: str, service: PlayerCardMarketService = Depends(get_service)) -> PlayerCardPlayerDetailView:
    try:
        detail = service.get_player_detail(player_id=player_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardPlayerDetailView.model_validate(detail)


@router.get("/inventory", response_model=list[PlayerCardHoldingView])
def list_inventory(current_user: User = Depends(get_current_user), service: PlayerCardMarketService = Depends(get_service)) -> list[PlayerCardHoldingView]:
    inventory = service.list_inventory(actor=current_user)
    return [PlayerCardHoldingView.model_validate(item) for item in inventory]


@router.get("/listings", response_model=list[PlayerCardListingView])
def list_listings(
    status_filter: str = Query(default="open"),
    player_id: str | None = Query(default=None),
    tier_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    service: PlayerCardMarketService = Depends(get_service),
) -> list[PlayerCardListingView]:
    listings = service.list_listings(status=status_filter, player_id=player_id, tier_id=tier_id, limit=limit)
    return [PlayerCardListingView.model_validate(item) for item in listings]


@router.get("/listings/mine", response_model=list[PlayerCardListingView])
def list_my_listings(current_user: User = Depends(get_current_user), service: PlayerCardMarketService = Depends(get_service)) -> list[PlayerCardListingView]:
    listings = service.list_listings(status="open", seller_user_id=current_user.id)
    return [PlayerCardListingView.model_validate(item) for item in listings]


@router.post("/listings", response_model=PlayerCardListingView, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: PlayerCardListingCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketService = Depends(get_service),
) -> PlayerCardListingView:
    try:
        listing = service.create_listing(
            actor=current_user,
            player_card_id=payload.player_card_id,
            quantity=payload.quantity,
            price_per_card_credits=payload.price_per_card_credits,
        )
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardListingView.model_validate(listing)


@router.post("/listings/{listing_id}/cancel", response_model=PlayerCardListingView)
def cancel_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketService = Depends(get_service),
) -> PlayerCardListingView:
    try:
        listing = service.cancel_listing(actor=current_user, listing_id=listing_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardListingView.model_validate(listing)


@router.post("/listings/{listing_id}/buy", response_model=PlayerCardSaleView)
def buy_listing(
    listing_id: str,
    payload: PlayerCardListingBuyRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketService = Depends(get_service),
) -> PlayerCardSaleView:
    try:
        sale = service.buy_listing(actor=current_user, listing_id=listing_id, quantity=payload.quantity)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlayerCardSaleView.model_validate(sale)


@router.get("/watchlist", response_model=list[PlayerCardWatchlistView])
def list_watchlist(current_user: User = Depends(get_current_user), service: PlayerCardMarketService = Depends(get_service)) -> list[PlayerCardWatchlistView]:
    items = service.list_watchlist(actor=current_user)
    return [PlayerCardWatchlistView.model_validate(item) for item in items]


@router.post("/watchlist", response_model=PlayerCardWatchlistView, status_code=status.HTTP_201_CREATED)
def add_watchlist(
    payload: PlayerCardWatchlistCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketService = Depends(get_service),
) -> PlayerCardWatchlistView:
    try:
        watch = service.add_watchlist(actor=current_user, player_id=payload.player_id, player_card_id=payload.player_card_id, notes=payload.notes)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardWatchlistView.model_validate(watch)


@router.delete("/watchlist/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist(
    watchlist_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketService = Depends(get_service),
) -> None:
    try:
        service.remove_watchlist(actor=current_user, watchlist_id=watchlist_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return None


api_router = APIRouter(prefix="/api")
api_router.include_router(router)

combined_router = APIRouter(tags=["player-cards"])
combined_router.include_router(router)
combined_router.include_router(api_router)

router = combined_router
