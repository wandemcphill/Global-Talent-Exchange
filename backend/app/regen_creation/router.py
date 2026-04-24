from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.regen_creation.schemas import RequestSonCreateRequest
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


def _service(session: Session) -> RegenCreationService:
    return RegenCreationService(session=session)


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
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RequestSonOptionsView:
    try:
        return _service(session).request_son_options(current_user)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.post("/request-son", response_model=RegenCreationOrderView, status_code=status.HTTP_201_CREATED)
def request_son(
    payload: RequestSonCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session).create_request_son_order(actor=current_user, payload=payload)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.get("/creation-orders", response_model=RegenCreationOrderListView)
def list_creation_orders(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderListView:
    try:
        return _service(session).list_orders(actor=current_user, limit=limit)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.get("/creation-orders/{order_id}", response_model=RegenCreationOrderView)
def get_creation_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        return _service(session).get_order(actor=current_user, order_id=order_id)
    except Exception as exc:  # pragma: no cover - mapped below
        _raise_http_error(exc)


@router.post("/creation-orders/{order_id}/pay-with-wallet", response_model=RegenCreationOrderView)
def pay_with_wallet(
    order_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session).pay_with_wallet(actor=current_user, order_id=order_id)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)


@router.post("/creation-orders/{order_id}/generate-after-payment", response_model=RegenCreationOrderView)
def generate_after_payment(
    order_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RegenCreationOrderView:
    try:
        result = _service(session).generate_after_payment(actor=current_user, order_id=order_id)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        _raise_http_error(exc)
