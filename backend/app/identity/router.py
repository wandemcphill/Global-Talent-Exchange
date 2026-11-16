from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.coin_traders.service import CoinTraderService
from app.identity.providers.didit import IdentityProviderConfigurationError
from app.identity.service import (
    IdentityVerificationError,
    IdentityVerificationIdempotencyError,
    IdentityVerificationNotFoundError,
    IdentityVerificationPermissionError,
    IdentityVerificationService,
    IdentityVerificationSignatureError,
    IdentityVerificationValidationError,
    _sanitize_checks_summary,
)
from app.models.coin_trader import CoinTraderProfile
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
    if isinstance(exc, IdentityProviderConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
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
        record = service.initiate_trader_verification(
            actor=current_user,
            provider_name=payload.provider,
            verification_type=payload.verification_type,
            callback_url=payload.callback_url,
        )
        metadata = dict(record.metadata_json or {})
        handoff_url = metadata.pop("handoff_url", None)
        return CoinTraderVerificationSessionView(
            session_id=record.provider_session_id or "",
            provider=record.provider,
            reference=record.provider_reference or "",
            handoff_url=handoff_url,
            verification_type=record.verification_type,
            status=record.status,
            expires_at=record.expires_at,
            metadata=metadata,
        )
    except (IdentityVerificationError, IdentityProviderConfigurationError) as exc:
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
    record = service.get_latest_trader_verification(actor=current_user)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trader identity verification has been started.",
        )
    return CoinTraderVerificationStatusView(
        id=record.id,
        user_id=record.user_id,
        trader_profile_id=record.trader_profile_id,
        provider=record.provider,
        provider_reference=record.provider_reference,
        verification_type=record.verification_type,
        status=record.status,
        decision=record.decision,
        rejection_reason=record.rejection_reason,
        checks_summary=dict(record.checks_summary_json or {}),
        initiated_at=record.initiated_at,
        verified_at=record.verified_at,
    )


@router.post("/api/kyc/webhooks/{provider_name}")
async def handle_provider_webhook(
    provider_name: str,
    request: Request,
    service: IdentityVerificationService = Depends(_service),
) -> dict[str, Any]:
    raw_payload = await request.body()
    headers = dict(request.headers)
    try:
        return service.process_provider_webhook(
            provider_name=provider_name,
            payload_bytes=raw_payload,
            headers=headers,
        )
    except (IdentityVerificationError, IdentityProviderConfigurationError) as exc:
        if isinstance(exc, IdentityVerificationSignatureError):
            logger.warning("Webhook signature verification failed for provider %s", provider_name)
        else:
            logger.error("Webhook processing failed for provider %s: %s", provider_name, exc)
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
    records = service.list_verification_records(
        user_id=user_id,
        domain=domain,
        status=record_status,
        limit=limit,
        offset=offset,
    )
    user_ids = {record.user_id for record in records if record.user_id}
    profile_ids = {record.trader_profile_id for record in records if record.trader_profile_id}
    users_by_id = (
        {user.id: user for user in service.session.scalars(select(User).where(User.id.in_(user_ids))).all()}
        if user_ids
        else {}
    )
    profiles_by_id = (
        {
            profile.id: profile
            for profile in service.session.scalars(
                select(CoinTraderProfile).where(CoinTraderProfile.id.in_(profile_ids))
            ).all()
        }
        if profile_ids
        else {}
    )
    return [
        IdentityVerificationRecordAdminView(
            id=record.id,
            user_id=record.user_id,
            user_email=users_by_id[record.user_id].email if record.user_id in users_by_id else None,
            trader_profile_id=record.trader_profile_id,
            trader_display_name=(
                profiles_by_id[record.trader_profile_id].display_name
                if record.trader_profile_id in profiles_by_id
                else None
            ),
            provider=record.provider,
            provider_session_id=record.provider_session_id,
            provider_reference=record.provider_reference,
            verification_type=record.verification_type,
            status=record.status,
            decision=record.decision,
            rejection_reason=record.rejection_reason,
            checks_summary=_sanitize_checks_summary(record.checks_summary_json),
            evidence_fingerprint=record.evidence_fingerprint,
            initiated_at=record.initiated_at,
            verified_at=record.verified_at,
            history=list(record.history_json or []),
        )
        for record in records
    ]


@admin_router.post("/api/admin/coin-traders/{profile_id}/suspend")
def admin_suspend_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminActionRequest | None = None,
    current_admin: User = Depends(get_current_admin),
    service: CoinTraderService = Depends(_coin_trader_service),
) -> dict[str, Any]:
    notes = payload.notes if payload else None
    reason = payload.reason if payload else "Administrative suspension"
    profile_view = service.suspend_trader(
        profile_id=profile_id, admin=current_admin, note=f"{reason}: {notes}" if notes else reason
    )
    return {"status": "suspended", "profile": profile_view}


@admin_router.post("/api/admin/coin-traders/{profile_id}/reinstate")
def admin_reinstate_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminActionRequest | None = None,
    current_admin: User = Depends(get_current_admin),
    service: CoinTraderService = Depends(_coin_trader_service),
) -> dict[str, Any]:
    notes = payload.notes if payload else None
    profile_view = service.reinstate_trader(profile_id=profile_id, admin=current_admin, note=notes)
    return {"status": "reinstated", "profile": profile_view}


__all__ = ["admin_router", "router"]
