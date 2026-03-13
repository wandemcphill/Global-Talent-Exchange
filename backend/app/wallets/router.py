from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pathlib import Path
import json
from decimal import Decimal
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.admin_godmode.service import (
    DEFAULT_COMMISSION_SETTINGS,
    DEFAULT_WITHDRAWAL_CONTROLS,
)
from backend.app.models.user import User
from backend.app.orders.router import (
    api_router as orders_api_router,
    legacy_router as orders_legacy_router,
)
from backend.app.portfolio.router import router as portfolio_router
from backend.app.wallets.schemas import (
    PaymentEventCreate,
    PaymentEventView,
    PortfolioSnapshotView,
    WalletAccountBalance,
    WalletLedgerEntryView,
    WalletLedgerPageView,
    WalletSummaryView,
    WalletAdaptiveOverviewView,
    WithdrawalRequestCreate,
    WithdrawalRequestView,
)
from backend.app.wallets.service import LedgerError, WalletService
from backend.app.models.wallet import PayoutStatus

router = APIRouter()
wallet_router = APIRouter(prefix="/wallets", tags=["wallets"])
api_router = APIRouter(prefix="/api")


def _api_operation_id(route: APIRoute) -> str:
    path = route.path_format.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    methods = "_".join(sorted(method.lower() for method in (route.methods or set())))
    return f"api_{route.name}_{path}_{methods}"


def _build_wallet_service(request: Request | None) -> WalletService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return WalletService(event_publisher=request.app.state.event_publisher)
    return WalletService()


def _load_admin_god_mode_state(request: Request | None) -> dict[str, object]:
    if request is None or not hasattr(request.app.state, "settings"):
        return {}
    config_root = getattr(request.app.state.settings, "config_root", None)
    if config_root is None:
        return {}
    path = Path(config_root) / "admin_god_mode.json"
    if not path.exists():
        return {
            "commissions": dict(DEFAULT_COMMISSION_SETTINGS),
            "withdrawal_controls": dict(DEFAULT_WITHDRAWAL_CONTROLS),
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "commissions": dict(DEFAULT_COMMISSION_SETTINGS),
            "withdrawal_controls": dict(DEFAULT_WITHDRAWAL_CONTROLS),
        }


def _withdrawal_controls(request: Request | None) -> dict[str, object]:
    return dict((_load_admin_god_mode_state(request).get("withdrawal_controls") or {}))


def _commission_settings(request: Request | None) -> dict[str, object]:
    return dict((_load_admin_god_mode_state(request).get("commissions") or {}))


def _build_withdrawal_policy_snapshot(request: Request | None) -> dict[str, object]:
    controls = _withdrawal_controls(request)
    return {
        "policy_enforced": bool(controls),
        "processor_mode": str(controls.get("processor_mode", "manual_bank_transfer")),
        "deposits_via_bank_transfer": bool(controls.get("deposits_via_bank_transfer", True)),
        "payouts_via_bank_transfer": bool(controls.get("payouts_via_bank_transfer", True)),
        "egame_withdrawals_enabled": bool(controls.get("egame_withdrawals_enabled", False)),
        "trade_withdrawals_enabled": bool(controls.get("trade_withdrawals_enabled", True)),
    }


