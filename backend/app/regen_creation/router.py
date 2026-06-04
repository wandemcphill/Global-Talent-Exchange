from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.regen_creation.schemas import RequestSonCreateRequest, RequestSonPreviewRequest, RequestSonPreviewView
from app.regen_creation.schemas import RegenCreationOrderListView, RegenCreationOrderView, RequestSonOptionsView
from app.regen_creation.service import (
    RegenCreationConflictError,
    RegenCreationNotFoundError,
    RegenCreationPaymentError,
    RegenCreationPermissionError,
    RegenCreationService,
    RegenCreationValidationError,
)

router = APIRouter(prefix="/regens", tags=["regen-creation"])


def _service(session: Session, request: Request | None = None) -> RegenCreationService:
    event_publisher = None
    if request is not None and hasattr(request.app.state, "event_publisher"):
        event_publisher = request.app.state.event_publisher
    return RegenCreationService(session=session, event_publisher=event_publisher)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, RegenCreationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RegenCreationPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, RegenCreationConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, RegenCreationPaymentError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, RegenCreationValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/request-son/options", response_model=RequestSonOptionsView)
def request_son_options(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RequestSonOptionsView:
    try:
        return _service(session, request).request_son_options(current_user)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.post("/request-son/preview", response_model=RequestSonPreviewView)
def preview_request_son(
    payload: RequestSonPreviewRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RequestSonPreviewView:
    try:
        return _service(session, request).preview_request_son(actor=current_user, payload=payload)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.post("/request-son", response_model=RegenCreationOrderView, status_code=status.HTTP_201_CREATED)
def request_son(
    payload: RequestSonCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session, request).create_request_son_order(actor=current_user, payload=payload)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.get("/creation-orders", response_model=RegenCreationOrderListView)
def list_creation_orders(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderListView:
    try:
        return _service(session, request).list_orders(actor=current_user, limit=limit)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.get("/creation-orders/{order_id}", response_model=RegenCreationOrderView)
def get_creation_order(
    order_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        return _service(session, request).get_order(actor=current_user, order_id=order_id)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.post("/creation-orders/{order_id}/pay-with-wallet", response_model=RegenCreationOrderView)
def pay_with_wallet(
    order_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session, request).pay_with_wallet(actor=current_user, order_id=order_id)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/creation-orders/{order_id}/generate-after-payment", response_model=RegenCreationOrderView)
def generate_after_payment(
    order_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session, request).generate_after_payment(actor=current_user, order_id=order_id)
        session.commit()
        return result
    except RegenCreationPaymentError as exc:
        if getattr(exc, "terminal", False):
            session.commit()
        else:
            session.rollback()
        _raise_http_error(exc)
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/creation-orders/{order_id}/cancel", response_model=RegenCreationOrderView)
def cancel_creation_order(
    order_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session, request).cancel_order(actor=current_user, order_id=order_id)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)
