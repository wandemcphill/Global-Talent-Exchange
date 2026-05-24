from __future__ import annotations

from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.admin_finance.schemas import (
    AccountControlUpsertRequest,
    AccountControlView,
    AdminEconomySimulationConfig,
    AdminEconomySimulationResultView,
    AdminFinanceControlTowerView,
    AdminFinanceWebhookResultView,
    ManualPriceOverrideUpsertRequest,
    ManualPriceOverrideView,
    MatchKillSwitchUpsertRequest,
    MatchKillSwitchView,
    PaymentReconciliationSummaryView,
    WalletProtectionSummaryView,
    WalletTransactionLockView,
)
from app.admin_finance.service import AdminFinanceService
from app.auth.dependencies import get_current_admin, get_session
from app.live_matches.service import ensure_live_match_hub
from app.models.user import User
from app.services.runtime_control_service import RuntimeControlService
from app.wallets.providers.registry import paystack_enabled

router = APIRouter(prefix="/api/admin/finance", tags=["admin-finance"])
webhook_router = APIRouter(prefix="/integrations/payments", tags=["payments"])
webhook_alias_router = APIRouter(prefix="/api/webhooks", tags=["payments"])


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
    hub = ensure_live_match_hub(request.app)
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
    ensure_live_match_hub(request.app).clear_match_halt(match_id)
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


@webhook_router.post("/paystack/webhook", response_model=AdminFinanceWebhookResultView)
async def handle_paystack_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> AdminFinanceWebhookResultView:
    if not paystack_enabled():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Paystack is unavailable. Use the KoraPay webhook endpoint.",
        )
    try:
        raw_body = await request.body()
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raw_body = b""
        payload = {}
    try:
        result = AdminFinanceService(session=session, settings=request.app.state.settings).handle_paystack_webhook(
            payload,
            raw_body=raw_body,
            headers=dict(request.headers),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    session.commit()
    return AdminFinanceWebhookResultView.model_validate(result)


async def _handle_korapay_webhook_impl(
    request: Request,
    session: Session,
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


@webhook_router.post("/korapay/webhook", response_model=AdminFinanceWebhookResultView)
async def handle_korapay_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> AdminFinanceWebhookResultView:
    return await _handle_korapay_webhook_impl(request=request, session=session)


@webhook_alias_router.post("/korapay", response_model=AdminFinanceWebhookResultView)
async def handle_korapay_webhook_alias(
    request: Request,
    session: Session = Depends(get_session),
) -> AdminFinanceWebhookResultView:
    return await _handle_korapay_webhook_impl(request=request, session=session)


__all__ = ["router", "webhook_router", "webhook_alias_router"]
