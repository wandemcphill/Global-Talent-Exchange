from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.user import User
from backend.app.reward_engine.schemas import PromoPoolCreditRequest, PromoPoolCreditView, RewardEngineSummaryView, RewardSettlementRequest, RewardSettlementView
from backend.app.reward_engine.service import RewardEngineError, RewardEngineService

router = APIRouter(prefix='/reward-engine', tags=['reward-engine'])
admin_router = APIRouter(prefix='/admin/reward-engine', tags=['admin-reward-engine'])


def _map_settlement(item: RewardSettlement) -> RewardSettlementView:
    return RewardSettlementView(
        id=item.id,
        user_id=item.user_id,
        competition_key=item.competition_key,
        reward_source=item.reward_source,
        title=item.title,
        gross_amount=item.gross_amount,
        platform_fee_amount=item.platform_fee_amount,
        net_amount=item.net_amount,
        ledger_unit=item.ledger_unit.value,
        ledger_transaction_id=item.ledger_transaction_id,
        status=item.status.value,
        note=item.note,
        created_at=item.created_at,
    )


@admin_router.post('/settlements', response_model=RewardSettlementView)
def settle_reward(payload: RewardSettlementRequest, actor: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> RewardSettlementView:
    service = RewardEngineService(session)
    try:
        item = service.settle_reward(
            actor=actor,
            user_id=payload.user_id,
            competition_key=payload.competition_key,
            title=payload.title,
            gross_amount=payload.gross_amount,
            reward_source=payload.reward_source,
            note=payload.note,
        )
    except RewardEngineError as exc:
        if exc.reason in {"spending_controls_blocked", "promo_pool_insufficient"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
        if exc.reason == "recipient_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    session.commit()
    session.refresh(item)
    return _map_settlement(item)


@admin_router.post('/promo-pool/credits', response_model=PromoPoolCreditView)
def credit_promo_pool(payload: PromoPoolCreditRequest, actor: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> PromoPoolCreditView:
    service = RewardEngineService(session)
    try:
        transaction_id, reference = service.credit_promo_pool(
            actor=actor,
            amount=payload.amount,
            unit=payload.unit,
            reference=payload.reference,
            note=payload.note,
        )
    except RewardEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc
    session.commit()
    return PromoPoolCreditView(
        transaction_id=transaction_id,
        amount=payload.amount,
        unit=payload.unit,
        reference=reference,
    )


@router.get('/me/settlements', response_model=list[RewardSettlementView])
def list_my_reward_settlements(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[RewardSettlementView]:
    service = RewardEngineService(session)
    return [_map_settlement(item) for item in service.list_settlements_for_user(user=current_user)]


@router.get('/me/summary', response_model=RewardEngineSummaryView)
def get_my_reward_summary(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> RewardEngineSummaryView:
    service = RewardEngineService(session)
    data = service.summary_for_user(user=current_user)
    return RewardEngineSummaryView(
        total_rewards=data['total_rewards'],
        total_platform_fee=data['total_platform_fee'],
        settlements=[_map_settlement(item) for item in data['settlements']],
    )
