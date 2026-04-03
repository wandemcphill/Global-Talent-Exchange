from __future__ import annotations

from contextlib import contextmanager
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pathlib import Path
import json
from decimal import Decimal
from fastapi.routing import APIRoute
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin_finance.service import AdminFinanceService
from app.auth.dependencies import get_current_admin, get_current_user, get_current_wallet_user, get_session
from app.admin_godmode.service import (
    AdminGodModeService,
    DEFAULT_COMMISSION_SETTINGS,
    DEFAULT_WITHDRAWAL_CONTROLS,
)
from app.economy.governor_service import EconomyGovernorService
from app.models.user import User
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.market_topup import MarketTopup, MarketTopupStatus
from app.policies.service import PolicyService
from app.orders.router import (
    api_router as orders_api_router,
    legacy_router as orders_legacy_router,
)
from app.portfolio.router import router as portfolio_router
from app.wallets.schemas import (
    PaymentEventCreate,
    PaymentEventView,
    PortfolioSnapshotView,
    PurchaseOrderCreateRequest,
    PurchaseOrderQuoteRequest,
    PurchaseOrderQuoteView,
    PurchaseOrderSourceScope,
    PurchaseOrderStatusUpdate,
    PurchaseOrderView,
    PurchaseOrderPageView,
    MarketTopupCreateRequest,
    MarketTopupQuoteRequest,
    MarketTopupQuoteView,
    MarketTopupStatusUpdate,
    MarketTopupView,
    MarketTopupPageView,
    WalletAccountBalance,
    WalletConversionQuoteRequest,
    WalletConversionQuoteView,
    WalletConversionRequest,
    WalletConversionView,
    WalletLedgerEntryView,
    WalletLedgerPageView,
    WalletSummaryView,
    WalletAdaptiveOverviewView,
    WalletOverviewView,
    WalletProfileView,
    WalletTopUpInitiateRequest,
    WalletTopUpInitiateView,
    WalletTopUpVerifyRequest,
    WalletTopUpVerifyAcceptedView,
    WalletTransactionRecordView,
)
from app.core.pagination import build_pagination_meta, resolve_pagination
from app.core.task_queue import NullTaskQueueBackend, get_task_queue_backend
from app.wallets.funding_service import (
    WalletFundingError,
    WalletFundingService,
)
from app.wallets.service import LedgerError, WalletService
from app.wallets.rail_service import WalletRailError, WalletRailConflictError, WalletRailService
from app.wallets.providers import get_provider_adapter
from app.models.wallet import LedgerEntry, LedgerUnit, PayoutRequest
from app.risk_ops_engine.service import RiskOpsService
from app.services.runtime_control_service import RuntimeControlService, WalletTransactionLockConflict
from app.models.treasury import DepositRequest, DepositStatus, PaymentMode, TreasurySettings, TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from app.treasury.schemas import (
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
from app.treasury.service import TreasuryConflictError, TreasuryService
from app.workers.jobs import verify_wallet_top_up_job

router = APIRouter()
wallet_router = APIRouter(prefix="/wallets", tags=["wallets"])
public_wallet_router = APIRouter(prefix="/wallet", tags=["wallet"])
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin/wallets", tags=["admin-wallets"])


def _api_operation_id(route: APIRoute) -> str:
    path = route.path_format.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    methods = "_".join(sorted(method.lower() for method in (route.methods or set())))
    return f"api_{route.name}_{path}_{methods}"


def _build_wallet_service(request: Request | None) -> WalletService:
    if request is not None:
        return WalletService(
            event_publisher=getattr(request.app.state, "event_publisher", None),
            cache_backend=getattr(request.app.state, "cache_backend", None),
        )
    return WalletService()


def _build_treasury_service(request: Request | None) -> TreasuryService:
    if request is not None:
        return TreasuryService(
            wallet_service=WalletService(
                event_publisher=getattr(request.app.state, "event_publisher", None),
                cache_backend=getattr(request.app.state, "cache_backend", None),
            )
        )
    return TreasuryService()


def _build_wallet_funding_service(request: Request | None) -> WalletFundingService:
    wallet_service = _build_wallet_service(request)
    return WalletFundingService(
        wallet_service=wallet_service,
        treasury_service=TreasuryService(wallet_service=wallet_service),
    )


def _build_wallet_rail_service(request: Request | None, session: Session) -> WalletRailService:
    event_publisher = None
    if request is not None and hasattr(request.app.state, "event_publisher"):
        event_publisher = request.app.state.event_publisher
    return WalletRailService(session=session, wallet_service=_build_wallet_service(request), event_publisher=event_publisher)


def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0.0000")
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _require_payment_rails_permission(request: Request, actor: User) -> None:
    service = AdminGodModeService(wallet_service=_build_wallet_service(request))
    state = service._load_state(request.app)
    profile = service.resolve_profile(actor, state)
    service._assert_has_permission(profile, "manage_payment_rails")


@contextmanager
def _wallet_transaction_lock(
    request: Request | None,
    *,
    user: User,
    operation: str,
    ttl_seconds: int = 90,
):
    if request is None:
        yield
        return
    control_service = RuntimeControlService(request.app)
    try:
        control_service.acquire_wallet_transaction_lock(
            user_id=user.id,
            operation=operation,
            ttl_seconds=ttl_seconds,
            reason="wallet_transaction_in_flight",
            updated_by_user_id=user.id,
        )
    except WalletTransactionLockConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another wallet transaction is already in progress for this account. Retry in a moment.",
        ) from exc
    try:
        yield
    finally:
        control_service.release_wallet_transaction_lock(user_id=user.id, operation=operation)




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
    legal_disclosures = meta.get("legal_disclosures")
    if isinstance(legal_disclosures, (list, tuple)):
        disclosure_items = [str(item) for item in legal_disclosures]
    else:
        disclosure_items = list(TreasuryService().legal_disclosures())
    platform_positioning = str(meta.get("platform_positioning") or TreasuryService.platform_positioning())
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
        platform_positioning=platform_positioning,
        legal_disclosures=disclosure_items,
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
    use_manual_payout = settings.withdrawal_mode in {PaymentMode.MANUAL, PaymentMode.HYBRID}
    payout_channel = "bank_transfer" if use_manual_payout else "gateway"
    processor_mode = "manual_bank_transfer" if use_manual_payout else "automatic_gateway"
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
        estimated_fiat_payout=_normalize_amount(estimated_fiat),
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
            kyc_tier=eligibility.kyc_tier,
            per_request_limit_fiat=eligibility.per_request_limit_fiat,
            requires_kyc=eligibility.requires_kyc,
            requires_bank_account=eligibility.requires_bank_account,
            pending_withdrawals=eligibility.pending_withdrawals,
            country_code=eligibility.country_code,
            country_withdrawals_enabled=eligibility.country_withdrawals_enabled,
            missing_required_policies=list(eligibility.missing_required_policies),
            policy_blocked=eligibility.policy_blocked,
            policy_block_reason=eligibility.policy_block_reason,
            platform_positioning=eligibility.platform_positioning,
            legal_disclosures=list(eligibility.legal_disclosures),
        ),
        blocked_reason=blocked_reason,
        platform_positioning=eligibility.platform_positioning,
        legal_disclosures=list(eligibility.legal_disclosures),
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
    deposit_mode = "bank_transfer" if settings.deposit_mode == PaymentMode.MANUAL else _selected_deposit_mode(policy)
    if not compliance_policy.deposits_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deposits are currently disabled for country policy '{compliance_policy.country_code}'.",
        )
    if deposit_mode != "gateway":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Automatic gateway deposits are disabled. Admin has selected manual bank transfer as the active funding rail.",
        )
    processor_mode = "automatic_gateway"
    payout_channel = "gateway"
    return settings, processor_mode, payout_channel


