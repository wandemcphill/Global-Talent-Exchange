from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.user import User
from backend.app.wallets.schemas import PaymentEventCreate, PaymentEventView, WalletAccountBalance
from backend.app.wallets.service import LedgerError, WalletService

router = APIRouter(prefix="/wallets", tags=["wallets"])


def _build_wallet_service(request: Request | None) -> WalletService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return WalletService(event_publisher=request.app.state.event_publisher)
    return WalletService()


@router.get("/accounts", response_model=list[WalletAccountBalance])
def list_wallet_accounts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[WalletAccountBalance]:
    service = _build_wallet_service(request)
    accounts = service.list_accounts_for_user(session, current_user)
    return [
        WalletAccountBalance(
            id=account.id,
            code=account.code,
            label=account.label,
            unit=account.unit,
            kind=account.kind,
            allow_negative=account.allow_negative,
            is_active=account.is_active,
            balance=service.get_balance(session, account),
        )
        for account in accounts
    ]


@router.post("/payment-events", response_model=PaymentEventView, status_code=status.HTTP_201_CREATED)
def create_payment_event(
    payload: PaymentEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> PaymentEventView:
    service = _build_wallet_service(request)
    try:
        payment_event = service.create_payment_event(
            session,
            user=current_user,
            provider=payload.provider,
            provider_reference=payload.provider_reference,
            amount=payload.amount,
            pack_code=payload.pack_code,
        )
        session.commit()
        session.refresh(payment_event)
    except LedgerError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PaymentEventView.model_validate(payment_event)
