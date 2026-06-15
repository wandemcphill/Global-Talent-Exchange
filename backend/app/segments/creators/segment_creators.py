from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.copilot.copilot_service import CreatorCopilotService
from app.models.user import User
from app.schemas.creator_requests import (
    CreatorCopilotDraftRequest,
    CreatorProfileCreateRequest,
    CreatorProfileUpdateRequest,
)
from app.schemas.creator_responses import (
    CreatorCopilotAnalysisView,
    CreatorCompetitionView,
    CreatorFinanceSummaryView,
    CreatorInsightsView,
    CreatorProfileView,
    CreatorSummaryView,
)
from app.services.referral_orchestrator import ReferralActionError, ReferralOrchestrator, get_referral_orchestrator
from app.services.creator_clip_monetization_service import CreatorClipMonetizationService
from app.services.creator_insights_service import CreatorInsightsService

from app.models.gift_transaction import GiftTransaction, GiftTransactionStatus
from app.models.reward_settlement import RewardSettlement, RewardSettlementStatus
from app.models.treasury import TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from app.models.wallet import LedgerUnit, PayoutRequest
from app.wallets.service import WalletService

# Endpoints are declared on prefix-less base routers so the same route set can be
# mounted under multiple namespaces. `_base_router` carries the full creators
# surface; `_alias_subset` carries only the bare `/creators/...` aliases.
_base_router = APIRouter(tags=["creators"])
_alias_subset = APIRouter(tags=["creators"])


@_base_router.post("/profile", response_model=CreatorProfileView, status_code=status.HTTP_201_CREATED)
def create_creator_profile(
    payload: CreatorProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        profile = CreatorProfileView.model_validate(
            orchestrator.create_creator_profile(current_user=current_user, payload=payload)
        )
        if orchestrator.session is not None:
            orchestrator.session.commit()
        return profile
    except ReferralActionError as exc:
        if orchestrator.session is not None:
            orchestrator.session.rollback()
        raise _to_http_error(exc) from exc


@_base_router.patch("/profile", response_model=CreatorProfileView)
def update_creator_profile(
    payload: CreatorProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        profile = CreatorProfileView.model_validate(
            orchestrator.update_creator_profile(current_user=current_user, payload=payload)
        )
        if orchestrator.session is not None:
            orchestrator.session.commit()
        return profile
    except ReferralActionError as exc:
        if orchestrator.session is not None:
            orchestrator.session.rollback()
        raise _to_http_error(exc) from exc


@_base_router.get("/profile/me", response_model=CreatorProfileView)
def get_my_creator_profile(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorProfileView:
    try:
        return CreatorProfileView.model_validate(orchestrator.get_my_creator_profile(current_user=current_user))
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@_base_router.get("/me/summary", response_model=CreatorSummaryView)
def get_my_creator_summary(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> CreatorSummaryView:
    try:
        return orchestrator.get_creator_summary(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc


@_base_router.get("/me/competitions", response_model=list[CreatorCompetitionView])
def get_my_creator_competitions(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
) -> list[CreatorCompetitionView]:
    try:
        competitions = orchestrator.get_creator_competitions(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc
    return [CreatorCompetitionView.model_validate(competition) for competition in competitions]


@_base_router.get("/me/finance", response_model=CreatorFinanceSummaryView)
def get_my_creator_finance(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
    session: Session = Depends(get_session),
) -> CreatorFinanceSummaryView:
    try:
        competitions = orchestrator.get_creator_competitions(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc
    wallet_service = WalletService()
    total_gift_income = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(GiftTransaction.recipient_net_amount), 0)).where(
                GiftTransaction.recipient_user_id == current_user.id,
                GiftTransaction.status == GiftTransactionStatus.SETTLED,
            )
        )
        or 0
    )
    total_reward_income = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(RewardSettlement.net_amount), 0)).where(
                RewardSettlement.user_id == current_user.id, RewardSettlement.status == RewardSettlementStatus.SETTLED
            )
        )
        or 0
    )
    rows = session.execute(
        select(TreasuryWithdrawalRequest, PayoutRequest)
        .join(PayoutRequest, TreasuryWithdrawalRequest.payout_request_id == PayoutRequest.id)
        .where(TreasuryWithdrawalRequest.user_id == current_user.id)
    ).all()
    total_withdrawn_gross = Decimal("0.0000")
    total_withdrawal_fees = Decimal("0.0000")
    total_withdrawn_net = Decimal("0.0000")
    pending_withdrawals = Decimal("0.0000")
    for withdrawal, payout in rows:
        meta = wallet_service._parse_payout_meta(payout.notes if payout else None)
        gross = Decimal(str(meta.get("requested_net_amount", withdrawal.amount_coin)))
        fee = Decimal(str(meta.get("fee_amount", "0.0000")))
        if withdrawal.status in {
            TreasuryWithdrawalStatus.PENDING_REVIEW,
            TreasuryWithdrawalStatus.APPROVED,
            TreasuryWithdrawalStatus.PROCESSING,
        }:
            pending_withdrawals += gross
        if withdrawal.status == TreasuryWithdrawalStatus.PAID:
            total_withdrawn_gross += gross
            total_withdrawal_fees += fee
            total_withdrawn_net += gross
    attributed_signups = sum(item.attributed_signups for item in competitions)
    qualified_joins = sum(item.qualified_joins for item in competitions)
    clip_summary = CreatorClipMonetizationService(session, wallet_service=wallet_service).build_creator_summary(
        actor=current_user
    )
    insights = [
        f"{len(competitions)} creator competition(s) are currently linked to your profile.",
        f"Gift income settled: {total_gift_income:.4f} credits.",
        f"Reward income settled: {total_reward_income:.4f} credits.",
    ]
    if clip_summary.total_creator_payout_credit > Decimal("0.0000"):
        insights.append(
            f"Clip monetization has paid {clip_summary.total_creator_payout_credit:.4f} credits across {clip_summary.total_views} views."
        )
    if clip_summary.total_viral_bonus_credit > Decimal("0.0000"):
        insights.append(f"Viral clip bonuses added {clip_summary.total_viral_bonus_credit:.4f} credits.")
    if pending_withdrawals > Decimal("0.0000"):
        insights.append(f"{pending_withdrawals:.4f} credits are still moving through the withdrawal queue.")
    return CreatorFinanceSummaryView(
        currency="credits",
        total_gift_income=total_gift_income,
        total_reward_income=total_reward_income,
        total_clip_income=clip_summary.total_creator_payout_credit,
        total_clip_views=clip_summary.total_views,
        monetized_clips=clip_summary.monetized_clip_count,
        viral_clip_count=clip_summary.viral_clip_count,
        total_viral_bonus=clip_summary.total_viral_bonus_credit,
        total_referral_bonus=clip_summary.total_referral_bonus_credit,
        total_weekly_top_creator_bonus=clip_summary.total_weekly_top_creator_bonus_credit,
        total_withdrawn_gross=total_withdrawn_gross,
        total_withdrawal_fees=total_withdrawal_fees,
        total_withdrawn_net=total_withdrawn_net,
        pending_withdrawals=pending_withdrawals,
        wallet_balance=clip_summary.wallet_balance_credit,
        wallet_available_balance=clip_summary.wallet_available_credit,
        wallet_currency=clip_summary.wallet_currency or LedgerUnit.CREDIT.value,
        active_competitions=len(competitions),
        attributed_signups=attributed_signups,
        qualified_joins=qualified_joins,
        insights=insights,
    )


