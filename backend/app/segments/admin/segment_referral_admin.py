from __future__ import annotations

import secrets

from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.models.referral_partner import ReferralPartner
from app.models.share_code import ShareCode
from app.models.referral_attribution import ReferralAttribution
from app.models.referral_reward import ReferralReward
from app.common.enums.share_code_type import ShareCodeType
from app.schemas.referral_admin import (
    ReferralPartnerCreateRequest,
    ReferralPartnerStatusRequest,
    ReferralPartnerView,
    ReferralPayoutBatchRequest,
    ReferralPayoutBatchView,
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


def _build_partner_view(session, partner: ReferralPartner) -> ReferralPartnerView:
    codes = tuple(session.scalars(select(ShareCode).order_by(ShareCode.created_at.desc())).all())
    partner_codes = [
        code
        for code in codes
        if str((code.metadata_json or {}).get("referral_partner_id") or "") == partner.id
    ]
    code = partner_codes[0] if partner_codes else None
    attributions = []
    rewards = []
    if code is not None:
        attributions = list(
            session.scalars(
                select(ReferralAttribution).where(ReferralAttribution.share_code_id == code.id)
            ).all()
        )
        rewards = list(
            session.scalars(
                select(ReferralReward).where(ReferralReward.referral_attribution_id.in_(
                    [item.id for item in attributions] or ["__none__"]
                ))
            ).all()
        )
    def total_for(status_value: str):
        return sum(
            (
                reward.reward_amount or 0
                for reward in rewards
                if reward.status.value == status_value
                and str((reward.reward_payload_json or {}).get("reward_role") or "") == "referrer_commission"
            ),
            start=__import__("decimal").Decimal("0.0000"),
        )
    return ReferralPartnerView(
        partner_id=partner.id,
        display_name=partner.display_name,
        contact_email=partner.contact_email,
        social_handle=partner.social_handle,
        campaign_name=partner.campaign_name,
        payout_method=partner.payout_method,
        payout_destination_reference=partner.payout_destination_reference,
        notes=partner.notes,
        is_active=partner.is_active,
        share_code_id=code.id if code is not None else None,
        share_code=code.code if code is not None else None,
        referral_path=f"/signup?ref={code.code}" if code is not None else None,
        current_uses=code.current_uses if code is not None else 0,
        max_uses=code.max_uses if code is not None else 0,
        attributed_signups=len(attributions),
        pending_commission=total_for("pending"),
        approved_commission=total_for("approved"),
        paid_commission=total_for("paid"),
        created_at=partner.created_at,
    )


def _to_http_error(exc: ReferralActionError) -> HTTPException:
    reason = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if reason in {"share_code_not_found", "creator_not_found", "reward_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif reason in {
        "creator_rewards_frozen",
        "reward_hold_active",
        "reward_must_be_approved_before_payout",
        "reward_already_paid",
    }:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=reason)


@router.post("/partners", response_model=ReferralPartnerView, status_code=status.HTTP_201_CREATED)
def create_referral_partner(
    payload: ReferralPartnerCreateRequest,
    current_user: User = Depends(_require_admin),
    session=Depends(get_session),
) -> ReferralPartnerView:
    display_name = payload.display_name.strip()
    vanity = (payload.vanity_code or "").strip().lower()
    if vanity and session.scalar(select(ShareCode.id).where(ShareCode.code == vanity)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="referral_code_already_exists")
    code = vanity or f"gtex{secrets.token_hex(4)}"
    if session.scalar(select(ShareCode.id).where(ShareCode.code == code)) is not None:
        code = f"gtex{secrets.token_hex(6)}"
    partner = ReferralPartner(
        id=secrets.token_hex(18),
        display_name=display_name,
        contact_email=(payload.contact_email or "").strip().lower() or None,
        social_handle=(payload.social_handle or "").strip() or None,
        campaign_name=(payload.campaign_name or "").strip() or None,
        payout_method=payload.payout_method,
        payout_destination_reference=(payload.payout_destination_reference or "").strip() or None,
        notes=(payload.notes or "").strip() or None,
        is_active=True,
        status="active",
        created_by_user_id=current_user.id,
    )
    session.add(partner)
    session.flush()
    share_code = ShareCode(
        code=code,
        vanity_code=vanity or None,
        code_type=ShareCodeType.PROMO_CODE,
        owner_user_id=None,
        owner_creator_id=None,
        is_active=True,
        max_uses=payload.max_uses,
        current_uses=0,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        referral_partner_id=partner.id,
        metadata_json={
            "origin": "admin_referral_affiliate",
            "referral_partner_id": partner.id,
            "campaign_name": partner.campaign_name or "",
            "benefit_rate_bps": "1000",
            "commission_rate_bps": "1000",
        },
    )
    session.add(share_code)
    session.commit()
    session.refresh(partner)
    return _build_partner_view(session, partner)