@public_wallet_router.get("", response_model=WalletProfileView)
def get_wallet_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> WalletProfileView:
    wallet = _build_wallet_funding_service(request).get_wallet(session, current_user)
    return WalletProfileView.model_validate(wallet)


@public_wallet_router.get("/transactions", response_model=list[WalletTransactionRecordView])
def list_wallet_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> list[WalletTransactionRecordView]:
    transactions = _build_wallet_funding_service(request).list_transactions(session, current_user, limit=limit)
    return [WalletTransactionRecordView.model_validate(item) for item in transactions]


@public_wallet_router.post("/top-up/initiate", response_model=WalletTopUpInitiateView, status_code=status.HTTP_201_CREATED)
def initiate_wallet_top_up(
    payload: WalletTopUpInitiateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> WalletTopUpInitiateView:
    service = _build_wallet_funding_service(request)
    try:
        with _wallet_transaction_lock(request, user=current_user, operation="wallet_top_up_initiate"):
            result = service.initiate_top_up(
                session,
                current_user,
                amount=payload.amount,
                provider=payload.provider,
                callback_url=payload.callback_url,
            )
            session.commit()
    except WalletFundingError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WalletTopUpInitiateView(
        reference=result.reference,
        payment_link=result.payment_link,
        amount=result.amount,
        currency=result.currency,
        provider=result.provider,
        status=result.status,
        mock_mode=result.mock_mode,
    )


@public_wallet_router.post(
    "/top-up/verify",
    response_model=WalletTopUpVerifyAcceptedView,
    status_code=status.HTTP_202_ACCEPTED,
)
def verify_wallet_top_up(
    payload: WalletTopUpVerifyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> WalletTopUpVerifyAcceptedView:
    del session
    normalized_reference = payload.reference.strip()
    if not normalized_reference:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A transaction reference is required.",
        )

    task_queue = get_task_queue_backend(request.app)
    if isinstance(task_queue, NullTaskQueueBackend):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wallet verification queue is unavailable.",
        )

    job_id = f"wallet-top-up-verify:{normalized_reference.lower()}"
    execution = task_queue.get(job_id)
    if execution is None:
        try:
            execution = task_queue.enqueue(
                name="wallet.verify_top_up",
                callable_=verify_wallet_top_up_job,
                kwargs={"user_id": current_user.id, "reference": normalized_reference},
                job_id=job_id,
                timeout_seconds=90,
                retry_intervals_seconds=(10, 30, 60),
                owner_user_id=current_user.id,
                meta={"reference": normalized_reference},
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Wallet verification queue is unavailable.",
            ) from exc
    return WalletTopUpVerifyAcceptedView(
        job_id=execution.job_id,
        name=execution.name,
        status=execution.status,
        queued_at=execution.queued_at,
        reference=normalized_reference,
    )


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
    currency: LedgerUnit = Query(default=LedgerUnit.CREDIT),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WalletSummaryView:
    service = _build_wallet_service(request)
    summary = service.get_wallet_summary(session, current_user, currency=currency)
    return WalletSummaryView(
        available_balance=summary.available_balance,
        reserved_balance=summary.reserved_balance,
        total_balance=summary.total_balance,
        currency=summary.currency,
    )


