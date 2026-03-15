from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pathlib import Path
import json
from decimal import Decimal
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.admin_godmode.service import (
    AdminGodModeService,
    DEFAULT_COMMISSION_SETTINGS,
    DEFAULT_WITHDRAWAL_CONTROLS,
)
from backend.app.models.user import User
from backend.app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from backend.app.models.market_topup import MarketTopup, MarketTopupStatus
from backend.app.policies.service import PolicyService
from backend.app.orders.router import (
    api_router as orders_api_router,
    legacy_router as orders_legacy_router,
)
from backend.app.portfolio.router import router as portfolio_router
from backend.app.wallets.schemas import (
    PaymentEventCreate,
    PaymentEventView,
    PortfolioSnapshotView,
    PurchaseOrderCreateRequest,
    PurchaseOrderQuoteRequest,
    PurchaseOrderQuoteView,
    PurchaseOrderSourceScope,
    PurchaseOrderStatusUpdate,
    PurchaseOrderView,
    MarketTopupCreateRequest,
    MarketTopupQuoteRequest,
    MarketTopupQuoteView,
    MarketTopupSourceScope,
    MarketTopupStatusUpdate,
    MarketTopupView,
    WalletAccountBalance,
    WalletLedgerEntryView,
    WalletLedgerPageView,
    WalletSummaryView,
    WalletAdaptiveOverviewView,
    WalletOverviewView,
)
from backend.app.wallets.service import LedgerError, WalletService
from backend.app.wallets.rail_service import WalletRailError, WalletRailConflictError, WalletRailService
from backend.app.wallets.providers import get_provider_adapter
from backend.app.models.wallet import LedgerEntry, PayoutRequest, PayoutStatus
from backend.app.risk_ops_engine.service import RiskOpsService
from backend.app.models.treasury import DepositRequest, DepositStatus, PaymentMode, TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from backend.app.treasury.schemas import (
    DepositQuoteRequest,
    DepositRequestView,
    DepositSubmitRequest,
    WithdrawalEligibilityView,
    WithdrawalQuoteRequest,
    WithdrawalQuoteView,
    WithdrawalReceiptView,
    WithdrawalSourceScope,
    WithdrawalRequestCreate as TreasuryWithdrawalRequestCreate,
    WithdrawalRequestView as TreasuryWithdrawalRequestView,
)
from backend.app.treasury.service import TreasuryConflictError, TreasuryService

router = APIRouter()
wallet_router = APIRouter(prefix="/wallets", tags=["wallets"])
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin/wallets", tags=["admin-wallets"])


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


def _build_wallet_rail_service(request: Request | None, session: Session) -> WalletRailService:
    event_publisher = None
    if request is not None and hasattr(request.app.state, "event_publisher"):
        event_publisher = request.app.state.event_publisher
    return WalletRailService(session=session, wallet_service=_build_wallet_service(request), event_publisher=event_publisher)


def _require_payment_rails_permission(request: Request, actor: User) -> None:
    service = AdminGodModeService(wallet_service=WalletService())
    state = service._load_state(request.app)
    profile = service.resolve_profile(actor, state)
    service._assert_has_permission(profile, "manage_payment_rails")




def _build_withdrawal_view(withdrawal: TreasuryWithdrawalRequest, payout: PayoutRequest | None, wallet_service: WalletService) -> TreasuryWithdrawalRequestView:
    meta = wallet_service._parse_payout_meta(payout.notes if payout else None)
    gross_amount = Decimal(withdrawal.amount_coin)
    fee_amount = Decimal(withdrawal.fee_amount or 0)
    if fee_amount <= Decimal("0.0000"):
        fee_amount = Decimal(str(meta.get("fee_amount", "0.0000")))
    net_amount = Decimal(withdrawal.net_amount or 0)
    if net_amount <= Decimal("0.0000"):
        net_amount = Decimal(str(meta.get("requested_net_amount", gross_amount)))
    source_scope = str(withdrawal.source_scope or meta.get("source_scope", "trade"))
    processor_mode = str(withdrawal.processor_mode or meta.get("processor_mode", "manual_bank_transfer"))
    payout_channel = str(withdrawal.payout_channel or meta.get("payout_channel", "bank_transfer"))
    total_debit = gross_amount + fee_amount
    if meta.get("total_debit") is not None:
        total_debit = Decimal(str(meta.get("total_debit")))
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
        fee_amount=fee_amount,
        total_debit=total_debit,
        source_scope=WithdrawalSourceScope(source_scope),
        net_amount=net_amount,
        processor_mode=processor_mode,
        payout_channel=payout_channel,
        notes=withdrawal.notes,
        created_at=withdrawal.created_at,
        reviewed_at=withdrawal.reviewed_at,
        approved_at=withdrawal.approved_at,
        processed_at=withdrawal.processed_at,
        paid_at=withdrawal.paid_at,
        rejected_at=withdrawal.rejected_at,
        cancelled_at=withdrawal.cancelled_at,
    )


