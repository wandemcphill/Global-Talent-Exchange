from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.user import User
from backend.app.player_cards.schemas import (
    PlayerCardHoldingView,
    PlayerCardLoanBorrowRequest,
    PlayerCardLoanContractView,
    PlayerCardLoanListingCreateRequest,
    PlayerCardLoanListingView,
    PlayerCardListingBuyRequest,
    PlayerCardListingCreateRequest,
    PlayerCardListingView,
    PlayerCardPlayerDetailView,
    PlayerCardPlayerSummaryView,
    PlayerCardSaleView,
    StarterSquadRentalCreateRequest,
    StarterSquadRentalView,
    PlayerCardWatchlistCreateRequest,
    PlayerCardWatchlistView,
)
from backend.app.player_cards.marketplace_schemas import (
    PlayerCardMarketplaceListingView,
    PlayerCardMarketplaceLoanContractListResponse,
    PlayerCardMarketplaceLoanContractView,
    PlayerCardMarketplaceLoanListingCreateRequest,
    PlayerCardMarketplaceLoanListingView,
    PlayerCardMarketplaceLoanNegotiationCreateRequest,
    PlayerCardMarketplaceLoanNegotiationView,
    PlayerCardMarketplaceSaleExecutionView,
    PlayerCardMarketplaceSaleListingCreateRequest,
    PlayerCardMarketplaceSalePurchaseRequest,
    PlayerCardMarketplaceSearchResponse,
    PlayerCardMarketplaceSwapExecuteRequest,
    PlayerCardMarketplaceSwapExecutionView,
    PlayerCardMarketplaceSwapListingCreateRequest,
    PlayerCardMarketplaceSwapListingView,
)
from backend.app.player_cards.marketplace_service import PlayerCardMarketplaceService
from backend.app.player_cards.access_service import CardLoanService, StarterSquadRentalService
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


def get_loan_service(request: Request, session: Session = Depends(get_session)) -> CardLoanService:
    event_publisher = getattr(request.app.state, "event_publisher", None)
    wallet_service = WalletService(event_publisher=event_publisher) if event_publisher else WalletService()
    return CardLoanService(session=session, wallet_service=wallet_service)


def get_rental_service(request: Request, session: Session = Depends(get_session)) -> StarterSquadRentalService:
    event_publisher = getattr(request.app.state, "event_publisher", None)
    wallet_service = WalletService(event_publisher=event_publisher) if event_publisher else WalletService()
    return StarterSquadRentalService(session=session, wallet_service=wallet_service)


def get_marketplace_service(request: Request, session: Session = Depends(get_session)) -> PlayerCardMarketplaceService:
    event_publisher = getattr(request.app.state, "event_publisher", None)
    wallet_service = WalletService(event_publisher=event_publisher) if event_publisher else WalletService()
    return PlayerCardMarketplaceService(
        session=session,
        wallet_service=wallet_service,
        event_publisher=event_publisher or InMemoryEventPublisher(),
        settings=request.app.state.settings,
    )


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


@router.get("/loans", response_model=list[PlayerCardLoanListingView])
def list_loan_listings(
    position: str | None = Query(default=None),
    tier_code: str | None = Query(default=None),
    max_cost: float | None = Query(default=None, ge=0),
    max_duration_days: int | None = Query(default=None, ge=1, le=30),
    limit: int = Query(default=100, ge=1, le=250),
    service: CardLoanService = Depends(get_loan_service),
) -> list[PlayerCardLoanListingView]:
    listings = service.list_listings(
        position=position,
        tier_code=tier_code,
        max_cost=None if max_cost is None else max_cost,
        max_duration_days=max_duration_days,
        limit=limit,
    )
    return [PlayerCardLoanListingView.model_validate(item) for item in listings]


@router.post("/loans", response_model=PlayerCardLoanListingView, status_code=status.HTTP_201_CREATED)
def create_loan_listing(
    payload: PlayerCardLoanListingCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CardLoanService = Depends(get_loan_service),
) -> PlayerCardLoanListingView:
    try:
        listing = service.create_listing(
            actor=current_user,
            player_card_id=payload.player_card_id,
            total_slots=payload.total_slots,
            duration_days=payload.duration_days,
            loan_fee_credits=payload.loan_fee_credits,
            usage_restrictions=payload.usage_restrictions_json,
            terms=payload.terms_json,
        )
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardLoanListingView.model_validate(listing)


@router.post("/loans/{loan_listing_id}/borrow", response_model=PlayerCardLoanContractView)
def borrow_loan_listing(
    loan_listing_id: str,
    payload: PlayerCardLoanBorrowRequest,
    current_user: User = Depends(get_current_user),
    service: CardLoanService = Depends(get_loan_service),
) -> PlayerCardLoanContractView:
    try:
        contract = service.borrow_listing(
            actor=current_user,
            listing_id=loan_listing_id,
            competition_id=payload.competition_id,
            squad_scope=payload.squad_scope,
        )
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlayerCardLoanContractView.model_validate(contract)


