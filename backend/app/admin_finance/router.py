from __future__ import annotations

from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.admin_finance.schemas import (
    AccountControlUpsertRequest,
    AccountControlView,
    AdminBulkActionRequest,
    AdminBulkActionStatusView,
    AdminEconomySimulationConfig,
    AdminEconomySimulationResultView,
    AdminExportRequest,
    AdminExportStatusView,
    AdminFinanceControlTowerView,
    AdminFinanceWebhookResultView,
    AdminLockAcquireRequest,
    AdminLockStateView,
    ManualPriceOverrideUpsertRequest,
    ManualPriceOverrideView,
    MatchKillSwitchUpsertRequest,
    MatchKillSwitchView,
    PaymentQueueActionRequest,
    PaymentQueueActionResultView,
    PaymentQueueView,
    PaymentReconciliationSummaryView,
    WalletProtectionSummaryView,
    WalletTransactionLockView,
)
from app.admin_finance.service import AdminFinanceService
from app.admin_godmode.service import AdminGodModeService, PermissionDeniedError
from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.services.runtime_control_service import RuntimeControlService
from app.treasury.service import TreasuryConflictError
from app.wallets.service import WalletService

router = APIRouter(prefix="/api/admin/finance", tags=["admin-finance"])
webhook_router = APIRouter(prefix="/api/v2/integrations/payments", tags=["payments"])


def _require_payment_queue_permission(request: Request, actor: User) -> None:
    service = AdminGodModeService(
        wallet_service=WalletService(cache_backend=getattr(request.app.state, "cache_backend", None))
    )
    try:
        profile = service.resolve_profile(actor, service._load_state(request.app))
        service._assert_has_permission(profile, "manage_treasury_withdrawals")
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


def _require_admin_notes(payload: PaymentQueueActionRequest | dict | None) -> str:
    if isinstance(payload, PaymentQueueActionRequest):
        raw_notes = payload.admin_notes or payload.reason or payload.notes
    else:
        raw_notes = (
            None if payload is None else payload.get("admin_notes") or payload.get("reason") or payload.get("notes")
        )
    notes = str(raw_notes or "").strip()
    if not notes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="admin_notes is required.")
    return notes


def _queue_service(request: Request, session: Session) -> AdminFinanceService:
    return AdminFinanceService(session=session, settings=request.app.state.settings)


def _ensure_live_match_hub(app):
    from app.live_matches.service import ensure_live_match_hub

    return ensure_live_match_hub(app)


