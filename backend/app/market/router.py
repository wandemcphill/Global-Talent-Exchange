from __future__ import annotations

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_trading_user, get_current_user
from app.auth.dependencies import get_session
from app.core.app_state import get_optional_app_settings
from app.core.cache_namespaces import PLAYER_MARKETS_CACHE_NAMESPACE
from app.core.response_cache import get_response_cache
from app.gtex.runtime import ensure_gtex_runtime
from app.gtex.schemas import CreatorTradeRequest, CreatorTradeView
from app.gtex.service import GtexConflictError, GtexError, GtexNotFoundError, GtexValidationError
from app.market.read_models import MarketSummaryReadModel
from app.market.projections import MarketSummaryProjector
from app.market.repositories import build_market_repository
from app.market.schemas import (
    ListingCreate,
    ListingView,
    MarketBrowseCatalogView,
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
from app.players.token_schemas import (
    PlayerShareHoldingView,
    PlayerSharePurchaseView,
    PlayerShareSaleView,
    PlayerShareTradeRequest,
    PlayerShareMarketView,
)
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService
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
from app.services.runtime_control_service import RuntimeControlService

router = APIRouter(prefix="/market", tags=["market"])


def _invalidate_player_markets_cache(request: Request) -> None:
    get_response_cache(request.app).invalidate(PLAYER_MARKETS_CACHE_NAMESPACE)


def get_market_engine(request: Request) -> MarketEngine:
    market_engine = getattr(request.app.state, "market_engine", None)
    if market_engine is None:
        session_factory = getattr(request.app.state, "session_factory", None)
        summary_projector = MarketSummaryProjector(session_factory) if session_factory is not None else None
        market_engine = MarketEngine(
            repository=build_market_repository(getattr(request.app.state.settings, "redis_url", None)),
            summary_projector=summary_projector,
            cache_backend=getattr(request.app.state, "cache_backend", None),
        )
        request.app.state.market_engine = market_engine
    return market_engine


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    if request.client is not None and request.client.host:
        return str(request.client.host)
    return None


def get_market_player_query_service(
    request: Request,
    session: Session = Depends(get_session),
) -> MarketPlayerQueryService:
    return MarketPlayerQueryService(
        session=session,
        market_engine=get_market_engine(request),
        runtime_controls=RuntimeControlService(request.app),
    )


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


def raise_gtex_http_exception(exc: GtexError) -> Never:
    if isinstance(exc, GtexNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, GtexConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, GtexValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def raise_player_share_market_http_exception(exc: PlayerTokenMarketError) -> Never:
    if exc.reason in {"player_not_found", "market_not_found", "holding_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if exc.reason in {
        "admin_required",
        "total_shares_invalid",
        "share_price_invalid",
        "liquidity_invalid",
        "market_status_invalid",
        "share_count_invalid",
        "market_inactive",
        "share_supply_insufficient",
        "shares_not_owned",
        "insufficient_balance",
        "market_liquidity_insufficient",
        "multiplier_invalid",
        "dividend_invalid",
        "no_shareholders",
        "no_circulation",
        "total_shares_below_circulation",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.post("/listings", response_model=ListingView, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    current_user: User = Depends(get_current_trading_user),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Market summary for {asset_id} was not found"
        )
    return MarketSummaryView.model_validate(summary)


@router.get("/players", response_model=MarketPlayerListView)
def list_market_players(
    request: Request = None,  # type: ignore[assignment]
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    position: str | None = Query(default=None),
    country: str | None = Query(default=None),
    nationality: str | None = Query(default=None),
    national_team: str | None = Query(default=None),
    club: str | None = Query(default=None),
    league: str | None = Query(default=None),
    division: str | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    min_value: float | None = Query(default=None, ge=0),
    max_value: float | None = Query(default=None, ge=0),
    availability: str | None = None,
    search: str | None = Query(default=None),
    sort: str = Query(default="current_value"),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerListView:
    settings = get_optional_app_settings(request.app) if request is not None else None
    if settings is not None and settings.api_cache_enabled:
        cached_payload = get_response_cache(request.app).get_json(
            namespace=PLAYER_MARKETS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
        )
        if cached_payload is not None:
            return MarketPlayerListView.model_validate(cached_payload)
    try:
        country_value = country if isinstance(country, str) else None
        result = service.list_players(
            limit=limit,
            cursor=cursor,
            offset=offset,
            position=position,
            country=country_value,
            nationality=nationality,
            national_team=national_team,
            club=club,
            league=league,
            division=division,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=availability,
            search=search,
            sort=sort,
        )
    except MarketError as exc:
        raise_market_http_exception(exc)

    response = MarketPlayerListView.model_validate(result)
    if settings is not None and settings.api_cache_enabled and request is not None:
        get_response_cache(request.app).set_json(
            namespace=PLAYER_MARKETS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
            payload=response.model_dump(mode="json"),
            ttl_seconds=settings.player_markets_cache_ttl_seconds,
        )
    return response


@router.get("/browse/catalog", response_model=MarketBrowseCatalogView)
def get_market_browse_catalog(
    request: Request = None,  # type: ignore[assignment]
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketBrowseCatalogView:
    settings = get_optional_app_settings(request.app) if request is not None else None
    if settings is not None and settings.api_cache_enabled:
        cached_payload = get_response_cache(request.app).get_json(
            namespace=PLAYER_MARKETS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
        )
        if cached_payload is not None:
            return MarketBrowseCatalogView.model_validate(cached_payload)
    response = MarketBrowseCatalogView.model_validate(service.browse_catalog())
    if settings is not None and settings.api_cache_enabled and request is not None:
        get_response_cache(request.app).set_json(
            namespace=PLAYER_MARKETS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
            payload=response.model_dump(mode="json"),
            ttl_seconds=settings.player_markets_cache_ttl_seconds,
        )
    return response


@router.get("/leagues")
def list_market_leagues(
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> list[dict[str, object]]:
    return service.list_leagues()


@router.get("/leagues/{league_id}/clubs")
def list_market_league_clubs(
    league_id: str,
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> list[dict[str, object]]:
    return service.list_league_clubs(league_id)


@router.get("/clubs/{club_id}/players", response_model=MarketPlayerListView)
def list_market_club_players(
    club_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerListView:
    return MarketPlayerListView.model_validate(service.list_club_players(club_id, limit=limit))


@router.get("/nationalities")
def list_market_nationalities(
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> list[dict[str, object]]:
    return service.list_nationalities()


@router.get("/nationalities/{country_code}/players", response_model=MarketPlayerListView)
def list_market_nationality_players(
    country_code: str,
    limit: int = Query(default=100, ge=1, le=200),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerListView:
    return MarketPlayerListView.model_validate(service.list_nationality_players(country_code, limit=limit))


@router.get("/national-teams")
def list_market_national_teams(
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> list[dict[str, object]]:
    return service.list_national_teams()


@router.get("/national-teams/{team_id}/eligible-players", response_model=MarketPlayerListView)
def list_market_national_team_eligible_players(
    team_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketPlayerListView:
    return MarketPlayerListView.model_validate(service.list_nationality_players(team_id, limit=limit))


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
    request: Request,
    limit: int = Query(default=5, ge=1, le=25),
    service: MarketPlayerQueryService = Depends(get_market_player_query_service),
) -> MarketMoversView:
    # Movers scans every tradable player's pricing snapshot (a hot-cache lookup
    # per player), so it is expensive on a cold cache. Serve from the shared
    # player-markets response cache when available -- it is invalidated whenever
    # a market changes, so cached movers stay consistent.
    settings = get_optional_app_settings(request.app)
    if settings is not None and settings.api_cache_enabled:
        cached_payload = get_response_cache(request.app).get_json(
            namespace=PLAYER_MARKETS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
        )
        if cached_payload is not None:
            return MarketMoversView.model_validate(cached_payload)
    try:
        result = service.get_market_movers(limit=limit)
    except MarketError as exc:
        raise_market_http_exception(exc)

    response = MarketMoversView.model_validate(result)
    if settings is not None and settings.api_cache_enabled:
        get_response_cache(request.app).set_json(
            namespace=PLAYER_MARKETS_CACHE_NAMESPACE,
            route=request.url.path,
            request=request,
            payload=response.model_dump(mode="json"),
            ttl_seconds=settings.player_markets_cache_ttl_seconds,
        )
    return response


@router.post("/buy", response_model=CreatorTradeView | PlayerSharePurchaseView, status_code=status.HTTP_201_CREATED)
def buy_market_position(
    payload: CreatorTradeRequest | PlayerShareTradeRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trading_user),
) -> CreatorTradeView | PlayerSharePurchaseView:
    if isinstance(payload, CreatorTradeRequest):
        runtime = ensure_gtex_runtime(request.app)
        try:
            trade = runtime.creator_market.buy_shares(
                session,
                buyer=current_user,
                player_id=payload.player_id,
                shares=payload.shares,
                client_ip=_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
            session.commit()
        except GtexError as exc:
            session.rollback()
            raise_gtex_http_exception(exc)
        return CreatorTradeView.model_validate(trade)

    service = PlayerTokenMarketService(
        session,
        event_publisher=getattr(request.app.state, "event_publisher", None),
    )
    try:
        result = service.buy_shares(
            actor=current_user,
            player_id=payload.player_id,
            share_count=payload.share_count,
        )
    except PlayerTokenMarketError as exc:
        raise_player_share_market_http_exception(exc)

    session.commit()
    session.refresh(result["holding"])
    _invalidate_player_markets_cache(request)
    return PlayerSharePurchaseView(
        market=PlayerShareMarketView.model_validate(result["market"]),
        holding=PlayerShareHoldingView.model_validate(result["holding"]),
        transaction_id=result["transaction_id"],
        gross_amount_coin=result["gross_amount_coin"],
        fee_amount_coin=result["fee_amount_coin"],
        net_amount_coin=result["net_amount_coin"],
    )


@router.post("/sell", response_model=CreatorTradeView | PlayerShareSaleView, status_code=status.HTTP_201_CREATED)
def sell_market_position(
    payload: CreatorTradeRequest | PlayerShareTradeRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trading_user),
) -> CreatorTradeView | PlayerShareSaleView:
    if isinstance(payload, CreatorTradeRequest):
        runtime = ensure_gtex_runtime(request.app)
        try:
            trade = runtime.creator_market.sell_shares(
                session,
                seller=current_user,
                player_id=payload.player_id,
                shares=payload.shares,
                client_ip=_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
            session.commit()
        except GtexError as exc:
            session.rollback()
            raise_gtex_http_exception(exc)
        return CreatorTradeView.model_validate(trade)

    service = PlayerTokenMarketService(
        session,
        event_publisher=getattr(request.app.state, "event_publisher", None),
    )
    try:
        result = service.sell_shares(
            actor=current_user,
            player_id=payload.player_id,
            share_count=payload.share_count,
        )
    except PlayerTokenMarketError as exc:
        raise_player_share_market_http_exception(exc)

    session.commit()
    session.refresh(result["holding"])
    _invalidate_player_markets_cache(request)
    return PlayerShareSaleView(
        market=PlayerShareMarketView.model_validate(result["market"]),
        holding=PlayerShareHoldingView.model_validate(result["holding"]),
        transaction_id=result["transaction_id"],
        gross_amount_coin=result["gross_amount_coin"],
        fee_amount_coin=result["fee_amount_coin"],
        net_amount_coin=result["net_amount_coin"],
    )


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
    current_user: User = Depends(get_current_trading_user),
    market_engine: MarketEngine = Depends(get_market_engine),
) -> OfferView:
    try:
        seller_user_id = payload.seller_user_id
        if payload.listing_id:
            listing = market_engine.get_listing(payload.listing_id)
            seller_user_id = listing.seller_user_id
            if payload.asset_id != listing.asset_id:
                raise MarketValidationError("offer target does not match listing")
        offer = market_engine.create_offer(
            asset_id=payload.asset_id,
            seller_user_id=seller_user_id,
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
    current_user: User = Depends(get_current_trading_user),
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
    current_user: User = Depends(get_current_trading_user),
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
    current_user: User = Depends(get_current_trading_user),
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

# Mount under /api/v2 as well.  The market module is registered without
# with_api_alias=True (its combined_router pre-builds the /api mount), so it
# would otherwise miss the /api/v2 alias that every versioned client expects
# (e.g. the Transfer Hub calls /api/v2/market/players) -> 404.
api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(router)

combined_router = APIRouter(tags=["market"])
combined_router.include_router(router)
combined_router.include_router(api_router)
combined_router.include_router(api_v2_router)

router = combined_router