@wallet_router.post("/conversions/quote", response_model=WalletConversionQuoteView)
def quote_wallet_conversion(
    payload: WalletConversionQuoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> WalletConversionQuoteView:
    del current_user
    quote = EconomyGovernorService(session).quote_conversion(source_unit=payload.source_unit, amount=payload.amount)
    return WalletConversionQuoteView(
        source_unit=quote.source_unit,
        source_amount=quote.source_amount,
        target_unit=quote.target_unit,
        target_amount=quote.target_amount,
        rate=quote.rate,
    )


@wallet_router.post("/conversions", response_model=WalletConversionView, status_code=status.HTTP_201_CREATED)
def create_wallet_conversion(
    payload: WalletConversionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> WalletConversionView:
    try:
        with _wallet_transaction_lock(request, user=current_user, operation="wallet_conversion"):
            result = EconomyGovernorService(session).convert_wallet_units(
                user=current_user,
                amount=payload.amount,
                source_unit=payload.source_unit,
                actor=current_user,
                idempotency_key=payload.idempotency_key,
            )
            session.commit()
    except LedgerError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return WalletConversionView(
        transaction_id=result.transaction_id,
        reference=result.reference,
        source_unit=result.source_unit,
        source_amount=result.source_amount,
        target_unit=result.target_unit,
        target_amount=result.target_amount,
        rate=EconomyGovernorService(session).quote_conversion(source_unit=result.source_unit, amount=result.source_amount).rate,
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
    payout_mode = "bank_transfer" if settings.withdrawal_mode in {PaymentMode.MANUAL, PaymentMode.HYBRID} else "gateway"
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
    current_user: User = Depends(get_current_wallet_user),
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
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> PurchaseOrderView:
    try:
        get_provider_adapter(payload.provider_key)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    settings, processor_mode, payout_channel = _require_gateway_deposit(request=request, session=session, user=current_user)
    rail_service = _build_wallet_rail_service(request, session)
    try:
        with _wallet_transaction_lock(request, user=current_user, operation="purchase_order_create"):
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


@wallet_router.get("/purchase-orders", response_model=PurchaseOrderPageView)
def list_purchase_orders(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> PurchaseOrderPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)
    total = int(
        session.scalar(
            select(func.count())
            .select_from(FancoinPurchaseOrder)
            .where(FancoinPurchaseOrder.user_id == current_user.id)
        )
        or 0
    )
    orders = session.scalars(
        select(FancoinPurchaseOrder)
        .where(FancoinPurchaseOrder.user_id == current_user.id)
        .order_by(FancoinPurchaseOrder.created_at.desc())
        .offset(params.offset)
        .limit(params.per_page)
    ).all()
    return PurchaseOrderPageView(
        items=[PurchaseOrderView.model_validate(order) for order in orders],
        pagination=build_pagination_meta(params=params, total=total),
    )


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


@wallet_router.get("/market-topups", response_model=MarketTopupPageView)
def list_market_topups(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MarketTopupPageView:
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)
    total = int(
        session.scalar(
            select(func.count())
            .select_from(MarketTopup)
            .where(MarketTopup.user_id == current_user.id)
        )
        or 0
    )
    topups = session.scalars(
        select(MarketTopup)
        .where(MarketTopup.user_id == current_user.id)
        .order_by(MarketTopup.created_at.desc())
        .offset(params.offset)
        .limit(params.per_page)
    ).all()
    return MarketTopupPageView(
        items=[MarketTopupView.model_validate(item) for item in topups],
        pagination=build_pagination_meta(params=params, total=total),
    )


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
    current_user: User = Depends(get_current_wallet_user),
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
        platform_positioning=view.platform_positioning,
        legal_disclosures=view.legal_disclosures,
    )


@wallet_router.post("/withdrawals", response_model=TreasuryWithdrawalRequestView, status_code=status.HTTP_201_CREATED)
def create_withdrawal_request(
    payload: TreasuryWithdrawalRequestCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_wallet_user),
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
        with _wallet_transaction_lock(request, user=current_user, operation="withdrawal_request"):
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
        raw_body = await request.body()
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError:
        raw_body = b""
        payload = {}
    try:
        AdminFinanceService(session=session, settings=request.app.state.settings).verify_provider_webhook(
            provider_key=provider_key,
            payload=payload,
            raw_body=raw_body,
            headers=dict(request.headers),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
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


@admin_router.get("/purchase-orders", response_model=PurchaseOrderPageView)
def list_admin_purchase_orders(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
    status_filter: str | None = Query(default=None, alias="status"),
    provider_key: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
) -> PurchaseOrderPageView:
    _require_payment_rails_permission(request, actor)
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)
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
    total = int(session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    orders = session.scalars(
        query.order_by(FancoinPurchaseOrder.created_at.desc()).offset(params.offset).limit(params.per_page)
    ).all()
    return PurchaseOrderPageView(
        items=[PurchaseOrderView.model_validate(order) for order in orders],
        pagination=build_pagination_meta(params=params, total=total),
    )


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


@admin_router.get("/market-topups", response_model=MarketTopupPageView)
def list_admin_market_topups(
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
    request: Request = None,
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    limit: int | None = Query(default=None, ge=1, deprecated=True),
    offset: int | None = Query(default=None, ge=0, deprecated=True),
) -> MarketTopupPageView:
    _require_payment_rails_permission(request, actor)
    params = resolve_pagination(page=page, per_page=per_page, limit=limit, offset=offset)
    query = select(MarketTopup)
    if status_filter:
        try:
            status_value = MarketTopupStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        query = query.where(MarketTopup.status == status_value)
    if user_id:
        query = query.where(MarketTopup.user_id == user_id)
    total = int(session.scalar(select(func.count()).select_from(query.subquery())) or 0)
    topups = session.scalars(
        query.order_by(MarketTopup.created_at.desc()).offset(params.offset).limit(params.per_page)
    ).all()
    return MarketTopupPageView(
        items=[MarketTopupView.model_validate(item) for item in topups],
        pagination=build_pagination_meta(params=params, total=total),
    )


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
    current_user: User = Depends(get_current_wallet_user),
    request: Request = None,
) -> PaymentEventView:
    service = _build_wallet_service(request)
    policy = _build_withdrawal_policy_snapshot(request)
    treasury = _build_treasury_service(request)
    settings = treasury.ensure_settings(session)
    policy_service = PolicyService(session)
    compliance_policy = policy_service.get_country_policy_for_user(user=current_user)
    deposit_mode = "bank_transfer" if settings.deposit_mode == PaymentMode.MANUAL else _selected_deposit_mode(policy)
    if not compliance_policy.deposits_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deposits are currently disabled for country policy '{compliance_policy.country_code}'.",
        )
    if deposit_mode != "gateway":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Automatic gateway deposits are disabled. Admin has selected manual bank transfer as the active funding rail.",
        )
    try:
        with _wallet_transaction_lock(request, user=current_user, operation="payment_event_create"):
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


router.include_router(public_wallet_router)
router.include_router(wallet_router)
router.include_router(admin_router)
router.include_router(orders_legacy_router)
router.include_router(orders_api_router, generate_unique_id_function=_api_operation_id)
api_router.include_router(wallet_router, generate_unique_id_function=_api_operation_id)
api_router.include_router(portfolio_router, generate_unique_id_function=_api_operation_id)
router.include_router(api_router)
