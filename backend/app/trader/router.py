from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_trader_user, get_session
from app.models.trader import TraderMarket, TraderWatchlist
from app.models.user import User
from app.trader.schemas import (
    TotpSetupView,
    TraderBalanceView,
    TraderDashboardView,
    TraderDepositRequest,
    TraderDepositResultView,
    TraderDisputeCreateRequest,
    TraderDisputeView,
    TraderMarketView,
    TraderOrderCreateRequest,
    TraderOrderBookView,
    TraderOrderView,
    TraderOverviewView,
    TraderP2POfferCreateRequest,
    TraderP2POfferView,
    TraderProfileView,
    TraderProcurementCreateRequest,
    TraderProcurementQuoteRequest,
    TraderProcurementQuoteView,
    TraderProcurementView,
    TraderQuoteRequest,
    TraderQuoteView,
    TraderSettlementView,
    TraderWatchlistCreateRequest,
    TraderWatchlistView,
    TraderWithdrawalRequest,
    TraderWithdrawalResultView,
)
from app.trader.service import (
    TraderAccessError,
    TraderFinancialBalanceUnavailableError,
    TraderMarketNotFoundError,
    TraderResourceNotFoundError,
    TraderService,
)

router = APIRouter(tags=["trader"])
api_router = APIRouter(prefix="/api/trader", tags=["trader"])


def _service(session: Session) -> TraderService:
    return TraderService(session)


@api_router.get("/overview", response_model=TraderOverviewView)
def trader_overview(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderOverviewView:
    try:
        return TraderOverviewView.model_validate(_service(session).overview(current_user))
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/profile", response_model=TraderProfileView)
def trader_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderProfileView:
    try:
        return TraderProfileView.model_validate(_service(session).profile(current_user))
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/dashboard", response_model=TraderDashboardView)
def trader_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderDashboardView:
    try:
        return TraderDashboardView.model_validate(_service(session).dashboard(current_user))
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/balance", response_model=TraderBalanceView)
def trader_balance(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderBalanceView:
    try:
        return TraderBalanceView.model_validate(_service(session).balance(current_user))
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@api_router.get("/markets", response_model=list[TraderMarketView])
def list_markets(
    session: Session = Depends(get_session), _: User = Depends(get_current_trader_user)
) -> list[TraderMarketView]:
    return [TraderMarketView.model_validate(item) for item in _service(session).list_markets()]


@api_router.get("/order-book/{market_id}", response_model=TraderOrderBookView)
def get_order_book(
    market_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_trader_user),
) -> TraderOrderBookView:
    try:
        return TraderOrderBookView.model_validate(_service(session).order_book(market_id))
    except TraderMarketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@api_router.get("/orders", response_model=list[TraderOrderView])
def list_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> list[TraderOrderView]:
    try:
        return [
            TraderOrderView.model_validate(item)
            for item in _service(session).list_orders(current_user, status_filter=status_filter)
        ]
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@api_router.get("/orders/{order_id}", response_model=TraderOrderView)
def get_order(
    order_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderOrderView:
    try:
        return TraderOrderView.model_validate(_service(session).get_order(current_user, order_id=order_id))
    except TraderResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@api_router.post("/quote", response_model=TraderQuoteView)
def request_quote(
    payload: TraderQuoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderQuoteView:
    try:
        return TraderQuoteView.model_validate(
            _service(session).quote_order(
                current_user,
                market_id=payload.market_id,
                side=payload.side,
                amount=payload.amount,
                currency=payload.currency,
            )
        )
    except TraderMarketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


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
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    session.commit()
    return TraderOrderView.model_validate(order)


@api_router.post("/orders/{order_id}/cancel", response_model=TraderOrderView)
def cancel_order(
    order_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderOrderView:
    try:
        order = _service(session).cancel_order(current_user, order_id=order_id)
    except TraderResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    return TraderOrderView.model_validate(order)


@api_router.get("/disputes", response_model=list[TraderDisputeView])
def list_disputes(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> list[TraderDisputeView]:
    return [TraderDisputeView.model_validate(item) for item in _service(session).list_disputes(current_user)]


@api_router.get("/disputes/{dispute_id}", response_model=TraderDisputeView)
def get_dispute(
    dispute_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderDisputeView:
    try:
        return TraderDisputeView.model_validate(_service(session).get_dispute(current_user, dispute_id=dispute_id))
    except TraderResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@api_router.post("/disputes", response_model=TraderDisputeView, status_code=status.HTTP_201_CREATED)
def file_dispute(
    payload: TraderDisputeCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderDisputeView:
    try:
        dispute = _service(session).file_dispute(current_user, order_id=payload.order_id, reason=payload.reason)
    except TraderResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    return TraderDisputeView.model_validate(dispute)


@api_router.get("/settlements", response_model=list[TraderSettlementView])
def list_settlements(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> list[TraderSettlementView]:
    return [TraderSettlementView.model_validate(item) for item in _service(session).list_settlements(current_user)]


@api_router.get("/settlements/{settlement_id}", response_model=TraderSettlementView)
def get_settlement(
    settlement_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderSettlementView:
    try:
        return TraderSettlementView.model_validate(
            _service(session).get_settlement(current_user, settlement_id=settlement_id)
        )
    except TraderResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@api_router.post("/deposit", response_model=TraderDepositResultView, status_code=status.HTTP_202_ACCEPTED)
def initiate_deposit(
    payload: TraderDepositRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderDepositResultView:
    try:
        result = _service(session).initiate_deposit(
            current_user,
            amount=payload.amount,
            currency=payload.currency,
            method=payload.method,
            proof_attachment_id=payload.proof_attachment_id,
        )
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    session.commit()
    return TraderDepositResultView.model_validate(result)


@api_router.post("/withdraw", response_model=TraderWithdrawalResultView, status_code=status.HTTP_202_ACCEPTED)
def request_withdrawal(
    payload: TraderWithdrawalRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderWithdrawalResultView:
    try:
        result = _service(session).request_withdrawal(
            current_user,
            amount=payload.amount,
            currency=payload.currency,
            method=payload.method,
            destination_ref=payload.destination_ref,
        )
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    session.commit()
    return TraderWithdrawalResultView.model_validate(result)


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
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    session.commit()
    return TraderP2POfferView.model_validate(offer)


@api_router.post("/procurements/quote", response_model=TraderProcurementQuoteView)
def quote_procurement(
    payload: TraderProcurementQuoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderProcurementQuoteView:
    try:
        quote = _service(session).quote_wholesale_procurement(
            current_user,
            amount=payload.amount,
            fee_bps=payload.fee_bps,
            unit=payload.unit,
        )
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return TraderProcurementQuoteView(
        gross_amount=quote.gross_amount,
        fee_amount=quote.fee_amount,
        net_amount=quote.net_amount,
        unit=quote.unit,
    )


@api_router.post("/procurements", response_model=TraderProcurementView, status_code=status.HTTP_201_CREATED)
def create_procurement(
    payload: TraderProcurementCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_trader_user),
) -> TraderProcurementView:
    try:
        topup = _service(session).request_wholesale_procurement(
            current_user,
            amount=payload.amount,
            fee_bps=payload.fee_bps,
            unit=payload.unit,
            notes=payload.notes,
        )
    except TraderFinancialBalanceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraderAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    session.commit()
    return TraderProcurementView.model_validate(topup)


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
    return [TraderWatchlistView(id=watch.id, market=TraderMarketView.model_validate(market)) for watch, market in rows]


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