@router.post("/loans/contracts/{loan_contract_id}/return", response_model=PlayerCardLoanContractView)
def return_loan_listing(
    loan_contract_id: str,
    current_user: User = Depends(get_current_user),
    service: CardLoanService = Depends(get_loan_service),
) -> PlayerCardLoanContractView:
    try:
        contract = service.return_loan(actor=current_user, contract_id=loan_contract_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardLoanContractView.model_validate(contract)


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


@router.get("/marketplace/listings", response_model=PlayerCardMarketplaceSearchResponse)
def search_marketplace_listings(
    search: str | None = Query(default=None),
    club: str | None = Query(default=None),
    position: str | None = Query(default=None),
    rating_min: float | None = Query(default=None),
    rating_max: float | None = Query(default=None),
    tier_code: str | None = Query(default=None),
    rarity_rank_min: int | None = Query(default=None, ge=1),
    rarity_rank_max: int | None = Query(default=None, ge=1),
    asset_origin: str | None = Query(default=None),
    listing_type: str | None = Query(default=None),
    sale_price_min: float | None = Query(default=None, ge=0),
    sale_price_max: float | None = Query(default=None, ge=0),
    loan_fee_min: float | None = Query(default=None, ge=0),
    loan_fee_max: float | None = Query(default=None, ge=0),
    loan_duration_min: int | None = Query(default=None, ge=1, le=30),
    loan_duration_max: int | None = Query(default=None, ge=1, le=30),
    availability: str = Query(default="available"),
    negotiable: bool | None = Query(default=None),
    sort: str = Query(default="relevance"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSearchResponse:
    try:
        payload = service.search_marketplace(
            listing_type=listing_type,
            search=search,
            club=club,
            position=position,
            rating_min=rating_min,
            rating_max=rating_max,
            tier_code=tier_code,
            rarity_rank_min=rarity_rank_min,
            rarity_rank_max=rarity_rank_max,
            asset_origin=asset_origin,
            sale_price_min=sale_price_min,
            sale_price_max=sale_price_max,
            loan_fee_min=loan_fee_min,
            loan_fee_max=loan_fee_max,
            loan_duration_min=loan_duration_min,
            loan_duration_max=loan_duration_max,
            availability=availability,
            negotiable=negotiable,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceSearchResponse.model_validate(payload)


@router.get("/marketplace/sales", response_model=PlayerCardMarketplaceSearchResponse)
def list_marketplace_sales(
    search: str | None = Query(default=None),
    club: str | None = Query(default=None),
    position: str | None = Query(default=None),
    rating_min: float | None = Query(default=None),
    rating_max: float | None = Query(default=None),
    tier_code: str | None = Query(default=None),
    rarity_rank_min: int | None = Query(default=None, ge=1),
    rarity_rank_max: int | None = Query(default=None, ge=1),
    asset_origin: str | None = Query(default=None),
    sale_price_min: float | None = Query(default=None, ge=0),
    sale_price_max: float | None = Query(default=None, ge=0),
    availability: str = Query(default="available"),
    negotiable: bool | None = Query(default=None),
    sort: str = Query(default="relevance"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSearchResponse:
    return search_marketplace_listings(
        search=search,
        club=club,
        position=position,
        rating_min=rating_min,
        rating_max=rating_max,
        tier_code=tier_code,
        rarity_rank_min=rarity_rank_min,
        rarity_rank_max=rarity_rank_max,
        asset_origin=asset_origin,
        listing_type="sale",
        sale_price_min=sale_price_min,
        sale_price_max=sale_price_max,
        availability=availability,
        negotiable=negotiable,
        sort=sort,
        limit=limit,
        offset=offset,
        service=service,
    )


@router.get("/marketplace/loans", response_model=PlayerCardMarketplaceSearchResponse)
def list_marketplace_loans(
    search: str | None = Query(default=None),
    club: str | None = Query(default=None),
    position: str | None = Query(default=None),
    rating_min: float | None = Query(default=None),
    rating_max: float | None = Query(default=None),
    tier_code: str | None = Query(default=None),
    rarity_rank_min: int | None = Query(default=None, ge=1),
    rarity_rank_max: int | None = Query(default=None, ge=1),
    asset_origin: str | None = Query(default=None),
    loan_fee_min: float | None = Query(default=None, ge=0),
    loan_fee_max: float | None = Query(default=None, ge=0),
    loan_duration_min: int | None = Query(default=None, ge=1, le=30),
    loan_duration_max: int | None = Query(default=None, ge=1, le=30),
    availability: str = Query(default="available"),
    negotiable: bool | None = Query(default=None),
    sort: str = Query(default="relevance"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSearchResponse:
    return search_marketplace_listings(
        search=search,
        club=club,
        position=position,
        rating_min=rating_min,
        rating_max=rating_max,
        tier_code=tier_code,
        rarity_rank_min=rarity_rank_min,
        rarity_rank_max=rarity_rank_max,
        asset_origin=asset_origin,
        listing_type="loan",
        loan_fee_min=loan_fee_min,
        loan_fee_max=loan_fee_max,
        loan_duration_min=loan_duration_min,
        loan_duration_max=loan_duration_max,
        availability=availability,
        negotiable=negotiable,
        sort=sort,
        limit=limit,
        offset=offset,
        service=service,
    )


@router.get("/marketplace/swaps", response_model=PlayerCardMarketplaceSearchResponse)
def list_marketplace_swaps(
    search: str | None = Query(default=None),
    club: str | None = Query(default=None),
    position: str | None = Query(default=None),
    rating_min: float | None = Query(default=None),
    rating_max: float | None = Query(default=None),
    tier_code: str | None = Query(default=None),
    rarity_rank_min: int | None = Query(default=None, ge=1),
    rarity_rank_max: int | None = Query(default=None, ge=1),
    asset_origin: str | None = Query(default=None),
    availability: str = Query(default="available"),
    negotiable: bool | None = Query(default=None),
    sort: str = Query(default="relevance"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSearchResponse:
    return search_marketplace_listings(
        search=search,
        club=club,
        position=position,
        rating_min=rating_min,
        rating_max=rating_max,
        tier_code=tier_code,
        rarity_rank_min=rarity_rank_min,
        rarity_rank_max=rarity_rank_max,
        asset_origin=asset_origin,
        listing_type="swap",
        availability=availability,
        negotiable=negotiable,
        sort=sort,
        limit=limit,
        offset=offset,
        service=service,
    )


@router.post("/marketplace/sales", response_model=PlayerCardMarketplaceListingView, status_code=status.HTTP_201_CREATED)
def create_marketplace_sale_listing(
    payload: PlayerCardMarketplaceSaleListingCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceListingView:
    try:
        listing = service.create_sale_listing(
            actor=current_user,
            player_card_id=payload.player_card_id,
            quantity=payload.quantity,
            price_per_card_credits=payload.price_per_card_credits,
            is_negotiable=payload.is_negotiable,
            expires_at=payload.expires_at,
        )
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceListingView.model_validate(listing)


@router.post("/marketplace/sales/{listing_id}/cancel", response_model=PlayerCardMarketplaceListingView)
def cancel_marketplace_sale_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceListingView:
    try:
        listing = service.cancel_sale_listing(actor=current_user, listing_id=listing_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceListingView.model_validate(listing)


@router.post("/marketplace/sales/{listing_id}/buy", response_model=PlayerCardMarketplaceSaleExecutionView)
def buy_marketplace_sale_listing(
    listing_id: str,
    payload: PlayerCardMarketplaceSalePurchaseRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSaleExecutionView:
    try:
        sale = service.buy_sale_listing(actor=current_user, listing_id=listing_id, quantity=payload.quantity)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlayerCardMarketplaceSaleExecutionView.model_validate(sale)


@router.post("/marketplace/loans", response_model=PlayerCardMarketplaceLoanListingView, status_code=status.HTTP_201_CREATED)
def create_marketplace_loan_listing(
    payload: PlayerCardMarketplaceLoanListingCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanListingView:
    try:
        listing = service.create_loan_listing(actor=current_user, **payload.model_dump())
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanListingView.model_validate(listing)


@router.post("/marketplace/loans/{listing_id}/cancel", response_model=PlayerCardMarketplaceLoanListingView)
def cancel_marketplace_loan_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanListingView:
    try:
        listing = service.cancel_loan_listing(actor=current_user, listing_id=listing_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanListingView.model_validate(listing)


@router.post("/marketplace/loans/{listing_id}/negotiations", response_model=PlayerCardMarketplaceLoanNegotiationView, status_code=status.HTTP_201_CREATED)
def create_marketplace_loan_negotiation(
    listing_id: str,
    payload: PlayerCardMarketplaceLoanNegotiationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanNegotiationView:
    try:
        negotiation = service.create_loan_negotiation(actor=current_user, listing_id=listing_id, **payload.model_dump())
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanNegotiationView.model_validate(negotiation)


@router.post("/marketplace/loans/negotiations/{negotiation_id}/counter", response_model=PlayerCardMarketplaceLoanNegotiationView)
def counter_marketplace_loan_negotiation(
    negotiation_id: str,
    payload: PlayerCardMarketplaceLoanNegotiationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanNegotiationView:
    try:
        negotiation = service.counter_loan_negotiation(actor=current_user, negotiation_id=negotiation_id, **payload.model_dump())
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanNegotiationView.model_validate(negotiation)


@router.post("/marketplace/loans/negotiations/{negotiation_id}/accept", response_model=PlayerCardMarketplaceLoanContractView)
def accept_marketplace_loan_negotiation(
    negotiation_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanContractView:
    try:
        contract = service.accept_loan_negotiation(actor=current_user, negotiation_id=negotiation_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanContractView.model_validate(contract)


@router.get("/marketplace/loans/contracts", response_model=PlayerCardMarketplaceLoanContractListResponse)
def list_marketplace_loan_contracts(
    role: str | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanContractListResponse:
    try:
        payload = service.list_loan_contracts(actor=current_user, role=role, status=status_filter)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanContractListResponse.model_validate(payload)


@router.post("/marketplace/loans/contracts/{contract_id}/settle", response_model=PlayerCardMarketplaceLoanContractView)
def settle_marketplace_loan_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanContractView:
    try:
        contract = service.settle_loan_contract(actor=current_user, contract_id=contract_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlayerCardMarketplaceLoanContractView.model_validate(contract)


@router.post("/marketplace/loans/contracts/{contract_id}/return", response_model=PlayerCardMarketplaceLoanContractView)
def return_marketplace_loan_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceLoanContractView:
    try:
        contract = service.return_loan_contract(actor=current_user, contract_id=contract_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceLoanContractView.model_validate(contract)


@router.post("/marketplace/swaps", response_model=PlayerCardMarketplaceSwapListingView, status_code=status.HTTP_201_CREATED)
def create_marketplace_swap_listing(
    payload: PlayerCardMarketplaceSwapListingCreateRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSwapListingView:
    try:
        listing = service.create_swap_listing(actor=current_user, **payload.model_dump())
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceSwapListingView.model_validate(listing)


@router.post("/marketplace/swaps/{listing_id}/cancel", response_model=PlayerCardMarketplaceSwapListingView)
def cancel_marketplace_swap_listing(
    listing_id: str,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSwapListingView:
    try:
        listing = service.cancel_swap_listing(actor=current_user, listing_id=listing_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceSwapListingView.model_validate(listing)


@router.post("/marketplace/swaps/{listing_id}/execute", response_model=PlayerCardMarketplaceSwapExecutionView)
def execute_marketplace_swap_listing(
    listing_id: str,
    payload: PlayerCardMarketplaceSwapExecuteRequest,
    current_user: User = Depends(get_current_user),
    service: PlayerCardMarketplaceService = Depends(get_marketplace_service),
) -> PlayerCardMarketplaceSwapExecutionView:
    try:
        execution = service.execute_swap_listing(actor=current_user, listing_id=listing_id, counterparty_player_card_id=payload.counterparty_player_card_id)
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    return PlayerCardMarketplaceSwapExecutionView.model_validate(execution)


@router.get("/watchlist", response_model=list[PlayerCardWatchlistView])
def list_watchlist(current_user: User = Depends(get_current_user), service: PlayerCardMarketService = Depends(get_service)) -> list[PlayerCardWatchlistView]:
    items = service.list_watchlist(actor=current_user)
    return [PlayerCardWatchlistView.model_validate(item) for item in items]


@router.get("/starter-rental", response_model=StarterSquadRentalView | None)
def get_starter_rental(
    current_user: User = Depends(get_current_user),
    service: StarterSquadRentalService = Depends(get_rental_service),
) -> StarterSquadRentalView | None:
    rental = service.get_active_rental(actor=current_user)
    return None if rental is None else StarterSquadRentalView.model_validate(rental)


@router.post("/starter-rental", response_model=StarterSquadRentalView, status_code=status.HTTP_201_CREATED)
def create_starter_rental(
    payload: StarterSquadRentalCreateRequest,
    current_user: User = Depends(get_current_user),
    service: StarterSquadRentalService = Depends(get_rental_service),
) -> StarterSquadRentalView:
    try:
        rental = service.create_rental(
            actor=current_user,
            club_id=payload.club_id,
            include_academy=payload.include_academy,
            first_team_count=payload.first_team_count,
            academy_count=payload.academy_count,
            term_days=payload.term_days,
            rental_fee_credits=payload.rental_fee_credits,
        )
    except PlayerCardMarketError as exc:
        raise_player_card_http(exc)
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return StarterSquadRentalView.model_validate(rental)


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