@router.get("/control-tower", response_model=AdminFinanceControlTowerView)
def get_control_tower(
    request: Request,
    history_days: int = Query(default=30, ge=7, le=90),
    transaction_limit: int = Query(default=12, ge=3, le=50),
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminFinanceControlTowerView:
    del actor
    service = AdminFinanceService(session=session, settings=request.app.state.settings)
    payload = service.get_control_tower_snapshot(
        history_days=history_days,
        transaction_limit=transaction_limit,
    )
    control_summary = RuntimeControlService(request.app).summary()
    governor_snapshot = service.governor_snapshot()
    payload.update(
        {
            **control_summary,
            "banned_account_count": service.count_banned_accounts(),
            "economy_governor_mode": governor_snapshot["mode"],
        }
    )
    session.commit()
    return AdminFinanceControlTowerView.model_validate(payload)


@router.post("/simulate", response_model=AdminEconomySimulationResultView)
def simulate_economy(
    payload: AdminEconomySimulationConfig,
    request: Request,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminEconomySimulationResultView:
    del actor
    result = AdminFinanceService(session=session, settings=request.app.state.settings).simulate(
        days=30,
        config=payload.model_dump(mode="json"),
    )
    return AdminEconomySimulationResultView.model_validate(result)


@router.get("/manual-price-overrides", response_model=list[ManualPriceOverrideView])
def list_manual_price_overrides(
    request: Request,
    _: User = Depends(get_current_admin),
) -> list[ManualPriceOverrideView]:
    return [
        ManualPriceOverrideView.model_validate(item)
        for item in RuntimeControlService(request.app).list_price_overrides()
    ]


@router.post("/manual-price-overrides", response_model=ManualPriceOverrideView)
def upsert_manual_price_override(
    payload: ManualPriceOverrideUpsertRequest,
    request: Request,
    actor: User = Depends(get_current_admin),
) -> ManualPriceOverrideView:
    item = RuntimeControlService(request.app).upsert_price_override(
        asset_type=payload.asset_type,
        asset_id=payload.asset_id,
        override_price=payload.override_price,
        currency=payload.currency,
        reason=payload.reason,
        updated_by_user_id=actor.id,
    )
    return ManualPriceOverrideView.model_validate(item)


@router.delete("/manual-price-overrides/{asset_type}/{asset_id}", response_model=ManualPriceOverrideView)
def delete_manual_price_override(
    asset_type: str,
    asset_id: str,
    request: Request,
    _: User = Depends(get_current_admin),
) -> ManualPriceOverrideView:
    item = RuntimeControlService(request.app).remove_price_override(asset_type=asset_type, asset_id=asset_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manual price override was not found.")
    return ManualPriceOverrideView.model_validate(item)


@router.get("/account-controls", response_model=list[AccountControlView])
def list_account_controls(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> list[AccountControlView]:
    control_service = RuntimeControlService(request.app)
    items: list[AccountControlView] = []
    for item in control_service.list_account_controls():
        user = session.get(User, item.user_id)
        items.append(
            AccountControlView(
                user_id=item.user_id,
                freeze_login=item.freeze_login,
                freeze_wallet=item.freeze_wallet,
                freeze_matches=item.freeze_matches,
                freeze_social=item.freeze_social,
                ban_account=False if user is None else not bool(user.is_active),
                reason=item.reason,
                updated_by_user_id=item.updated_by_user_id,
                updated_at=item.updated_at,
            )
        )
    return items


@router.post("/account-controls", response_model=AccountControlView)
def upsert_account_control(
    payload: AccountControlUpsertRequest,
    request: Request,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AccountControlView:
    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user was not found.")
    user.is_active = not payload.ban_account
    item = RuntimeControlService(request.app).upsert_account_control(
        user_id=payload.user_id,
        freeze_login=payload.freeze_login,
        freeze_wallet=payload.freeze_wallet,
        freeze_matches=payload.freeze_matches,
        freeze_social=payload.freeze_social,
        reason=payload.reason,
        updated_by_user_id=actor.id,
    )
    session.commit()
    return AccountControlView(
        user_id=item.user_id,
        freeze_login=item.freeze_login,
        freeze_wallet=item.freeze_wallet,
        freeze_matches=item.freeze_matches,
        freeze_social=item.freeze_social,
        ban_account=payload.ban_account,
        reason=item.reason,
        updated_by_user_id=item.updated_by_user_id,
        updated_at=item.updated_at,
    )


@router.delete("/account-controls/{user_id}", response_model=AccountControlView)
def clear_account_control(
    user_id: str,
    request: Request,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AccountControlView:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user was not found.")
    cleared = RuntimeControlService(request.app).clear_account_control(user_id=user_id)
    user.is_active = True
    session.commit()
    if cleared is None:
        return AccountControlView(
            user_id=user_id,
            freeze_login=False,
            freeze_wallet=False,
            freeze_matches=False,
            freeze_social=False,
            ban_account=False,
            reason=None,
            updated_by_user_id=actor.id,
            updated_at=datetime.now(timezone.utc),
        )
    return AccountControlView(
        user_id=cleared.user_id,
        freeze_login=cleared.freeze_login,
        freeze_wallet=cleared.freeze_wallet,
        freeze_matches=cleared.freeze_matches,
        freeze_social=cleared.freeze_social,
        ban_account=False,
        reason=cleared.reason,
        updated_by_user_id=actor.id,
        updated_at=cleared.updated_at,
    )


@router.get("/match-kill-switches", response_model=list[MatchKillSwitchView])
def list_match_kill_switches(
    request: Request,
    _: User = Depends(get_current_admin),
) -> list[MatchKillSwitchView]:
    return [
        MatchKillSwitchView(
            match_id=item.match_id,
            enabled=item.enabled,
            reason=item.reason,
            updated_by_user_id=item.updated_by_user_id,
            updated_at=item.updated_at,
        )
        for item in RuntimeControlService(request.app).list_match_kill_switches()
    ]


@router.post("/match-kill-switches", response_model=MatchKillSwitchView)
def upsert_match_kill_switch(
    payload: MatchKillSwitchUpsertRequest,
    request: Request,
    actor: User = Depends(get_current_admin),
) -> MatchKillSwitchView:
    control_service = RuntimeControlService(request.app)
    item = control_service.set_match_kill_switch(
        match_id=payload.match_id,
        enabled=payload.enabled,
        reason=payload.reason,
        updated_by_user_id=actor.id,
    )
    hub = _ensure_live_match_hub(request.app)
    if payload.enabled:
        hub.halt_match(payload.match_id, reason=payload.reason, actor_user_id=actor.id)
    else:
        hub.clear_match_halt(payload.match_id)
    return MatchKillSwitchView(
        match_id=item.match_id,
        enabled=item.enabled,
        reason=item.reason,
        updated_by_user_id=item.updated_by_user_id,
        updated_at=item.updated_at,
    )


@router.delete("/match-kill-switches/{match_id}", response_model=MatchKillSwitchView)
def clear_match_kill_switch(
    match_id: str,
    request: Request,
    actor: User = Depends(get_current_admin),
) -> MatchKillSwitchView:
    item = RuntimeControlService(request.app).set_match_kill_switch(
        match_id=match_id,
        enabled=False,
        reason=None,
        updated_by_user_id=actor.id,
    )
    _ensure_live_match_hub(request.app).clear_match_halt(match_id)
    return MatchKillSwitchView(
        match_id=item.match_id,
        enabled=item.enabled,
        reason=item.reason,
        updated_by_user_id=item.updated_by_user_id,
        updated_at=item.updated_at,
    )


@router.get("/wallet-protection", response_model=WalletProtectionSummaryView)
def get_wallet_protection_summary(
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> WalletProtectionSummaryView:
    control_service = RuntimeControlService(request.app)
    frozen_wallet_accounts = sum(1 for item in control_service.list_account_controls() if item.freeze_wallet)
    active_wallet_locks = [
        WalletTransactionLockView.model_validate(item, from_attributes=True).model_dump(mode="json")
        for item in control_service.list_wallet_transaction_locks()
    ]
    payload = AdminFinanceService(session=session, settings=request.app.state.settings).wallet_protection_summary(
        frozen_wallet_account_count=frozen_wallet_accounts,
        active_wallet_transaction_locks=active_wallet_locks,
    )
    return WalletProtectionSummaryView.model_validate(payload)


@router.get("/reconciliation", response_model=PaymentReconciliationSummaryView)
def get_payment_reconciliation_summary(
    request: Request,
    issue_limit: int = Query(default=25, ge=5, le=100),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> PaymentReconciliationSummaryView:
    payload = AdminFinanceService(session=session, settings=request.app.state.settings).payment_reconciliation_summary(
        issue_limit=issue_limit,
    )
    return PaymentReconciliationSummaryView.model_validate(payload)


@router.get("/locks/{resource_type}/{resource_id}", response_model=AdminLockStateView)
def get_admin_resource_lock(
    request: Request,
    resource_type: str,
    resource_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminLockStateView:
    _require_payment_queue_permission(request, actor)
    state = _queue_service(request, session).get_admin_lock_state(
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return AdminLockStateView.model_validate(state)


@router.post("/locks/{resource_type}/{resource_id}", response_model=AdminLockStateView)
def acquire_admin_resource_lock(
    request: Request,
    resource_type: str,
    resource_id: str,
    payload: AdminLockAcquireRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminLockStateView:
    _require_payment_queue_permission(request, actor)
    try:
        state = _queue_service(request, session).acquire_admin_lock(
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
            ttl_seconds=(payload or AdminLockAcquireRequest()).ttl_seconds,
        )
        session.commit()
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminLockStateView.model_validate(state)


@router.delete("/locks/{resource_type}/{resource_id}", response_model=AdminLockStateView)
def release_admin_resource_lock(
    request: Request,
    resource_type: str,
    resource_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminLockStateView:
    _require_payment_queue_permission(request, actor)
    try:
        state = _queue_service(request, session).release_admin_lock(
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        session.commit()
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminLockStateView.model_validate(state)


@router.post("/exports", response_model=AdminExportStatusView, status_code=status.HTTP_202_ACCEPTED)
def request_admin_export(
    request: Request,
    payload: AdminExportRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminExportStatusView:
    _require_payment_queue_permission(request, actor)
    try:
        result = _queue_service(request, session).request_admin_export(
            actor=actor,
            export_type=payload.export_type,
            export_format=payload.format,
            filters=payload.filters,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AdminExportStatusView.model_validate(result)


@router.get("/exports/{export_id}/download")
def download_admin_export(
    request: Request,
    export_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> Response:
    _require_payment_queue_permission(request, actor)
    service = _queue_service(request, session)
    try:
        result = service.complete_admin_export(actor=actor, export_id=export_id)
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if result.get("status") != "ready":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=jsonable_encoder(result),
        )
    try:
        artifact = service.get_admin_export_artifact(export_id=export_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    filename = str(artifact.get("filename") or f"{export_id}.export")
    artifact_content_type = str(artifact.get("content_type") or "application/octet-stream")
    media_type = "text/csv" if artifact_content_type == "text/csv" else "application/octet-stream"
    return Response(
        content=str(artifact["content"]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-GTEX-Audit-Ref": str(result.get("audit_reference") or ""),
            "X-GTEX-Artifact-Content-Type": artifact_content_type,
        },
    )


@router.get("/exports/{export_id}", response_model=AdminExportStatusView)
def get_admin_export_status(
    request: Request,
    export_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminExportStatusView:
    _require_payment_queue_permission(request, actor)
    try:
        result = _queue_service(request, session).complete_admin_export(actor=actor, export_id=export_id)
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminExportStatusView.model_validate(result)


@router.get("/payment-queue", response_model=PaymentQueueView)
def get_admin_payment_queue(
    request: Request,
    tab: str | None = Query(default=None),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueView:
    _require_payment_queue_permission(request, actor)
    try:
        payload = _queue_service(request, session).get_admin_payment_queue(
            actor=actor,
            tab=tab,
            q=q,
            limit=limit,
            offset=offset,
        )
        return PaymentQueueView.model_validate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/payment-queue/bulk-actions",
    response_model=AdminBulkActionStatusView,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_admin_payment_queue_bulk_action(
    request: Request,
    payload: AdminBulkActionRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminBulkActionStatusView:
    _require_payment_queue_permission(request, actor)
    try:
        result = _queue_service(request, session).request_admin_bulk_action(
            actor=actor,
            item_type=payload.item_type,
            action=payload.action,
            item_ids=payload.item_ids,
            admin_notes=payload.admin_notes,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AdminBulkActionStatusView.model_validate(result)


@router.get("/payment-queue/bulk-actions/{bulk_action_id}", response_model=AdminBulkActionStatusView)
def get_admin_payment_queue_bulk_action_status(
    request: Request,
    bulk_action_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AdminBulkActionStatusView:
    _require_payment_queue_permission(request, actor)
    try:
        result = _queue_service(request, session).get_admin_bulk_action_status(bulk_action_id=bulk_action_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AdminBulkActionStatusView.model_validate(result)


@router.post("/payment-queue/deposits/{deposit_id}/review", response_model=PaymentQueueActionResultView)
def review_admin_payment_queue_deposit(
    request: Request,
    deposit_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_deposit_queue_action(request, session, actor, deposit_id, payload, "review")


@router.post("/payment-queue/deposits/{deposit_id}/approve", response_model=PaymentQueueActionResultView)
def approve_admin_payment_queue_deposit(
    request: Request,
    deposit_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_deposit_queue_action(request, session, actor, deposit_id, payload, "approve")


@router.post("/payment-queue/deposits/{deposit_id}/reject", response_model=PaymentQueueActionResultView)
def reject_admin_payment_queue_deposit(
    request: Request,
    deposit_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_deposit_queue_action(request, session, actor, deposit_id, payload, "reject")


@router.post("/payment-queue/deposits/{deposit_id}/reinstate", response_model=PaymentQueueActionResultView)
def reinstate_admin_payment_queue_deposit(
    request: Request,
    deposit_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_deposit_queue_action(request, session, actor, deposit_id, payload, "reinstate")


def _run_deposit_queue_action(
    request: Request,
    session: Session,
    actor: User,
    deposit_id: str,
    payload: PaymentQueueActionRequest | dict | None,
    action: str,
) -> PaymentQueueActionResultView:
    _require_payment_queue_permission(request, actor)
    notes = _require_admin_notes(payload)
    service = _queue_service(request, session)
    try:
        if action == "review":
            result = service.review_payment_queue_deposit(actor=actor, deposit_id=deposit_id, admin_notes=notes)
        elif action == "approve":
            result = service.approve_payment_queue_deposit(actor=actor, deposit_id=deposit_id, admin_notes=notes)
        elif action == "reject":
            result = service.reject_payment_queue_deposit(actor=actor, deposit_id=deposit_id, admin_notes=notes)
        else:
            result = service.reinstate_payment_queue_deposit(actor=actor, deposit_id=deposit_id, admin_notes=notes)
        session.commit()
        return PaymentQueueActionResultView.model_validate(result)
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/payment-queue/withdrawals/{withdrawal_id}/approve", response_model=PaymentQueueActionResultView)
def approve_admin_payment_queue_withdrawal(
    request: Request,
    withdrawal_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_withdrawal_queue_action(request, session, actor, withdrawal_id, payload, "approve")


@router.post("/payment-queue/withdrawals/{withdrawal_id}/reject", response_model=PaymentQueueActionResultView)
def reject_admin_payment_queue_withdrawal(
    request: Request,
    withdrawal_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_withdrawal_queue_action(request, session, actor, withdrawal_id, payload, "reject")


@router.post("/payment-queue/withdrawals/{withdrawal_id}/reinstate", response_model=PaymentQueueActionResultView)
def reinstate_admin_payment_queue_withdrawal(
    request: Request,
    withdrawal_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_withdrawal_queue_action(request, session, actor, withdrawal_id, payload, "reinstate")


def _run_withdrawal_queue_action(
    request: Request,
    session: Session,
    actor: User,
    withdrawal_id: str,
    payload: PaymentQueueActionRequest | dict | None,
    action: str,
) -> PaymentQueueActionResultView:
    _require_payment_queue_permission(request, actor)
    notes = _require_admin_notes(payload)
    service = _queue_service(request, session)
    try:
        if action == "approve":
            result = service.approve_payment_queue_withdrawal(
                actor=actor, withdrawal_id=withdrawal_id, admin_notes=notes
            )
        elif action == "reject":
            result = service.reject_payment_queue_withdrawal(
                actor=actor, withdrawal_id=withdrawal_id, admin_notes=notes
            )
        else:
            result = service.reinstate_payment_queue_withdrawal(
                actor=actor, withdrawal_id=withdrawal_id, admin_notes=notes
            )
        session.commit()
        return PaymentQueueActionResultView.model_validate(result)
    except (TreasuryConflictError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/payment-queue/bids/windows/{window_id}/bids/{bid_id}/approve", response_model=PaymentQueueActionResultView
)
def approve_admin_payment_queue_bid(
    request: Request,
    window_id: str,
    bid_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_bid_queue_action(request, session, actor, window_id, bid_id, payload, "approve")


@router.post(
    "/payment-queue/bids/windows/{window_id}/bids/{bid_id}/reject", response_model=PaymentQueueActionResultView
)
def reject_admin_payment_queue_bid(
    request: Request,
    window_id: str,
    bid_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_bid_queue_action(request, session, actor, window_id, bid_id, payload, "reject")


@router.post(
    "/payment-queue/bids/windows/{window_id}/bids/{bid_id}/counter", response_model=PaymentQueueActionResultView
)
def counter_admin_payment_queue_bid(
    request: Request,
    window_id: str,
    bid_id: str,
    payload: PaymentQueueActionRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PaymentQueueActionResultView:
    return _run_bid_queue_action(request, session, actor, window_id, bid_id, payload, "counter")


def _run_bid_queue_action(
    request: Request,
    session: Session,
    actor: User,
    window_id: str,
    bid_id: str,
    payload: PaymentQueueActionRequest | dict | None,
    action: str,
) -> PaymentQueueActionResultView:
    _require_payment_queue_permission(request, actor)
    notes = _require_admin_notes(payload)
    try:
        result = _queue_service(request, session).record_payment_queue_bid_action(
            actor=actor,
            window_id=window_id,
            bid_id=bid_id,
            action=action,
            admin_notes=notes,
        )
        session.commit()
        return PaymentQueueActionResultView.model_validate(result)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@webhook_router.post("/korapay/webhook", response_model=AdminFinanceWebhookResultView)
async def handle_korapay_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> AdminFinanceWebhookResultView:
    try:
        raw_body = await request.body()
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raw_body = b""
        payload = {}
    try:
        result = AdminFinanceService(session=session, settings=request.app.state.settings).handle_korapay_webhook(
            payload,
            raw_body=raw_body,
            headers=dict(request.headers),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    session.commit()
    return AdminFinanceWebhookResultView.model_validate(result)


__all__ = ["router", "webhook_router"]
