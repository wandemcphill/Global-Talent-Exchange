from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.user import User
from backend.app.services.payment_gateway_service import PaymentGatewayError, PaymentGatewayService
from backend.app.integrations.payments.schemas import (
    PaymentMethodView,
    PaymentOrderCreateRequest,
    PaymentOrderView,
    PaymentQuoteRequest,
    PaymentQuoteView,
)


router = APIRouter(prefix="/integrations/payments", tags=["payments"])


def _service(request: Request, session: Session) -> PaymentGatewayService:
    return PaymentGatewayService(session=session, settings=request.app.state.settings)


@router.get("/methods", response_model=list[PaymentMethodView])
def list_payment_methods(request: Request, session: Session = Depends(get_session)) -> list[PaymentMethodView]:
    methods = _service(request, session).list_methods()
    return [
        PaymentMethodView(
            method_key=method.method_key,
            display_name=method.display_name,
            provider_key=method.provider_key,
            method_group=method.method_group,
            unit=method.unit,
            deposits_enabled=method.deposits_enabled,
            withdrawals_enabled=method.withdrawals_enabled,
            is_live=method.is_live,
            maintenance_message=method.maintenance_message,
        )
        for method in methods
    ]


@router.post("/quote", response_model=PaymentQuoteView)
def quote_payment(
    payload: PaymentQuoteRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> PaymentQuoteView:
    service = _service(request, session)
    try:
        quote = service.quote_deposit(
            amount=payload.amount,
            input_unit=payload.input_unit,
            provider_key=payload.provider_key,
            method_key=payload.method_key,
            unit=payload.unit,
        )
    except PaymentGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PaymentQuoteView(
        amount_fiat=quote.amount_fiat,
        gross_amount=quote.gross_amount,
        fee_amount=quote.fee_amount,
        net_amount=quote.net_amount,
        currency_code=quote.currency_code,
        rate_value=quote.rate_value,
        rate_direction=quote.rate_direction.value if hasattr(quote.rate_direction, "value") else str(quote.rate_direction),
        unit=quote.unit,
        processor_mode=quote.processor_mode,
        payout_channel=quote.payout_channel,
        provider_key=quote.provider_key,
        source_scope=quote.source_scope,
    )


@router.post("/orders", response_model=PaymentOrderView, status_code=status.HTTP_201_CREATED)
def create_payment_order(
    payload: PaymentOrderCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PaymentOrderView:
    service = _service(request, session)
    try:
        order = service.create_purchase_order(
            user=user,
            amount=payload.amount,
            input_unit=payload.input_unit,
            provider_key=payload.provider_key,
            method_key=payload.method_key,
            unit=payload.unit,
            provider_reference=payload.provider_reference,
            notes=payload.notes,
        )
    except PaymentGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    return PaymentOrderView(
        order_id=order.id,
        reference=order.reference,
        status=order.status.value if hasattr(order.status, "value") else str(order.status),
        provider_key=order.provider_key,
        unit=order.unit,
        gross_amount=order.gross_amount,
        net_amount=order.net_amount,
        currency_code=order.currency_code,
        metadata={
            "provider_reference": order.provider_reference,
            "processor_mode": order.processor_mode,
            "payout_channel": order.payout_channel,
        },
    )


__all__ = ["router"]