def _validate_bank_transfer_destination(destination_reference: str) -> str:
    candidate = destination_reference.strip()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A payout destination reference is required.")
    if not candidate.lower().startswith("bank:"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Bank-transfer payouts must use a destination_reference starting with bank:.")
    return candidate


def _selected_deposit_mode(policy: dict[str, object]) -> str:
    if not bool(policy.get("policy_enforced", False)):
        return "gateway"
    processor_mode = str(policy.get("processor_mode", "manual_bank_transfer"))
    if processor_mode == "manual_bank_transfer" or bool(policy.get("deposits_via_bank_transfer", True)):
        return "bank_transfer"
    return "gateway"


def _selected_payout_mode(policy: dict[str, object]) -> str:
    processor_mode = str(policy.get("processor_mode", "manual_bank_transfer"))
    if processor_mode == "manual_bank_transfer" or bool(policy.get("payouts_via_bank_transfer", True)):
        return "bank_transfer"
    return "gateway"


@wallet_router.get("/accounts", response_model=list[WalletAccountBalance])
def list_wallet_accounts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[WalletAccountBalance]:
    service = _build_wallet_service(request)
    accounts = service.list_accounts_for_user(session, current_user)
    return [
        WalletAccountBalance(
            id=account.id,
            code=account.code,
            label=account.label,
            unit=account.unit,
            kind=account.kind,
            allow_negative=account.allow_negative,
            is_active=account.is_active,
            balance=service.get_balance(session, account),
        )
        for account in accounts
    ]


@wallet_router.get("/summary", response_model=WalletSummaryView)
def get_wallet_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WalletSummaryView:
    service = _build_wallet_service(request)
    summary = service.get_wallet_summary(session, current_user)
    return WalletSummaryView(
        available_balance=summary.available_balance,
        reserved_balance=summary.reserved_balance,
        total_balance=summary.total_balance,
        currency=summary.currency,
    )


@wallet_router.get("/adaptive-overview", response_model=WalletAdaptiveOverviewView)
def get_wallet_adaptive_overview(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WalletAdaptiveOverviewView:
    service = _build_wallet_service(request)
    overview = service.get_adaptive_overview(session, current_user)
    policy = _build_withdrawal_policy_snapshot(request)
    overview["competition_reward_balance"] = service.competition_reward_balance(session, current_user)
    overview["competition_reward_withdrawable_balance"] = service.competition_reward_withdrawable_balance(session, current_user)
    overview.update(policy)
    insights = list(overview.get("insights") or [])
    payout_mode = _selected_payout_mode(policy)
    deposit_mode = _selected_deposit_mode(policy)
    insights.append({
        "label": "Deposit rail",
        "value": "Bank transfer" if deposit_mode == "bank_transfer" else "Automatic gateway",
        "tone": "info",
    })
    insights.append({
        "label": "Withdrawal rail",
        "value": "Bank transfer" if payout_mode == "bank_transfer" else "Automatic gateway",
        "tone": "info",
    })
    insights.append({
        "label": "E-game cash-out",
        "value": "Enabled" if policy["egame_withdrawals_enabled"] else "Tradable only",
        "tone": "success" if policy["egame_withdrawals_enabled"] else "warning",
    })
    overview["insights"] = insights
    return WalletAdaptiveOverviewView(**overview)


@wallet_router.get("/ledger", response_model=WalletLedgerPageView)
def list_wallet_ledger(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WalletLedgerPageView:
    service = _build_wallet_service(request)
    ledger_page = service.list_ledger_entries_for_user(
        session,
        current_user,
        page=page,
        page_size=page_size,
    )
    return WalletLedgerPageView(
        page=ledger_page.page,
        page_size=ledger_page.page_size,
        total=ledger_page.total,
        items=[WalletLedgerEntryView.model_validate(item) for item in ledger_page.items],
    )


@router.get("/portfolio", response_model=PortfolioSnapshotView, tags=["wallets"])
def get_portfolio(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> PortfolioSnapshotView:
    service = _build_wallet_service(request)
    snapshot = service.build_portfolio_snapshot(session, current_user)
    return PortfolioSnapshotView(
        user_id=snapshot.user_id,
        currency=snapshot.currency,
        available_balance=snapshot.available_balance,
        reserved_balance=snapshot.reserved_balance,
        total_balance=snapshot.total_balance,
        holdings=snapshot.holdings,
    )


@wallet_router.get("/withdrawals", response_model=list[WithdrawalRequestView])
def list_withdrawals(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[WithdrawalRequestView]:
    service = _build_wallet_service(request)
    items = service.list_payout_requests_for_user(session, current_user)
    result: list[WithdrawalRequestView] = []
    for item in items:
        meta = service._parse_payout_meta(item.notes)
        result.append(WithdrawalRequestView(
            payout_request_id=item.id,
            amount=item.amount,
            fee_amount=Decimal(str(meta.get("fee_amount", "0.0000"))),
            total_debit=Decimal(str(meta.get("total_debit", item.amount))),
            unit=item.unit,
            status=item.status,
            source_scope=str(meta.get("source_scope", "trade")),
            destination_reference=item.destination_reference,
            processing_mode=str(meta.get("processor_mode", "manual_bank_transfer")),
            payout_channel=str(meta.get("payout_channel", "bank_transfer")),
            notes=item.notes,
            requested_at=item.created_at,
            updated_at=item.updated_at,
        ))
    return result


@wallet_router.post("/withdrawals", response_model=WithdrawalRequestView, status_code=status.HTTP_201_CREATED)
def create_withdrawal_request(
    payload: WithdrawalRequestCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WithdrawalRequestView:
    service = _build_wallet_service(request)
    policy = _build_withdrawal_policy_snapshot(request)
    commissions = _commission_settings(request)
    if payload.source_scope == "competition" and not bool(policy.get("egame_withdrawals_enabled", False)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-game winnings are currently locked for direct withdrawal. They remain tradable inside the app.")
    if payload.source_scope == "trade" and not bool(policy.get("trade_withdrawals_enabled", True)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trade withdrawals are temporarily disabled by admin policy.")
    payout_channel = _selected_payout_mode(policy)
    destination_reference = payload.destination_reference
    if payout_channel == "bank_transfer":
        destination_reference = _validate_bank_transfer_destination(payload.destination_reference)
    try:
        result = service.request_payout(
            session,
            user=current_user,
            amount=payload.amount,
            destination_reference=destination_reference,
            unit=payload.unit,
            source_scope=payload.source_scope,
            withdrawal_fee_bps=int(commissions.get("withdrawal_fee_bps", 1000) or 1000),
            minimum_fee=Decimal(str(commissions.get("minimum_withdrawal_fee_credits", "5.0000") or "5.0000")),
            actor=current_user,
            notes=payload.notes,
            extra_meta={
                "processor_mode": str(policy.get("processor_mode", "manual_bank_transfer")),
                "payout_channel": payout_channel,
                "deposits_via_bank_transfer": bool(policy.get("deposits_via_bank_transfer", True)),
                "payouts_via_bank_transfer": bool(policy.get("payouts_via_bank_transfer", True)),
            },
        )
        processor_mode = str(policy.get("processor_mode", "manual_bank_transfer"))
        if payout_channel == "gateway" and processor_mode == "automatic_gateway":
            result.payout_request.status = PayoutStatus.PROCESSING
        else:
            result.payout_request.status = PayoutStatus.REVIEWING
        session.commit()
        session.refresh(result.payout_request)
    except LedgerError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return WithdrawalRequestView(
        payout_request_id=result.payout_request.id,
        amount=result.payout_request.amount,
        fee_amount=result.fee_amount,
        total_debit=result.total_debit,
        unit=result.payout_request.unit,
        status=result.payout_request.status,
        source_scope=result.source_scope,
        destination_reference=result.payout_request.destination_reference,
        processing_mode=str(policy.get("processor_mode", "manual_bank_transfer")),
        payout_channel=payout_channel,
        notes=result.payout_request.notes,
        requested_at=result.payout_request.created_at,
        updated_at=result.payout_request.updated_at,
    )


@wallet_router.post("/payment-events", response_model=PaymentEventView, status_code=status.HTTP_201_CREATED)
def create_payment_event(
    payload: PaymentEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> PaymentEventView:
    service = _build_wallet_service(request)
    policy = _build_withdrawal_policy_snapshot(request)
    deposit_mode = _selected_deposit_mode(policy)
    if deposit_mode != "gateway":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Automatic gateway deposits are disabled. Admin has selected manual bank transfer as the active funding rail.",
        )
    try:
        payment_event = service.create_payment_event(
            session,
            user=current_user,
            provider=payload.provider,
            provider_reference=payload.provider_reference,
            amount=payload.amount,
            pack_code=payload.pack_code,
        )
        session.commit()
        session.refresh(payment_event)
    except LedgerError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return PaymentEventView.model_validate(payment_event)


router.include_router(wallet_router)
router.include_router(orders_legacy_router)
router.include_router(orders_api_router, generate_unique_id_function=_api_operation_id)
api_router.include_router(wallet_router, generate_unique_id_function=_api_operation_id)
api_router.include_router(portfolio_router, generate_unique_id_function=_api_operation_id)
router.include_router(api_router)
