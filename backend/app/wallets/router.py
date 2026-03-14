from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pathlib import Path
import json
from decimal import Decimal
from fastapi.routing import APIRoute
from sqlalchemy import func, select
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
    WalletOverviewView,
)
from backend.app.wallets.service import LedgerError, WalletService
from backend.app.models.wallet import LedgerEntry, PayoutRequest, PayoutStatus
from backend.app.models.treasury import DepositRequest, DepositStatus, PaymentMode, TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from backend.app.treasury.schemas import (
    DepositQuoteRequest,
    DepositRequestView,
    DepositSubmitRequest,
    WithdrawalEligibilityView,
    WithdrawalRequestCreate as TreasuryWithdrawalRequestCreate,
    WithdrawalRequestView as TreasuryWithdrawalRequestView,
)
from backend.app.treasury.service import TreasuryConflictError, TreasuryService

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


def _build_treasury_service(request: Request | None) -> TreasuryService:
    if request is not None and hasattr(request.app.state, "event_publisher"):
        return TreasuryService(wallet_service=WalletService(event_publisher=request.app.state.event_publisher))
    return TreasuryService()


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
    treasury = _build_treasury_service(request)
    settings = treasury.ensure_settings(session)
    overview["competition_reward_balance"] = service.competition_reward_balance(session, current_user)
    overview["competition_reward_withdrawable_balance"] = service.competition_reward_withdrawable_balance(session, current_user)
    overview.update(policy)
    insights = list(overview.get("insights") or [])
    payout_mode = "bank_transfer" if settings.withdrawal_mode == PaymentMode.MANUAL else "gateway"
    deposit_mode = "bank_transfer" if settings.deposit_mode == PaymentMode.MANUAL else "gateway"
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


@wallet_router.get("/overview", response_model=WalletOverviewView)
def get_wallet_overview(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WalletOverviewView:
    wallet_service = _build_wallet_service(request)
    treasury_service = _build_treasury_service(request)
    summary = wallet_service.get_wallet_summary(session, current_user)
    account = wallet_service.get_user_account(session, current_user, summary.currency)
    total_inflow = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .where(LedgerEntry.account_id == account.id, LedgerEntry.amount > 0)
    )
    total_outflow = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .where(LedgerEntry.account_id == account.id, LedgerEntry.amount < 0)
    )
    pending_deposits = session.scalar(
        select(func.coalesce(func.sum(DepositRequest.amount_coin), 0))
        .where(
            DepositRequest.user_id == current_user.id,
            DepositRequest.status.in_([
                DepositStatus.AWAITING_PAYMENT,
                DepositStatus.PAYMENT_SUBMITTED,
                DepositStatus.UNDER_REVIEW,
            ]),
        )
    )
    pending_withdrawals = session.scalar(
        select(func.coalesce(func.sum(TreasuryWithdrawalRequest.amount_coin), 0))
        .where(
            TreasuryWithdrawalRequest.user_id == current_user.id,
            TreasuryWithdrawalRequest.status.in_([
                TreasuryWithdrawalStatus.PENDING_REVIEW,
                TreasuryWithdrawalStatus.APPROVED,
                TreasuryWithdrawalStatus.PROCESSING,
            ]),
        )
    )
    eligibility = treasury_service.get_withdrawal_eligibility(session, current_user)
    return WalletOverviewView(
        available_balance=summary.available_balance,
        pending_deposits=Decimal(pending_deposits or 0),
        pending_withdrawals=Decimal(pending_withdrawals or 0),
        total_inflow=Decimal(total_inflow or 0),
        total_outflow=abs(Decimal(total_outflow or 0)),
        withdrawable_now=eligibility.withdrawable_now,
        currency=summary.currency,
    )


