from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.referral_admin import (
    AttributionChainEntryView,
    CreatorAdminSummaryView,
    CreatorRewardFreezeRequest,
    PendingRewardView,
    ReferralAdminDashboardView,
    ReferralFlagView,
    RewardReviewDecisionView,
    RewardReviewRequest,
    ShareCodeModerationRequest,
    ShareCodeUsageSummaryView,
)
from app.schemas.referral_analytics import CreatorLeaderboardResponse, ReferralAnalyticsSummaryView
from app.services.referral_admin_service import ReferralAdminService, get_referral_admin_service
from app.services.referral_orchestrator import ReferralActionError

router = APIRouter(prefix="/api/admin/referrals", tags=["admin-referrals"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    role = getattr(current_user, "role", None)
    role_value = getattr(role, "value", role)
    if role_value != "admin" and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_access_required")
    return current_user


def _to_http_error(exc: ReferralActionError) -> HTTPException:
    reason = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if reason in {"share_code_not_found", "creator_not_found", "reward_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif reason in {"creator_rewards_frozen"}:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=reason)


@router.get("/dashboard", response_model=ReferralAdminDashboardView)
def get_referral_admin_dashboard(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> ReferralAdminDashboardView:
    return admin_service.dashboard()


@router.get("/share-codes", response_model=list[ShareCodeUsageSummaryView])
def list_referral_share_codes(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> list[ShareCodeUsageSummaryView]:
    return admin_service.list_share_codes()


@router.get("/share-codes/{share_code_id}", response_model=ShareCodeUsageSummaryView)
def get_referral_share_code(
    share_code_id: str,
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> ShareCodeUsageSummaryView:
    result = admin_service.get_share_code(share_code_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="share_code_not_found")
    return result


@router.post("/share-codes/{share_code_id}/block", response_model=ShareCodeUsageSummaryView)
def block_referral_share_code(
    share_code_id: str,
    payload: ShareCodeModerationRequest,
    current_user: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> ShareCodeUsageSummaryView:
    try:
        return admin_service.block_share_code(share_code_id=share_code_id, admin_user_id=current_user.id, payload=payload)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/creators", response_model=list[CreatorAdminSummaryView])
def list_referral_creators(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> list[CreatorAdminSummaryView]:
    return admin_service.list_creators()


@router.get("/creators/{creator_id}", response_model=CreatorAdminSummaryView)
def get_referral_creator(
    creator_id: str,
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> CreatorAdminSummaryView:
    result = admin_service.get_creator(creator_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="creator_not_found")
    return result


@router.post("/creators/{creator_id}/reward-freeze", response_model=CreatorAdminSummaryView)
def set_referral_creator_reward_freeze(
    creator_id: str,
    payload: CreatorRewardFreezeRequest,
    current_user: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> CreatorAdminSummaryView:
    try:
        return admin_service.set_creator_reward_freeze(
            creator_id=creator_id,
            admin_user_id=current_user.id,
            payload=payload,
        )
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/attributions", response_model=list[AttributionChainEntryView])
def list_referral_attributions(
    share_code_id: str | None = Query(default=None),
    creator_id: str | None = Query(default=None),
    attribution_status: str | None = Query(default=None),
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> list[AttributionChainEntryView]:
    return admin_service.list_attributions(
        share_code_id=share_code_id,
        creator_id=creator_id,
        attribution_status=attribution_status,
    )


@router.get("/rewards/pending", response_model=list[PendingRewardView])
def list_pending_referral_rewards(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> list[PendingRewardView]:
    return admin_service.list_pending_rewards()


@router.post("/rewards/{reward_id}/review", response_model=RewardReviewDecisionView)
def review_referral_reward(
    reward_id: str,
    payload: RewardReviewRequest,
    current_user: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> RewardReviewDecisionView:
    try:
        return admin_service.review_reward(reward_id=reward_id, admin_user_id=current_user.id, payload=payload)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@router.get("/flags", response_model=list[ReferralFlagView])
def list_referral_flags(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> list[ReferralFlagView]:
    return admin_service.list_flags()


@router.get("/analytics/summary", response_model=ReferralAnalyticsSummaryView)
def get_referral_analytics_summary(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> ReferralAnalyticsSummaryView:
    return admin_service.analytics_summary()


@router.get("/leaderboard", response_model=CreatorLeaderboardResponse)
def get_creator_leaderboard(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> CreatorLeaderboardResponse:
    return admin_service.creator_leaderboard()