@_base_router.get("/me/insights", response_model=CreatorInsightsView)
@_alias_subset.get("/me/insights", response_model=CreatorInsightsView)
def get_my_creator_insights(
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
    session: Session = Depends(get_session),
) -> CreatorInsightsView:
    try:
        creator = orchestrator.get_my_creator_profile(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc
    return CreatorInsightsView.model_validate(
        CreatorInsightsService(session=session).build_creator_insights(
            actor=current_user,
            creator_id=creator.creator_id,
        )
    )


@_base_router.post("/me/copilot/analyze", response_model=CreatorCopilotAnalysisView)
@_alias_subset.post("/me/copilot/analyze", response_model=CreatorCopilotAnalysisView)
def analyze_my_creator_draft(
    payload: CreatorCopilotDraftRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: ReferralOrchestrator = Depends(get_referral_orchestrator),
    session: Session = Depends(get_session),
) -> CreatorCopilotAnalysisView:
    try:
        creator = orchestrator.get_my_creator_profile(current_user=current_user)
    except ReferralActionError as exc:
        raise _to_http_error(exc) from exc
    return CreatorCopilotAnalysisView.model_validate(
        CreatorCopilotService(session=session).analyze_draft(
            actor=current_user,
            creator_id=creator.creator_id,
            draft=payload.model_dump(mode="python"),
        )
    )


@_base_router.get("/{handle}", response_model=CreatorProfileView)
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


# Mount the full creators surface under both /api/creators and /api/v2/creators,
# and the bare-alias subset under /creators. The /api/v2 mirror matches /api/creators
# route-for-route, so the contract's present/absent split holds for both namespaces.
router = APIRouter(prefix="/api/creators", tags=["creators"])
router.include_router(_base_router)
api_v2_router = APIRouter(prefix="/api/v2/creators", tags=["creators"])
api_v2_router.include_router(_base_router)
alias_router = APIRouter(prefix="/creators", tags=["creators"])
alias_router.include_router(_alias_subset)
