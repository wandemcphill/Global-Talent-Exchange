from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.gift_engine.schemas import (
    GiftAbuseFlagView,
    GiftCatalogAdminPatchRequest,
    GiftCatalogAdminUpsertRequest,
    GiftCatalogItemView,
    GiftComboEventView,
    GiftComboSummaryView,
    GiftEngineSummaryView,
    GiftSendRequest,
    GiftStatsView,
    GiftTransactionView,
)
from app.gift_engine.service import GiftEngineError, GiftEngineService
from app.models.economy_config import GiftCatalogItem
from app.models.gift_transaction import GiftAbuseFlag, GiftStats, GiftTransactionStatus
from app.models.gift_combo_event import GiftComboEvent
from app.models.gift_transaction import GiftTransaction
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

router = APIRouter(prefix="/gift-engine", tags=["gift-engine"])
gifts_router = APIRouter(prefix="/gifts", tags=["gifts"])
gift_stats_router = APIRouter(tags=["gifts"])
admin_gifts_router = APIRouter(prefix="/admin/gifts", tags=["admin-gifts"])


def _map_catalog_item(item: GiftCatalogItem) -> GiftCatalogItemView:
    return GiftCatalogItemView(
        id=item.id,
        code=item.key,
        display_name=item.display_name,
        fallback_display_name=item.fallback_display_name,
        description=item.description,
        cost_amount=item.fancoin_price,
        currency=item.currency,
        currency_label="Fan Coin" if item.currency == "credit" else "GTEX Coin",
        rarity=item.rarity,
        tier=item.tier,
        animation_key=item.animation_key,
        sound_key=item.sound_key,
        duration_ms=item.duration_ms,
        is_active=item.active,
        is_award_pack=item.is_award_pack,
        legal_status=item.legal_status,
        sort_order=item.sort_order,
    )


def _map_transaction(item: GiftTransaction) -> GiftTransactionView:
    gift_item = item.gift_catalog_item
    return GiftTransactionView(
        id=item.id,
        sender_user_id=item.sender_user_id,
        recipient_user_id=item.recipient_user_id,
        gift_key=gift_item.key,
        gift_display_name=gift_item.display_name,
        fallback_gift_name=gift_item.fallback_display_name,
        rarity=gift_item.rarity,
        quantity=item.quantity,
        unit_price=item.unit_price,
        gross_amount=item.gross_amount,
        platform_rake_amount=item.platform_rake_amount,
        recipient_net_amount=item.recipient_net_amount,
        recipient_type=item.recipient_type,
        recipient_entity_id=item.recipient_entity_id,
        chat_thread_id=item.chat_thread_id,
        discussion_thread_id=item.discussion_thread_id,
        discussion_reply_id=item.discussion_reply_id,
        match_id=item.match_id,
        competition_id=item.competition_id,
        source_scope=item.source_scope,
        ledger_unit=item.ledger_unit.value,
        currency_label="Fan Coin" if item.ledger_unit.value == "credit" else "GTEX Coin",
        ledger_transaction_id=item.ledger_transaction_id,
        wallet_debit_ledger_id=item.wallet_debit_ledger_id,
        wallet_credit_ledger_id=item.wallet_credit_ledger_id,
        platform_fee_ledger_id=item.platform_fee_ledger_id,
        idempotency_key=item.idempotency_key,
        animation_key=item.animation_key,
        sound_key=item.sound_key,
        duration_ms=gift_item.duration_ms,
        abuse_status=item.abuse_status,
        animation_payload={
            "event_type": "gift.sent",
            "gift_code": gift_item.key,
            "gift_name": gift_item.display_name,
            "fallback_gift_name": gift_item.fallback_display_name,
            "rarity": gift_item.rarity,
            "animation_key": item.animation_key or gift_item.animation_key,
            "sound_key": item.sound_key or gift_item.sound_key,
            "amount": str(item.gross_amount),
            "currency_label": "Fan Coin" if item.ledger_unit.value == "credit" else "GTEX Coin",
            "duration_ms": gift_item.duration_ms,
            "chat_thread_id": item.chat_thread_id,
            "discussion_thread_id": item.discussion_thread_id,
            "match_id": item.match_id,
            "competition_id": item.competition_id,
        },
        note=item.note,
        status=item.status.value,
        created_at=item.created_at,
    )


