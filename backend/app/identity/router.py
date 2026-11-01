from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.coin_traders.service import CoinTraderService
from app.identity.service import (
    IdentityVerificationError,
    IdentityVerificationIdempotencyError,
    IdentityVerificationNotFoundError,
    IdentityVerificationPermissionError,
    IdentityVerificationService,
    IdentityVerificationSignatureError,
    IdentityVerificationValidationError,
)
from app.models.user import User
from app.schemas.coin_trader_verification import (
    CoinTraderAdminActionRequest,
    CoinTraderVerificationInitiateRequest,
    CoinTraderVerificationSessionView,
    CoinTraderVerificationStatusView,
    IdentityVerificationRecordAdminView,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["identity-verification"])
admin_router = APIRouter(tags=["admin-identity-verification"])


def _service(session: Session = Depends(get_session)) -> IdentityVerificationService:
    return IdentityVerificationService(session)


def _coin_trader_service(session: Session = Depends(get_session)) -> CoinTraderService:
    return CoinTraderService(session)


def _raise_identity_http(exc: Exception) -> None:
    if isinstance(exc, IdentityVerificationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, IdentityVerificationPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, IdentityVerificationSignatureError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if isinstance(exc, IdentityVerificationIdempotencyError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, IdentityVerificationValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, IdentityVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.post(
    "/api/coin-traders/verification/initiate",
    response_model=CoinTraderVerificationSessionView,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/api/kyc/trader/initiate",
    response_model=CoinTraderVerificationSessionView,
    status_code=status.HTTP_201_CREATED,
)
def initiate_trader_verification(
    payload: CoinTraderVerificationInitiateRequest,
    current_user: User = Depends(get_current_user),
    service: IdentityVerificationService = Depends(_service),
) -> CoinTraderVerificationSessionView:
    try:
        return service.initiate_trader_verification(
            user_id=current_user.id,
            provider_name=payload.provider,
            request_payload=payload.model_dump(),
            callback_url=payload.callback_url,
        )
    except IdentityVerificationError as exc:
        _raise_identity_http(exc)


@router.get(
    "/api/coin-traders/verification/status",
    response_model=CoinTraderVerificationStatusView,
)
@router.get(
    "/api/kyc/trader/status",
    response_model=CoinTraderVerificationStatusView,
)
def get_trader_verification_status(
    current_user: User = Depends(get_current_user),
    service: IdentityVerificationService = Depends(_service),
) -> CoinTraderVerificationStatusView:
    try:
        return service.get_trader_verification_status(user_id=current_user.id)
    except IdentityVerificationError as exc:
        _raise_identity_http(exc)


@router.post("/api/kyc/webhooks/{provider_name}")
async def handle_provider_webhook(
    provider_name: str,
    request: Request,
    service: IdentityVerificationService = Depends(_service),
) -> dict[str, Any]:
    raw_payload = await request.body()
    headers = dict(request.headers)
    try:
        result = service.process_provider_webhook(
            provider_name=provider_name,
            raw_payload=raw_payload,
            headers=headers,
        )
        return {
            "status": "success",
            "provider": provider_name,
            "session_id": result.session_id,
            "decision": result.decision,
            "idempotent": result.idempotent,
            "user_id": result.user_id,
        }
    except IdentityVerificationSignatureError as exc:
        logger.warning("Webhook signature verification failed for provider %s: %s", provider_name, exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature") from exc
    except IdentityVerificationError as exc:
        logger.error("Webhook processing error for provider %s: %s", provider_name, exc)
        _raise_identity_http(exc)


@admin_router.get(
    "/api/admin/coin-traders/verification/records",
    response_model=list[IdentityVerificationRecordAdminView],
)
@admin_router.get(
    "/api/admin/kyc/records",
    response_model=list[IdentityVerificationRecordAdminView],
)
def list_verification_records(
    user_id: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    record_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_admin: User = Depends(get_current_admin),
    service: IdentityVerificationService = Depends(_service),
) -> list[IdentityVerificationRecordAdminView]:
    _ = current_admin
    return service.list_verification_records(
        user_id=user_id,
        domain=domain,
        status=record_status,
        limit=limit,
        offset=offset,
    )


@admin_router.post("/api/admin/coin-traders/{profile_id}/suspend")
def admin_suspend_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminActionRequest | None = None,
    current_admin: User = Depends(get_current_admin),
    service: CoinTraderService = Depends(_coin_trader_service),
) -> dict[str, Any]:
    note = payload.note if payload else None
    reason = payload.reason if payload else "Administrative suspension"
    profile_view = service.suspend_trader(profile_id=profile_id, admin=current_admin, note=f"{reason}: {note}" if note else reason)
    return {"status": "suspended", "profile": profile_view}


@admin_router.post("/api/admin/coin-traders/{profile_id}/reinstate")
def admin_reinstate_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminActionRequest | None = None,
    current_admin: User = Depends(get_current_admin),
    service: CoinTraderService = Depends(_coin_trader_service),
) -> dict[str, Any]:
    note = payload.note if payload else None
    profile_view = service.reinstate_trader(profile_id=profile_id, admin=current_admin, note=note)
    return {"status": "reinstated", "profile": profile_view}


__all__ = ["admin_router", "router"]