def _build_withdrawal_quote(*, request: Request | None, session: Session, current_user: User, amount_coin: Decimal, source_scope: WithdrawalSourceScope) -> WithdrawalQuoteView:
    treasury = _build_treasury_service(request)
    settings = treasury.ensure_settings(session)
    eligibility = treasury.get_withdrawal_eligibility(session, current_user)
    commissions = _commission_settings(request)
    fee_bps = int(commissions.get("withdrawal_fee_bps", 1000) or 1000)
    minimum_fee = Decimal(str(commissions.get("minimum_withdrawal_fee_credits", "5.0000") or "5.0000"))
    fee_amount = max((Decimal(amount_coin) * Decimal(fee_bps) / Decimal(10000)), minimum_fee).quantize(Decimal("0.0001"))
    gross_amount = Decimal(amount_coin).quantize(Decimal("0.0001"))
    total_debit = (gross_amount + fee_amount).quantize(Decimal("0.0001"))
    payout_channel = "bank_transfer" if settings.withdrawal_mode == PaymentMode.MANUAL else "gateway"
    processor_mode = "manual_bank_transfer" if settings.withdrawal_mode == PaymentMode.MANUAL else "automatic_gateway"
    blocked_reason = None
    controls = _withdrawal_controls(request)
    if source_scope == WithdrawalSourceScope.COMPETITION and not bool(controls.get("egame_withdrawals_enabled", False)):
        blocked_reason = "E-game reward withdrawals are currently disabled by platform policy."
    elif source_scope == WithdrawalSourceScope.TRADE and not bool(controls.get("trade_withdrawals_enabled", True)):
        blocked_reason = "Trade withdrawals are currently disabled by platform policy."
    elif eligibility.requires_kyc:
        blocked_reason = "KYC is required before withdrawals can be requested."
    elif eligibility.requires_bank_account and payout_channel == "bank_transfer":
        blocked_reason = "Bank account details are required before withdrawals can be requested."
    elif eligibility.policy_blocked:
        blocked_reason = eligibility.policy_block_reason or "Withdrawal policy requirements are not satisfied."
    elif gross_amount > eligibility.withdrawable_now:
        blocked_reason = "Withdrawal amount exceeds available withdrawable balance."
    rate_value = Decimal(settings.withdrawal_rate_value)
    estimated_fiat = gross_amount * rate_value if settings.withdrawal_rate_direction.value == "fiat_per_coin" else gross_amount / rate_value
    return WithdrawalQuoteView(
        gross_amount=gross_amount,
        fee_amount=fee_amount,
        net_amount=gross_amount,
        total_debit=total_debit,
        source_scope=source_scope,
        currency_code=settings.currency_code,
        rate_value=Decimal(settings.withdrawal_rate_value),
        rate_direction=settings.withdrawal_rate_direction,
        estimated_fiat_payout=treasury._normalize_amount(estimated_fiat if settings.withdrawal_rate_direction.value == "fiat_per_coin" else gross_amount / Decimal(settings.withdrawal_rate_value)),
        processor_mode=processor_mode,
        payout_channel=payout_channel,
        fee_bps=fee_bps,
        minimum_fee=minimum_fee,
        eligibility=WithdrawalEligibilityView(
            available_balance=eligibility.available_balance,
            withdrawable_now=eligibility.withdrawable_now,
            remaining_allowance=eligibility.remaining_allowance,
            next_eligible_at=eligibility.next_eligible_at,
            kyc_status=eligibility.kyc_status,
            requires_kyc=eligibility.requires_kyc,
            requires_bank_account=eligibility.requires_bank_account,
            pending_withdrawals=eligibility.pending_withdrawals,
            country_code=eligibility.country_code,
            country_withdrawals_enabled=eligibility.country_withdrawals_enabled,
            missing_required_policies=list(eligibility.missing_required_policies),
            policy_blocked=eligibility.policy_blocked,
            policy_block_reason=eligibility.policy_block_reason,
        ),
        blocked_reason=blocked_reason,
    )

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