def _map_stats(item: GiftStats | None, *, entity_type: str, entity_id: str) -> GiftStatsView:
    if item is None:
        return GiftStatsView(
            entity_type=entity_type,
            entity_id=entity_id,
            total_gifts_received=0,
            total_fan_coin_received=0,
            total_unique_senders=0,
            mythic_gifts_received=0,
        )
    return GiftStatsView(
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        total_gifts_received=item.total_gifts_received,
        total_fan_coin_received=item.total_fan_coin_received,
        total_unique_senders=item.total_unique_senders,
        top_gift_code=item.top_gift_code,
        mythic_gifts_received=item.mythic_gifts_received,
    )


def _map_abuse_flag(item: GiftAbuseFlag) -> GiftAbuseFlagView:
    return GiftAbuseFlagView(
        id=item.id,
        flag_key=item.flag_key,
        sender_user_id=item.sender_user_id,
        recipient_type=item.recipient_type,
        recipient_id=item.recipient_id,
        gift_transaction_id=item.gift_transaction_id,
        flag_type=item.flag_type,
        severity=item.severity,
        description=item.description,
        status=item.status,
        metadata_json=item.metadata_json,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _apply_admin_catalog_fields(
    item: GiftCatalogItem,
    payload: GiftCatalogAdminUpsertRequest | GiftCatalogAdminPatchRequest,
) -> GiftCatalogItem:
    if isinstance(payload, GiftCatalogAdminUpsertRequest) or payload.display_name is not None:
        item.display_name = payload.display_name
    if payload.fallback_display_name is not None:
        item.fallback_display_name = payload.fallback_display_name
    if payload.description is not None:
        item.description = payload.description
    price = payload.cost_amount if payload.cost_amount is not None else payload.fancoin_price
    if isinstance(payload, GiftCatalogAdminUpsertRequest):
        price = payload.resolved_price
    if price is not None:
        item.fancoin_price = price
    if payload.currency is not None:
        item.currency = payload.currency
    if payload.rarity is not None:
        item.rarity = payload.rarity
    if payload.tier is not None:
        item.tier = payload.tier
    if payload.animation_key is not None:
        item.animation_key = payload.animation_key
    if payload.sound_key is not None:
        item.sound_key = payload.sound_key
    if payload.duration_ms is not None:
        item.duration_ms = payload.duration_ms
    active = payload.active if payload.active is not None else payload.is_active
    if active is not None:
        item.active = active
    if payload.is_award_pack is not None:
        item.is_award_pack = payload.is_award_pack
    if payload.legal_status is not None:
        item.legal_status = payload.legal_status
    if payload.sort_order is not None:
        item.sort_order = payload.sort_order
    return item


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


@router.post("/send", response_model=GiftTransactionView)
def send_gift(
    payload: GiftSendRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> GiftTransactionView:
    service = GiftEngineService(session)
    try:
        item = service.send_gift(
            sender=current_user,
            recipient_user_id=payload.recipient_user_id,
            gift_key=payload.gift_key,
            quantity=payload.quantity,
            note=payload.note,
            source_scope=payload.source_scope,
            idempotency_key=payload.idempotency_key,
            chat_thread_id=payload.chat_thread_id,
            discussion_thread_id=payload.discussion_thread_id,
            discussion_reply_id=payload.discussion_reply_id,
            match_id=payload.match_id,
            competition_id=payload.competition_id,
        )
    except GiftEngineError as exc:
        status_code = (
            status.HTTP_409_CONFLICT if exc.reason == "spending_controls_blocked" else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return _map_transaction(item)


@router.get("/me/transactions", response_model=list[GiftTransactionView])
def list_my_gifts(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> list[GiftTransactionView]:
    service = GiftEngineService(session)
    return [_map_transaction(item) for item in service.list_transactions_for_user(user=current_user)]


@router.get("/me/summary", response_model=GiftEngineSummaryView)
def get_my_gift_summary(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> GiftEngineSummaryView:
    service = GiftEngineService(session)
    data = service.summary_for_user(user=current_user)
    return GiftEngineSummaryView(
        sent_total=data["sent_total"],
        received_total=data["received_total"],
        rake_total=data["rake_total"],
        recent_transactions=[_map_transaction(item) for item in data["recent_transactions"]],
    )


@router.get("/me/combos", response_model=GiftComboSummaryView)
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


@gifts_router.get("/catalog", response_model=list[GiftCatalogItemView])
def list_gift_catalog(session: Session = Depends(get_session)) -> list[GiftCatalogItemView]:
    service = GiftEngineService(session)
    items = service.list_catalog(active_only=True)
    session.commit()
    return [_map_catalog_item(item) for item in items]


@gifts_router.get("/award-packs", response_model=list[GiftCatalogItemView])
def list_award_gift_packs(session: Session = Depends(get_session)) -> list[GiftCatalogItemView]:
    service = GiftEngineService(session)
    items = service.list_catalog(active_only=True, award_only=True)
    session.commit()
    return [_map_catalog_item(item) for item in items]


@gifts_router.post("/send", response_model=GiftTransactionView)
def send_public_gift(
    payload: GiftSendRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> GiftTransactionView:
    service = GiftEngineService(session)
    try:
        item = service.send_gift(
            sender=current_user,
            recipient_user_id=payload.recipient_user_id,
            gift_key=payload.gift_key,
            quantity=payload.quantity,
            note=payload.note,
            source_scope="user_hosted",
            idempotency_key=payload.idempotency_key,
            chat_thread_id=payload.chat_thread_id,
            discussion_thread_id=payload.discussion_thread_id,
            discussion_reply_id=payload.discussion_reply_id,
            match_id=payload.match_id,
            competition_id=payload.competition_id,
        )
    except GiftEngineError as exc:
        status_code = (
            status.HTTP_409_CONFLICT if exc.reason == "spending_controls_blocked" else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return _map_transaction(item)


@gifts_router.get("/events", response_model=list[GiftTransactionView])
def list_my_gift_events(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[GiftTransactionView]:
    service = GiftEngineService(session)
    return [_map_transaction(item) for item in service.list_transactions_for_user(user=current_user)]


@gifts_router.get("/users/{user_id}/gift-stats", response_model=GiftStatsView)
def get_user_gift_stats(user_id: str, session: Session = Depends(get_session)) -> GiftStatsView:
    item = session.scalar(select(GiftStats).where(GiftStats.entity_type == "user", GiftStats.entity_id == user_id))
    return _map_stats(item, entity_type="user", entity_id=user_id)


@gifts_router.get("/discussions/threads/{thread_id}/gift-stats", response_model=GiftStatsView)
def get_discussion_thread_gift_stats(thread_id: str, session: Session = Depends(get_session)) -> GiftStatsView:
    item = session.scalar(
        select(GiftStats).where(GiftStats.entity_type == "discussion_thread", GiftStats.entity_id == thread_id)
    )
    return _map_stats(item, entity_type="discussion_thread", entity_id=thread_id)


@gift_stats_router.get("/users/{user_id}/gift-stats", response_model=GiftStatsView)
def get_user_gift_stats_alias(user_id: str, session: Session = Depends(get_session)) -> GiftStatsView:
    return get_user_gift_stats(user_id=user_id, session=session)


@gift_stats_router.get("/discussions/threads/{thread_id}/gift-stats", response_model=GiftStatsView)
def get_discussion_thread_gift_stats_alias(thread_id: str, session: Session = Depends(get_session)) -> GiftStatsView:
    return get_discussion_thread_gift_stats(thread_id=thread_id, session=session)


@admin_gifts_router.get("/events", response_model=list[GiftTransactionView])
def admin_list_gift_events(
    abuse_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[GiftTransactionView]:
    statement = select(GiftTransaction).order_by(GiftTransaction.created_at.desc()).limit(limit)
    if abuse_status:
        statement = statement.where(GiftTransaction.abuse_status == abuse_status.strip().lower())
    return [_map_transaction(item) for item in session.scalars(statement).all()]


@admin_gifts_router.get("/abuse-flags", response_model=list[GiftAbuseFlagView])
def admin_list_gift_abuse_flags(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[GiftAbuseFlagView]:
    statement = select(GiftAbuseFlag).order_by(GiftAbuseFlag.created_at.desc()).limit(limit)
    if status_filter:
        statement = statement.where(GiftAbuseFlag.status == status_filter.strip().lower())
    return [_map_abuse_flag(item) for item in session.scalars(statement).all()]


@admin_gifts_router.post("/catalog", response_model=GiftCatalogItemView)
def admin_upsert_gift_catalog_item(
    payload: GiftCatalogAdminUpsertRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> GiftCatalogItemView:
    key = payload.resolved_key
    if not key:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Gift code is required.")
    service = GiftEngineService(session)
    service.ensure_football_gift_catalog()
    item = session.scalar(select(GiftCatalogItem).where(GiftCatalogItem.key == key))
    if item is None:
        item = GiftCatalogItem(key=key)
        session.add(item)
    _apply_admin_catalog_fields(item, payload)
    item.updated_by_user_id = actor.id
    session.commit()
    session.refresh(item)
    return _map_catalog_item(item)


@admin_gifts_router.patch("/catalog/{gift_id}", response_model=GiftCatalogItemView)
def admin_patch_gift_catalog_item(
    gift_id: str,
    payload: GiftCatalogAdminPatchRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> GiftCatalogItemView:
    GiftEngineService(session).ensure_football_gift_catalog()
    item = session.get(GiftCatalogItem, gift_id)
    if item is None:
        item = session.scalar(select(GiftCatalogItem).where(GiftCatalogItem.key == gift_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift catalog item was not found.")
    _apply_admin_catalog_fields(item, payload)
    item.updated_by_user_id = actor.id
    session.commit()
    session.refresh(item)
    return _map_catalog_item(item)


@admin_gifts_router.post("/events/{event_id}/refund", response_model=GiftTransactionView)
def admin_refund_gift_event(
    event_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> GiftTransactionView:
    transaction = session.get(GiftTransaction, event_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift event was not found.")
    if transaction.status == GiftTransactionStatus.REFUNDED:
        return _map_transaction(transaction)

    sender = session.get(User, transaction.sender_user_id)
    recipient = session.get(User, transaction.recipient_user_id)
    if sender is None or recipient is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Gift users are no longer available.")

    wallet_service = WalletService()
    sender_account = wallet_service.get_user_account(session, sender, transaction.ledger_unit)
    recipient_account = wallet_service.get_user_account(session, recipient, transaction.ledger_unit)
    platform_account = wallet_service.ensure_platform_account(session, transaction.ledger_unit)
    source_tag = (
        LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN
        if transaction.ledger_unit.value == "credit"
        else LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
    )
    try:
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=recipient_account, amount=-transaction.recipient_net_amount, source_tag=source_tag
                ),
                LedgerPosting(
                    account=platform_account, amount=-transaction.platform_rake_amount, source_tag=source_tag
                ),
                LedgerPosting(account=sender_account, amount=transaction.gross_amount, source_tag=source_tag),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=source_tag,
            reference=f"gift-refund:{transaction.id}",
            description=f"Admin refund for gift {transaction.gift_catalog_item.key}",
            external_reference=f"gift-refund:{transaction.id}",
            actor=actor,
            idempotency_key=f"gift-refund:{transaction.id}",
            metadata={"gift_transaction_id": transaction.id, "admin_user_id": actor.id},
        )
    except InsufficientBalanceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    transaction.status = GiftTransactionStatus.REFUNDED
    transaction.abuse_status = "review"
    transaction.metadata_json = {
        **dict(transaction.metadata_json or {}),
        "refunded_by_user_id": actor.id,
    }
    session.commit()
    session.refresh(transaction)
    return _map_transaction(transaction)