@router.get("/partners", response_model=list[ReferralPartnerView])
def list_referral_partners(
    _: User = Depends(_require_admin),
    session=Depends(get_session),
) -> list[ReferralPartnerView]:
    partners = session.scalars(
        select(ReferralPartner).order_by(ReferralPartner.created_at.desc(), ReferralPartner.id)
    ).all()
    return [_build_partner_view(session, partner) for partner in partners]


@router.patch("/partners/{partner_id}/status", response_model=ReferralPartnerView)
def set_referral_partner_status(
    partner_id: str,
    payload: ReferralPartnerStatusRequest,
    _: User = Depends(_require_admin),
    session=Depends(get_session),
) -> ReferralPartnerView:
    partner = session.get(ReferralPartner, partner_id)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referral_partner_not_found")
    partner.is_active = payload.is_active
    partner.status = "active" if payload.is_active else "suspended"
    for code in session.scalars(select(ShareCode)).all():
        if str((code.metadata_json or {}).get("referral_partner_id") or "") == partner.id:
            code.is_active = payload.is_active
    session.flush()
    session.commit()
    session.refresh(partner)
    return _build_partner_view(session, partner)


@router.post("/rewards/payout-batch", response_model=ReferralPayoutBatchView)
def mark_referral_rewards_paid(
    payload: ReferralPayoutBatchRequest,
    current_user: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> ReferralPayoutBatchView:
    try:
        rewards = []
        for reward_id in payload.reward_ids:
            reward = admin_service.orchestrator.rewards.get_by_id(reward_id)
            if reward is None:
                raise ReferralActionError("reward_not_found")
            if reward.reward_type != "creator_revshare" or reward.trigger_milestone != "wallet_funded":
                raise ReferralActionError("reward_not_eligible_for_referral_payout")
            rewards.append(reward)
        currencies = {str(reward.unit or "").upper() for reward in rewards}
        if len(currencies) != 1:
            raise ReferralActionError("payout_batch_currency_mismatch")
        total = sum((reward.amount or 0 for reward in rewards), start=__import__("decimal").Decimal("0.0000"))
        paid_at = utcnow()
        for reward in rewards:
            admin_service.orchestrator.rewards.mark_paid(
                reward_id=reward.reward_id,
                payment_reference=payload.payment_reference,
                admin_user_id=current_user.id,
                enforce_hold=True,
            )
        if admin_service.session is not None:
            admin_service.session.commit()
        return ReferralPayoutBatchView(
            payment_reference=payload.payment_reference,
            reward_count=len(rewards),
            total_amount=total,
            currency=next(iter(currencies)),
            reward_ids=[reward.reward_id for reward in rewards],
            paid_at=paid_at,
        )
    except ReferralActionError as exc:
        if admin_service.session is not None:
            admin_service.session.rollback()
        raise _to_http_error(exc) from exc


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
        admin_service.block_share_code(
            share_code_id=share_code_id,
            admin_user_id=current_user.id,
            payload=payload,
        )
        if admin_service.session is not None:
            admin_service.session.commit()
        refreshed = admin_service.get_share_code(share_code_id)
        if refreshed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="share_code_not_found")
        return refreshed
    except ReferralActionError as exc:
        if admin_service.session is not None:
            admin_service.session.rollback()
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
        admin_service.set_creator_reward_freeze(
            creator_id=creator_id,
            admin_user_id=current_user.id,
            payload=payload,
        )
        if admin_service.session is not None:
            admin_service.session.commit()
        refreshed = admin_service.get_creator(creator_id)
        if refreshed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="creator_not_found")
        return refreshed
    except ReferralActionError as exc:
        if admin_service.session is not None:
            admin_service.session.rollback()
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


@router.get("/rewards/approved", response_model=list[PendingRewardView])
def list_approved_referral_rewards(
    _: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> list[PendingRewardView]:
    return admin_service.list_pending_rewards(status_filter="approved")


@router.post("/rewards/{reward_id}/review", response_model=RewardReviewDecisionView)
def review_referral_reward(
    reward_id: str,
    payload: RewardReviewRequest,
    current_user: User = Depends(_require_admin),
    admin_service: ReferralAdminService = Depends(get_referral_admin_service),
) -> RewardReviewDecisionView:
    try:
        result = admin_service.review_reward(
            reward_id=reward_id,
            admin_user_id=current_user.id,
            payload=payload,
        )
        if admin_service.session is not None:
            admin_service.session.commit()
        return result
    except ReferralActionError as exc:
        if admin_service.session is not None:
            admin_service.session.rollback()
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


from app.segments.admin.segment_referral_affiliate_admin import router as affiliate_admin_router

router.include_router(affiliate_admin_router)
