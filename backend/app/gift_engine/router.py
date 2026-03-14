from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.gift_engine.schemas import (
    GiftComboEventView,
    GiftComboSummaryView,
    GiftEngineSummaryView,
    GiftSendRequest,
    GiftTransactionView,
)
from backend.app.gift_engine.service import GiftEngineError, GiftEngineService
from backend.app.models.gift_combo_event import GiftComboEvent
from backend.app.models.gift_transaction import GiftTransaction
from backend.app.models.user import User
from backend.app.wallets.service import InsufficientBalanceError

router = APIRouter(prefix='/gift-engine', tags=['gift-engine'])


def _map_transaction(item: GiftTransaction) -> GiftTransactionView:
    gift_item = item.gift_catalog_item
    return GiftTransactionView(
        id=item.id,
        sender_user_id=item.sender_user_id,
        recipient_user_id=item.recipient_user_id,
        gift_key=gift_item.key,
        gift_display_name=gift_item.display_name,
        quantity=item.quantity,
        unit_price=item.unit_price,
        gross_amount=item.gross_amount,
        platform_rake_amount=item.platform_rake_amount,
        recipient_net_amount=item.recipient_net_amount,
        ledger_unit=item.ledger_unit.value,
        ledger_transaction_id=item.ledger_transaction_id,
        note=item.note,
        status=item.status.value,
        created_at=item.created_at,
    )


def _map_combo_event(item: GiftComboEvent) -> GiftComboEventView:
    gift_item = item.gift_catalog_item
    return GiftComboEventView(
        id=item.id,
        gift_transaction_id=item.gift_transaction_id,
        sender_user_id=item.sender_user_id,
        recipient_user_id=item.recipient_user_id,
        gift_key=gift_item.key,
        gift_display_name=gift_item.display_name,
        combo_rule_key=item.combo_rule_key,
        combo_count=item.combo_count,
        window_seconds=item.window_seconds,
        bonus_bps=item.bonus_bps,
        bonus_amount=item.bonus_amount,
        created_at=item.created_at,
    )


@router.post('/send', response_model=GiftTransactionView)
def send_gift(payload: GiftSendRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> GiftTransactionView:
    service = GiftEngineService(session)
    try:
        item = service.send_gift(
            sender=current_user,
            recipient_user_id=payload.recipient_user_id,
            gift_key=payload.gift_key,
            quantity=payload.quantity,
            note=payload.note,
        )
    except GiftEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return _map_transaction(item)


@router.get('/me/transactions', response_model=list[GiftTransactionView])
def list_my_gifts(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[GiftTransactionView]:
    service = GiftEngineService(session)
    return [_map_transaction(item) for item in service.list_transactions_for_user(user=current_user)]


@router.get('/me/summary', response_model=GiftEngineSummaryView)
def get_my_gift_summary(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> GiftEngineSummaryView:
    service = GiftEngineService(session)
    data = service.summary_for_user(user=current_user)
    return GiftEngineSummaryView(
        sent_total=data['sent_total'],
        received_total=data['received_total'],
        rake_total=data['rake_total'],
        recent_transactions=[_map_transaction(item) for item in data['recent_transactions']],
    )


@router.get('/me/combos', response_model=GiftComboSummaryView)
def get_my_combo_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    role: str = Query(default="sender"),
) -> GiftComboSummaryView:
    normalized_role = role.strip().lower()
    if normalized_role not in {"sender", "recipient"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role must be sender or recipient")
    service = GiftEngineService(session)
    data = service.combo_summary_for_user(user=current_user, role=normalized_role)
    return GiftComboSummaryView(
        total_combos=int(data["total_combos"]),
        total_bonus_amount=data["total_bonus_amount"],
        recent_combos=[_map_combo_event(item) for item in data["recent_combos"]],
    )
