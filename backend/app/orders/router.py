from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.matching.service import InvalidOrderTransitionError, OrderBookSnapshot
from app.models.user import User
from app.orders.schemas import (
    OrderAcceptedView,
    OrderBookLevelView,
    OrderBookView,
    OrderCreateRequest,
    OrderExecutionSummaryView,
    OrderExecutionView,
    OrderListView,
    OrderView,
)
from app.orders.models import OrderStatus
from app.orders.service import OrderNotFoundError, OrderPlacementError, OrderService, PlayerNotFoundError
from app.wallets.service import LedgerError

router = APIRouter(tags=["orders"])
legacy_router = APIRouter(prefix="/orders")
api_router = APIRouter(prefix="/api/orders")


def _build_order_service(request: Request | None) -> OrderService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return OrderService(event_publisher=request.app.state.event_publisher)
    return OrderService()


def _build_order_view(service: OrderService, session: Session, order) -> OrderView:
    execution_snapshot = service.get_execution_snapshot(session, order_id=order.id)
    return OrderView(
        id=order.id,
        user_id=order.user_id,
        player_id=order.player_id,
        side=order.side,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        max_price=order.max_price,
        currency=order.currency,
        reserved_amount=order.reserved_amount,
        status=order.status,
        hold_transaction_id=order.hold_transaction_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        execution_summary=OrderExecutionSummaryView(
            execution_count=execution_snapshot.execution_count,
            total_notional=execution_snapshot.total_notional,
            average_price=execution_snapshot.average_price,
            last_executed_at=execution_snapshot.last_executed_at,
            executions=[OrderExecutionView.model_validate(item) for item in execution_snapshot.executions],
        ),
    )


def _build_order_book_view(order_book: OrderBookSnapshot) -> OrderBookView:
    return OrderBookView(
        player_id=order_book.player_id,
        bids=[
            OrderBookLevelView(price=level.price, quantity=level.quantity, order_count=level.order_count)
            for level in order_book.bids
        ],
        asks=[
            OrderBookLevelView(price=level.price, quantity=level.quantity, order_count=level.order_count)
            for level in order_book.asks
        ],
        generated_at=order_book.generated_at,
    )


@legacy_router.get("", response_model=OrderListView)
@api_router.get("", response_model=OrderListView)
def list_orders(
    status: list[OrderStatus] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> OrderListView:
    service = _build_order_service(request)
    orders, total = service.list_orders(
        session,
        user=current_user,
        statuses=status,
        limit=limit,
        offset=offset,
    )
    return OrderListView(
        items=[_build_order_view(service, session, order) for order in orders],
        limit=limit,
        offset=offset,
        total=total,
    )


@legacy_router.post("", response_model=OrderAcceptedView, status_code=status.HTTP_201_CREATED)
@api_router.post("", response_model=OrderAcceptedView, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: OrderCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> OrderAcceptedView:
    service = _build_order_service(request)
    try:
        order = service.place_order(
            session,
            user=current_user,
            player_id=payload.player_id,
            side=payload.side,
            quantity=payload.quantity,
            max_price=payload.max_price,
        )
        session.commit()
        session.refresh(order)
    except PlayerNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidOrderTransitionError, LedgerError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrderPlacementError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OrderAcceptedView.model_validate(_build_order_view(service, session, order))


@legacy_router.get("/book/{player_id}", response_model=OrderBookView)
@api_router.get("/book/{player_id}", response_model=OrderBookView)
def get_order_book(
    player_id: str,
    session: Session = Depends(get_session),
    request: Request = None,
) -> OrderBookView:
    service = _build_order_service(request)
    order_book = service.get_order_book(session, player_id=player_id)
    return _build_order_book_view(order_book)


@legacy_router.get("/{order_id}", response_model=OrderView)
@api_router.get("/{order_id}", response_model=OrderView)
def get_order_detail(
    order_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> OrderView:
    service = _build_order_service(request)
    try:
        order = service.get_order(session, order_id=order_id, user=current_user)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _build_order_view(service, session, order)


@legacy_router.post("/{order_id}/cancel", response_model=OrderView)
@api_router.post("/{order_id}/cancel", response_model=OrderView)
def cancel_order(
    order_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> OrderView:
    service = _build_order_service(request)
    try:
        order = service.cancel_order(session, order_id=order_id, user=current_user)
        session.commit()
        session.refresh(order)
    except OrderNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidOrderTransitionError, LedgerError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OrderPlacementError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _build_order_view(service, session, order)


router.include_router(legacy_router)
router.include_router(api_router)