def _require_gateway_deposit(
    *,
    request: Request | None,
    session: Session,
    user: User,
) -> tuple[TreasurySettings, str, str]:
    treasury = _build_treasury_service(request)
    settings = treasury.ensure_settings(session)
    policy = _build_withdrawal_policy_snapshot(request)
    policy_service = PolicyService(session)
    compliance_policy = policy_service.get_country_policy_for_user(user=user)
    missing_policies = policy_service.list_missing_acceptances(user_id=user.id)
    deposit_mode = "bank_transfer" if settings.deposit_mode == PaymentMode.MANUAL else _selected_deposit_mode(policy)
    if not compliance_policy.deposits_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deposits are currently disabled for country policy '{compliance_policy.country_code}'.",
        )
    if missing_policies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accept the latest required policies before using automatic gateway deposits.",
        )
    if deposit_mode != "gateway":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Automatic gateway deposits are disabled. Admin has selected manual bank transfer as the active funding rail.",
        )
    processor_mode = "automatic_gateway"
    payout_channel = "gateway"
    return settings, processor_mode, payout_channel


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
    policy_service = PolicyService(session)
    compliance_policy = policy_service.get_country_policy_for_user(user=current_user)
    missing_policies = policy_service.list_missing_acceptances(user_id=current_user.id)
    overview["competition_reward_balance"] = service.competition_reward_balance(session, current_user)
    overview["competition_reward_withdrawable_balance"] = service.competition_reward_withdrawable_balance(session, current_user)
    overview.update(policy)
    overview["country_code"] = compliance_policy.country_code
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
    insights.append({
        "label": "Country policy",
        "value": compliance_policy.country_code,
        "tone": "info",
    })
    if missing_policies:
        insights.append({
            "label": "Compliance actions",
            "value": f"{len(missing_policies)} required policy update(s)",
            "tone": "warning",
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


@wallet_router.post("/purchase-orders/quote", response_model=PurchaseOrderQuoteView)
def create_purchase_order_quote(
    payload: PurchaseOrderQuoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> PurchaseOrderQuoteView:
    try:
        get_provider_adapter(payload.provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    settings, processor_mode, payout_channel = _require_gateway_deposit(request=request, session=session, user=current_user)
    rail_service = _build_wallet_rail_service(request, session)
    try:
        quote = rail_service.quote_purchase_order(
            settings=settings,
            amount=payload.amount,
            input_unit=payload.input_unit,
            provider_key=payload.provider_key,
            source_scope=payload.source_scope.value,
            unit=payload.unit,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
        )
    except WalletRailConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WalletRailError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PurchaseOrderQuoteView(
        amount_fiat=quote.amount_fiat,
        gross_amount=quote.gross_amount,
        fee_amount=quote.fee_amount,
        net_amount=quote.net_amount,
        currency_code=quote.currency_code,
        rate_value=quote.rate_value,
        rate_direction=quote.rate_direction.value if hasattr(quote.rate_direction, "value") else str(quote.rate_direction),
        unit=quote.unit,
        processor_mode=quote.processor_mode,
        payout_channel=quote.payout_channel,
        provider_key=quote.provider_key,
        source_scope=PurchaseOrderSourceScope(quote.source_scope),
    )


@wallet_router.post("/purchase-orders", response_model=PurchaseOrderView, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> PurchaseOrderView:
    try:
        get_provider_adapter(payload.provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    settings, processor_mode, payout_channel = _require_gateway_deposit(request=request, session=session, user=current_user)
    rail_service = _build_wallet_rail_service(request, session)
    try:
        order = rail_service.create_purchase_order(
            user=current_user,
            settings=settings,
            amount=payload.amount,
            input_unit=payload.input_unit,
            provider_key=payload.provider_key,
            source_scope=payload.source_scope.value,
            unit=payload.unit,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
            provider_reference=payload.provider_reference,
            notes=payload.notes,
        )
        session.commit()
        session.refresh(order)
    except WalletRailConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WalletRailError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PurchaseOrderView.model_validate(order)


@wallet_router.get("/purchase-orders", response_model=list[PurchaseOrderView])
def list_purchase_orders(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[PurchaseOrderView]:
    rail_service = _build_wallet_rail_service(request, session)
    orders = rail_service.list_purchase_orders_for_user(user=current_user, limit=limit)
    return [PurchaseOrderView.model_validate(order) for order in orders]


@wallet_router.get("/purchase-orders/{order_id}", response_model=PurchaseOrderView)
def get_purchase_order(
    order_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PurchaseOrderView:
    order = session.scalar(
        select(FancoinPurchaseOrder).where(FancoinPurchaseOrder.id == order_id, FancoinPurchaseOrder.user_id == current_user.id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    return PurchaseOrderView.model_validate(order)


@wallet_router.get("/market-topups", response_model=list[MarketTopupView])
def list_market_topups(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[MarketTopupView]:
    topups = session.scalars(
        select(MarketTopup)
        .where(MarketTopup.user_id == current_user.id)
        .order_by(MarketTopup.created_at.desc())
        .limit(limit)
    ).all()
    return [MarketTopupView.model_validate(item) for item in topups]


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
        result.append(_build_withdrawal_view(withdrawal, payout, wallet_service))
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
        country_code=eligibility.country_code,
        country_withdrawals_enabled=eligibility.country_withdrawals_enabled,
        missing_required_policies=list(eligibility.missing_required_policies),
        policy_blocked=eligibility.policy_blocked,
        policy_block_reason=eligibility.policy_block_reason,
    )


@wallet_router.post("/withdrawals/quote", response_model=WithdrawalQuoteView)
def create_withdrawal_quote(
    payload: WithdrawalQuoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WithdrawalQuoteView:
    return _build_withdrawal_quote(request=request, session=session, current_user=current_user, amount_coin=payload.amount_coin, source_scope=payload.source_scope)


@wallet_router.get("/withdrawals/{withdrawal_id}/receipt", response_model=WithdrawalReceiptView)
def get_withdrawal_receipt(
    withdrawal_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WithdrawalReceiptView:
    wallet_service = _build_wallet_service(request)
    row = session.execute(
        select(TreasuryWithdrawalRequest, PayoutRequest)
        .join(PayoutRequest, TreasuryWithdrawalRequest.payout_request_id == PayoutRequest.id)
        .where(TreasuryWithdrawalRequest.id == withdrawal_id, TreasuryWithdrawalRequest.user_id == current_user.id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal receipt not found.")
    withdrawal, payout = row
    view = _build_withdrawal_view(withdrawal, payout, wallet_service)
    return WithdrawalReceiptView(
        withdrawal=view,
        gross_amount=withdrawal.amount_coin,
        fee_amount=view.fee_amount,
        net_amount=view.net_amount,
        total_debit=view.total_debit,
        source_scope=view.source_scope,
        processor_mode=view.processor_mode,
        payout_channel=view.payout_channel,
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
    controls = _withdrawal_controls(request)
    if payload.source_scope == WithdrawalSourceScope.COMPETITION and not bool(controls.get("egame_withdrawals_enabled", False)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-game reward withdrawals are currently disabled by platform policy.")
    if payload.source_scope == WithdrawalSourceScope.TRADE and not bool(controls.get("trade_withdrawals_enabled", True)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trade withdrawals are currently disabled by platform policy.")
    try:
        withdrawal = service.create_withdrawal_request(
            session,
            user=current_user,
            amount_coin=payload.amount_coin,
            bank_account_id=payload.bank_account_id,
            source_scope=payload.source_scope.value,
            notes=payload.notes,
        )
        session.commit()
        session.refresh(withdrawal)
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    payout_request = session.get(PayoutRequest, withdrawal.payout_request_id)
    return _build_withdrawal_view(withdrawal, payout_request, wallet_service)


@wallet_router.post("/providers/{provider_key}/webhook")
async def handle_provider_webhook(
    provider_key: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        adapter = get_provider_adapter(provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    event = adapter.parse_webhook(payload, headers=dict(request.headers))
    rail_service = _build_wallet_rail_service(request, session)
    if event is None:
        return {"status": "ignored"}
    order = rail_service.handle_provider_event(event=event)
    session.commit()
    return {
        "status": "ok",
        "purchase_order_id": order.id if order else None,
        "order_status": order.status.value if order is not None and hasattr(order.status, "value") else (str(order.status) if order else None),
    }


@admin_router.get("/purchase-orders", response_model=list[PurchaseOrderView])
def list_admin_purchase_orders(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
    status_filter: str | None = Query(default=None, alias="status"),
    provider_key: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PurchaseOrderView]:
    _require_payment_rails_permission(request, actor)
    query = select(FancoinPurchaseOrder)
    if status_filter:
        try:
            status_value = PurchaseOrderStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        query = query.where(FancoinPurchaseOrder.status == status_value)
    if provider_key:
        query = query.where(FancoinPurchaseOrder.provider_key == provider_key)
    if user_id:
        query = query.where(FancoinPurchaseOrder.user_id == user_id)
    orders = session.scalars(
        query.order_by(FancoinPurchaseOrder.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return [PurchaseOrderView.model_validate(order) for order in orders]


@admin_router.post("/purchase-orders/{order_id}/status", response_model=PurchaseOrderView)
def update_purchase_order_status(
    order_id: str,
    payload: PurchaseOrderStatusUpdate,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
) -> PurchaseOrderView:
    _require_payment_rails_permission(request, actor)
    order = session.get(FancoinPurchaseOrder, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found.")
    try:
        status_value = PurchaseOrderStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    rail_service = _build_wallet_rail_service(request, session)
    order = rail_service.apply_purchase_order_status(order=order, status=status_value, actor=actor, notes=payload.notes)
    RiskOpsService(session).log_audit(
        actor_user_id=actor.id,
        action_key="wallet.purchase_order.status_changed",
        resource_type="purchase_order",
        resource_id=order.id,
        detail=f"Purchase order set to {status_value.value}.",
        metadata_json={"status": status_value.value, "reference": order.reference},
    )
    session.commit()
    session.refresh(order)
    return PurchaseOrderView.model_validate(order)


@admin_router.post("/market-topups/quote", response_model=MarketTopupQuoteView)
def quote_market_topup(
    payload: MarketTopupQuoteRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
) -> MarketTopupQuoteView:
    _require_payment_rails_permission(request, actor)
    rail_service = _build_wallet_rail_service(request, session)
    try:
        quote = rail_service.quote_market_topup(amount=payload.amount, fee_bps=payload.fee_bps, unit=payload.unit)
    except WalletRailError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MarketTopupQuoteView(
        gross_amount=quote.gross_amount,
        fee_amount=quote.fee_amount,
        net_amount=quote.net_amount,
        unit=quote.unit,
    )


@admin_router.post("/market-topups", response_model=MarketTopupView, status_code=status.HTTP_201_CREATED)
def create_market_topup(
    payload: MarketTopupCreateRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
) -> MarketTopupView:
    _require_payment_rails_permission(request, actor)
    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")
    rail_service = _build_wallet_rail_service(request, session)
    try:
        topup = rail_service.create_market_topup(
            user=user,
            amount=payload.amount,
            fee_bps=payload.fee_bps,
            unit=payload.unit,
            source_scope=payload.source_scope.value,
            notes=payload.notes,
            requested_by=actor,
        )
        session.commit()
        session.refresh(topup)
    except WalletRailError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MarketTopupView.model_validate(topup)


@admin_router.get("/market-topups", response_model=list[MarketTopupView])
def list_admin_market_topups(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[MarketTopupView]:
    _require_payment_rails_permission(request, actor)
    query = select(MarketTopup)
    if status_filter:
        try:
            status_value = MarketTopupStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        query = query.where(MarketTopup.status == status_value)
    if user_id:
        query = query.where(MarketTopup.user_id == user_id)
    topups = session.scalars(
        query.order_by(MarketTopup.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return [MarketTopupView.model_validate(item) for item in topups]


@admin_router.post("/market-topups/{topup_id}/status", response_model=MarketTopupView)
def update_market_topup_status(
    topup_id: str,
    payload: MarketTopupStatusUpdate,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
) -> MarketTopupView:
    _require_payment_rails_permission(request, actor)
    topup = session.get(MarketTopup, topup_id)
    if topup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market topup not found.")
    try:
        status_value = MarketTopupStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    rail_service = _build_wallet_rail_service(request, session)
    topup = rail_service.apply_market_topup_status(topup=topup, status=status_value, actor=actor, notes=payload.notes)
    RiskOpsService(session).log_audit(
        actor_user_id=actor.id,
        action_key="wallet.market_topup.status_changed",
        resource_type="market_topup",
        resource_id=topup.id,
        detail=f"Market topup set to {status_value.value}.",
        metadata_json={"status": status_value.value, "reference": topup.reference},
    )
    session.commit()
    session.refresh(topup)
    return MarketTopupView.model_validate(topup)


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
    policy_service = PolicyService(session)
    compliance_policy = policy_service.get_country_policy_for_user(user=current_user)
    missing_policies = policy_service.list_missing_acceptances(user_id=current_user.id)
    deposit_mode = "bank_transfer" if settings.deposit_mode == PaymentMode.MANUAL else _selected_deposit_mode(policy)
    if not compliance_policy.deposits_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deposits are currently disabled for country policy '{compliance_policy.country_code}'.",
        )
    if missing_policies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accept the latest required policies before using automatic gateway deposits.",
        )
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
router.include_router(admin_router)
router.include_router(orders_legacy_router)
router.include_router(orders_api_router, generate_unique_id_function=_api_operation_id)
api_router.include_router(wallet_router, generate_unique_id_function=_api_operation_id)
api_router.include_router(portfolio_router, generate_unique_id_function=_api_operation_id)
router.include_router(api_router)
