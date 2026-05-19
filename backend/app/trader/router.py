from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_trader_user, get_session
from app.models.trader import TraderMarket, TraderWatchlist
from app.models.user import User
from app.trader.schemas import (
    TotpSetupView,
    TraderMarketView,
    TraderOrderCreateRequest,
    TraderOrderView,
    TraderOverviewView,
    TraderP2POfferCreateRequest,
    TraderP2POfferView,
    TraderWatchlistCreateRequest,
    TraderWatchlistView,
)
from app.trader.service import TraderAccessError, TraderMarketNotFoundError, TraderService

router = APIRouter(tags=["trader"])
api_router = APIRouter(prefix="/api/v2/trader", tags=["trader"])


def _service(session: Session) -> TraderService:
    return TraderService(session)


@api_router.get("/overview", response_model=TraderOverviewView)
def trader_overview(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderOverviewView:
    try:
        return TraderOverviewView.model_validate(_service(session).overview(current_user))
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/markets", response_model=list[TraderMarketView])
def list_markets(session: Session = Depends(get_session), _: User = Depends(get_current_trader_user)) -> list[TraderMarketView]:
    return [TraderMarketView.model_validate(item) for item in _service(session).list_markets()]


@api_router.post("/orders", response_model=TraderOrderView, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: TraderOrderCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderOrderView:
    try:
        order = _service(session).place_order(
            current_user,
            market_id=payload.market_id,
            side=payload.side,
            quantity=payload.quantity,
            limit_price=payload.limit_price,
        )
    except TraderMarketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    return TraderOrderView.model_validate(order)


@api_router.post("/p2p", response_model=TraderP2POfferView, status_code=status.HTTP_201_CREATED)
def create_p2p_offer(
    payload: TraderP2POfferCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderP2POfferView:
    try:
        offer = _service(session).create_p2p_offer(
            current_user,
            market_id=payload.market_id,
            side=payload.side,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            preferred_currency=payload.preferred_currency,
        )
    except TraderMarketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    return TraderP2POfferView.model_validate(offer)


@api_router.get("/watchlist", response_model=list[TraderWatchlistView])
def list_watchlist(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> list[TraderWatchlistView]:
    rows = session.execute(
        select(TraderWatchlist, TraderMarket)
        .join(TraderMarket, TraderMarket.id == TraderWatchlist.market_id)
        .where(TraderWatchlist.user_id == current_user.id)
        .order_by(TraderWatchlist.created_at.desc())
    ).all()
    return [
        TraderWatchlistView(id=watch.id, market=TraderMarketView.model_validate(market))
        for watch, market in rows
    ]


@api_router.post("/watchlist", response_model=TraderWatchlistView, status_code=status.HTTP_201_CREATED)
def add_watchlist(
    payload: TraderWatchlistCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderWatchlistView:
    try:
        watch = _service(session).add_watchlist(current_user, market_id=payload.market_id)
    except TraderMarketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    market = session.get(TraderMarket, watch.market_id)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trader market not found.")
    session.commit()
    return TraderWatchlistView(id=watch.id, market=TraderMarketView.model_validate(market))


@api_router.post("/security/totp/setup", response_model=TotpSetupView)
def setup_totp(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TotpSetupView:
    return TotpSetupView.model_validate(_service(session).totp_setup(current_user))


router.include_router(api_router)
