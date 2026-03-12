from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.creator_requests import CreatorProfileCreateRequest, CreatorProfileUpdateRequest
from backend.app.schemas.creator_responses import CreatorCompetitionView, CreatorProfileView, CreatorSummaryView
from backend.app.services.referral_orchestrator import ReferralActionError, ReferralOrchestrator, get_referral_orchestrator

router = APIRouter(prefix="/api/creators", tags=["creators"])


@router.post("/profile", response_model=CreatorProfileView, status_code=status.HTTP_201_CREATED)
def create_creator_profile(
    payload: CreatorProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        return CreatorProfileView.model_validate(
            orchestrator.create_creator_profile(current_user=current_user, payload=payload)
        )
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.patch("/profile", response_model=CreatorProfileView)
def update_creator_profile(
    payload: CreatorProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        return CreatorProfileView.model_validate(
            orchestrator.update_creator_profile(current_user=current_user, payload=payload)
        )
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/profile/me", response_model=CreatorProfileView)
def get_my_creator_profile(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        return CreatorProfileView.model_validate(orchestrator.get_my_creator_profile(current_user=current_user))
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/me/summary", response_model=CreatorSummaryView)
def get_my_creator_summary(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorSummaryView:
    try:
        return orchestrator.get_creator_summary(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/me/competitions", response_model=list[CreatorCompetitionView])
def get_my_creator_competitions(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> list[CreatorCompetitionView]:
    try:
        competitions = orchestrator.get_creator_competitions(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc
    return [CreatorCompetitionView.model_validate(competition) for competition in competitions]


@router.get("/{handle}", response_model=CreatorProfileView)
def get_creator_profile(
    handle: str,
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        return CreatorProfileView.model_validate(orchestrator.get_creator_by_handle(handle))
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


def _to_http_error(exc: ReferralActionError) -> HTTPException:
    reason = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if reason in {"creator_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif reason in {"creator_handle_taken", "creator_profile_exists"}:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=reason)
