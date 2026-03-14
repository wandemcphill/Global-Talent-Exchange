from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.user import User
from backend.app.schemas.creator_requests import CreatorProfileCreateRequest, CreatorProfileUpdateRequest
from backend.app.schemas.creator_responses import CreatorCompetitionView, CreatorFinanceSummaryView, CreatorProfileView, CreatorSummaryView
from backend.app.services.referral_orchestrator import ReferralActionError, ReferralOrchestrator, get_referral_orchestrator

from backend.app.models.gift_transaction import GiftTransaction, GiftTransactionStatus
from backend.app.models.reward_settlement import RewardSettlement, RewardSettlementStatus
from backend.app.models.treasury import TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from backend.app.models.wallet import PayoutRequest
from backend.app.wallets.service import WalletService

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


@router.get("/me/finance", response_model=CreatorFinanceSummaryView)
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
    total_gift_income = Decimal(session.scalar(select(func.coalesce(func.sum(GiftTransaction.recipient_net_amount), 0)).where(GiftTransaction.recipient_user_id == current_user.id, GiftTransaction.status == GiftTransactionStatus.SETTLED)) or 0)
    total_reward_income = Decimal(session.scalar(select(func.coalesce(func.sum(RewardSettlement.net_amount), 0)).where(RewardSettlement.user_id == current_user.id, RewardSettlement.status == RewardSettlementStatus.SETTLED)) or 0)
    rows = session.execute(select(TreasuryWithdrawalRequest, PayoutRequest).join(PayoutRequest, TreasuryWithdrawalRequest.payout_request_id == PayoutRequest.id).where(TreasuryWithdrawalRequest.user_id == current_user.id)).all()
    total_withdrawn_gross = Decimal('0.0000')
    total_withdrawal_fees = Decimal('0.0000')
    total_withdrawn_net = Decimal('0.0000')
    pending_withdrawals = Decimal('0.0000')
    for withdrawal, payout in rows:
        meta = wallet_service._parse_payout_meta(payout.notes if payout else None)
        gross = Decimal(str(meta.get('requested_net_amount', withdrawal.amount_coin)))
        fee = Decimal(str(meta.get('fee_amount', '0.0000')))
        if withdrawal.status in {TreasuryWithdrawalStatus.PENDING_REVIEW, TreasuryWithdrawalStatus.APPROVED, TreasuryWithdrawalStatus.PROCESSING}:
            pending_withdrawals += gross
        if withdrawal.status == TreasuryWithdrawalStatus.PAID:
            total_withdrawn_gross += gross
            total_withdrawal_fees += fee
            total_withdrawn_net += gross
    attributed_signups = sum(item.attributed_signups for item in competitions)
    qualified_joins = sum(item.qualified_joins for item in competitions)
    insights = [
        f"{len(competitions)} creator competition(s) are currently linked to your profile.",
        f"Gift income settled: {total_gift_income:.4f} credits.",
        f"Reward income settled: {total_reward_income:.4f} credits.",
    ]
    if pending_withdrawals > Decimal('0.0000'):
        insights.append(f"{pending_withdrawals:.4f} credits are still moving through the withdrawal queue.")
    return CreatorFinanceSummaryView(
        currency='credits',
        total_gift_income=total_gift_income,
        total_reward_income=total_reward_income,
        total_withdrawn_gross=total_withdrawn_gross,
        total_withdrawal_fees=total_withdrawal_fees,
        total_withdrawn_net=total_withdrawn_net,
        pending_withdrawals=pending_withdrawals,
        active_competitions=len(competitions),
        attributed_signups=attributed_signups,
        qualified_joins=qualified_joins,
        insights=insights,
    )


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