@wallet_router.post("/deposits", response_model=DepositRequestView, status_code=status.HTTP_201_CREATED)
def create_deposit_request(
    payload: DepositQuoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> DepositRequestView:
    service = _build_treasury_service(request)
    try:
        deposit = service.create_deposit_request(
            session,
            user=current_user,
            amount=payload.amount,
            input_unit=payload.input_unit,
        )
        session.commit()
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DepositRequestView.model_validate(deposit)


@wallet_router.post("/deposits/{deposit_id}/submit", response_model=DepositRequestView)
def submit_deposit_request(
    deposit_id: str,
    payload: DepositSubmitRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> DepositRequestView:
    service = _build_treasury_service(request)
    try:
        deposit = service.submit_deposit_request(
            session,
            user=current_user,
            deposit_request_id=deposit_id,
            payer_name=payload.payer_name,
            sender_bank=payload.sender_bank,
            transfer_reference=payload.transfer_reference,
            proof_attachment_id=payload.proof_attachment_id,
        )
        session.commit()
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DepositRequestView.model_validate(deposit)


@wallet_router.get("/deposits", response_model=list[DepositRequestView])
def list_deposits(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[DepositRequestView]:
    service = _build_treasury_service(request)
    deposits = service.list_user_deposits(session, current_user)
    return [DepositRequestView.model_validate(item) for item in deposits]


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


@wallet_router.get("/withdrawals", response_model=list[TreasuryWithdrawalRequestView])
def list_withdrawals(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[TreasuryWithdrawalRequestView]:
    wallet_service = _build_wallet_service(request)
    rows = session.execute(
        select(TreasuryWithdrawalRequest, PayoutRequest)
        .join(PayoutRequest, TreasuryWithdrawalRequest.payout_request_id == PayoutRequest.id)
        .where(TreasuryWithdrawalRequest.user_id == current_user.id)
        .order_by(TreasuryWithdrawalRequest.created_at.desc())
    ).all()
    result: list[TreasuryWithdrawalRequestView] = []
    for withdrawal, payout in rows:
        meta = wallet_service._parse_payout_meta(payout.notes)
        result.append(
            TreasuryWithdrawalRequestView(
                id=withdrawal.id,
                payout_request_id=withdrawal.payout_request_id,
                reference=withdrawal.reference,
                status=withdrawal.status,
                unit=withdrawal.unit,
                amount_coin=withdrawal.amount_coin,
                amount_fiat=withdrawal.amount_fiat,
                currency_code=withdrawal.currency_code,
                rate_value=withdrawal.rate_value,
                rate_direction=withdrawal.rate_direction,
                bank_name=withdrawal.bank_name,
                bank_account_number=withdrawal.bank_account_number,
                bank_account_name=withdrawal.bank_account_name,
                bank_code=withdrawal.bank_code,
                kyc_status_snapshot=withdrawal.kyc_status_snapshot,
                kyc_tier_snapshot=withdrawal.kyc_tier_snapshot,
                fee_amount=Decimal(str(meta.get("fee_amount", "0.0000"))),
                total_debit=Decimal(str(meta.get("total_debit", payout.amount))),
                notes=withdrawal.notes,
                created_at=withdrawal.created_at,
                reviewed_at=withdrawal.reviewed_at,
                approved_at=withdrawal.approved_at,
                processed_at=withdrawal.processed_at,
                paid_at=withdrawal.paid_at,
                rejected_at=withdrawal.rejected_at,
                cancelled_at=withdrawal.cancelled_at,
            )
        )
    return result


@wallet_router.get("/withdrawals/eligibility", response_model=WithdrawalEligibilityView)
def get_withdrawal_eligibility(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WithdrawalEligibilityView:
    service = _build_treasury_service(request)
    eligibility = service.get_withdrawal_eligibility(session, current_user)
    service.track_event(session, "withdrawal_started", user=current_user, metadata={})
    return WithdrawalEligibilityView(
        available_balance=eligibility.available_balance,
        withdrawable_now=eligibility.withdrawable_now,
        remaining_allowance=eligibility.remaining_allowance,
        next_eligible_at=eligibility.next_eligible_at,
        kyc_status=eligibility.kyc_status,
        requires_kyc=eligibility.requires_kyc,
        requires_bank_account=eligibility.requires_bank_account,
        pending_withdrawals=eligibility.pending_withdrawals,
    )


@wallet_router.post("/withdrawals", response_model=TreasuryWithdrawalRequestView, status_code=status.HTTP_201_CREATED)
def create_withdrawal_request(
    payload: TreasuryWithdrawalRequestCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> TreasuryWithdrawalRequestView:
    service = _build_treasury_service(request)
    wallet_service = _build_wallet_service(request)
    try:
        withdrawal = service.create_withdrawal_request(
            session,
            user=current_user,
            amount_coin=payload.amount_coin,
            bank_account_id=payload.bank_account_id,
            notes=payload.notes,
        )
        session.commit()
        session.refresh(withdrawal)
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    payout_request = session.get(PayoutRequest, withdrawal.payout_request_id)
    meta = wallet_service._parse_payout_meta(payout_request.notes if payout_request else None)
    return TreasuryWithdrawalRequestView(
        id=withdrawal.id,
        payout_request_id=withdrawal.payout_request_id,
        reference=withdrawal.reference,
        status=withdrawal.status,
        unit=withdrawal.unit,
        amount_coin=withdrawal.amount_coin,
        amount_fiat=withdrawal.amount_fiat,
        currency_code=withdrawal.currency_code,
        rate_value=withdrawal.rate_value,
        rate_direction=withdrawal.rate_direction,
        bank_name=withdrawal.bank_name,
        bank_account_number=withdrawal.bank_account_number,
        bank_account_name=withdrawal.bank_account_name,
        bank_code=withdrawal.bank_code,
        kyc_status_snapshot=withdrawal.kyc_status_snapshot,
        kyc_tier_snapshot=withdrawal.kyc_tier_snapshot,
        fee_amount=Decimal(str(meta.get("fee_amount", "0.0000"))),
        total_debit=Decimal(str(meta.get("total_debit", withdrawal.amount_coin))),
        notes=withdrawal.notes,
        created_at=withdrawal.created_at,
        reviewed_at=withdrawal.reviewed_at,
        approved_at=withdrawal.approved_at,
        processed_at=withdrawal.processed_at,
        paid_at=withdrawal.paid_at,
        rejected_at=withdrawal.rejected_at,
        cancelled_at=withdrawal.cancelled_at,
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
    treasury = _build_treasury_service(request)
    settings = treasury.ensure_settings(session)
    deposit_mode = "bank_transfer" if settings.deposit_mode == PaymentMode.MANUAL else _selected_deposit_mode(policy)
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
