from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.referral_requests import (
    AttributionCaptureRequest,
    ShareCodeCreateRequest,
    ShareCodeRedeemRequest,
    ShareCodeUpdateRequest,
)
from app.schemas.referral_responses import (
    AttributionView,
    ReferralInviteView,
    ReferralRewardView,
    ReferralSummaryView,
    ShareCodeRedeemResponse,
    ShareCodeView,
)
from app.services.referral_orchestrator import ReferralActionError, ReferralOrchestrator, get_referral_orchestrator

router = APIRouter(prefix="/api/referrals", tags=["referrals"])


@router.post("/share-codes", response_model=ShareCodeView, status_code=status.HTTP_201_CREATED)
def create_share_code(
    payload: ShareCodeCreateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> ShareCodeView:
    try:
        return ShareCodeView.model_validate(orchestrator.create_share_code(current_user=current_user, payload=payload))
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/share-codes/me", response_model=list[ShareCodeView])
def list_my_share_codes(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> list[ShareCodeView]:
    return [ShareCodeView.model_validate(code) for code in orchestrator.list_my_share_codes(current_user=current_user)]


@router.patch("/share-codes/{share_code_id}", response_model=ShareCodeView)
def update_share_code(
    share_code_id: str,
    payload: ShareCodeUpdateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> ShareCodeView:
    try:
        return ShareCodeView.model_validate(
            orchestrator.update_share_code(current_user=current_user, share_code_id=share_code_id, payload=payload)
        )
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.post("/share-codes/{code}/redeem", response_model=ShareCodeRedeemResponse)
def redeem_share_code(
    code: str,
    payload: ShareCodeRedeemRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> ShareCodeRedeemResponse:
    try:
        return orchestrator.redeem_share_code(current_user=current_user, code=code, payload=payload)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.post("/attribution", response_model=AttributionView)
def capture_referral_attribution(
    payload: AttributionCaptureRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> AttributionView:
    try:
        return orchestrator.capture_attribution(current_user=current_user, payload=payload)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/me/summary", response_model=ReferralSummaryView)
def get_my_referral_summary(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> ReferralSummaryView:
    return orchestrator.get_my_referral_summary(current_user=current_user)


@router.get("/me/rewards", response_model=list[ReferralRewardView])
def get_my_referral_rewards(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> list[ReferralRewardView]:
    return orchestrator.get_my_rewards(current_user=current_user)


@router.get("/me/invites", response_model=list[ReferralInviteView])
def get_my_referral_invites(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> list[ReferralInviteView]:
    return orchestrator.get_my_invites(current_user=current_user)


def _to_http_error(exc: ReferralActionError) -> HTTPException:
    reason = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if reason in {"share_code_not_found", "creator_not_found", "attribution_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif reason in {"self_referral_blocked", "share_code_inactive", "share_code_expired", "share_code_exhausted", "share_code_not_started"}:
        status_code = status.HTTP_409_CONFLICT
    elif reason in {"share_code_forbidden"}:
        status_code = status.HTTP_403_FORBIDDEN
    return HTTPException(status_code=status_code, detail=reason)
