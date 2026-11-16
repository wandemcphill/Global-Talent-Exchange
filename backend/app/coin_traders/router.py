from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.admin.capabilities import AdminCapability, assert_admin_capability
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.coin_traders.schemas import (
    CoinTraderAdminAdvertPauseRequest,
    CoinTraderAdminAuditLogView,
    CoinTraderAdminConfigUpdateRequest,
    CoinTraderAdminLiquidityRequest,
    CoinTraderAdminLiquidityTransferView,
    CoinTraderAdminOverviewView,
    CoinTradeAdminResolutionRequest,
    CoinTradeDisputeRequest,
    CoinTradeMessageCreateRequest,
    CoinTradeMessageView,
    CoinTradeOrderCreateRequest,
    CoinTradeOrderQuoteRequest,
    CoinTradeOrderQuoteView,
    CoinTradeOrderView,
    CoinTradeProofRequest,
    CoinTradeRatingCreateRequest,
    CoinTradeRatingView,
    CoinTraderAdminDecisionRequest,
    CoinTraderAdminRejectRequest,
    CoinTraderAdvertStatusUpdateRequest,
    CoinTraderAdvertUpsertRequest,
    CoinTraderAdvertView,
    CoinTraderDashboardView,
    CoinTraderMarketReferenceView,
    CoinTraderMarketplaceResponse,
    CoinTraderProfileCreateRequest,
    CoinTraderProfileUpdateRequest,
    CoinTraderProfileView,
    CoinTraderPublicProfileView,
    CoinTraderRateUpsertRequest,
    CoinTraderRateView,
    CoinTraderLiquidityQuoteRequest,
    CoinTraderLiquidityQuoteView,
    CoinTraderLiquidityPurchaseRequest,
    CoinTraderLiquidityPurchaseSessionView,
)
from app.coin_traders.service import (
    CoinTraderNotFoundError,
    CoinTraderPermissionError,
    CoinTraderService,
    CoinTraderValidationError,
)
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.wallets.service import InsufficientBalanceError

router = APIRouter(tags=["coin-traders"])
admin_router = APIRouter(tags=["admin-coin-traders"])


def _service(session: Session = Depends(get_session)) -> CoinTraderService:
    return CoinTraderService(session)


def _raise_coin_trader_error(exc: Exception) -> None:
    if isinstance(exc, CoinTraderNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CoinTraderPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, (CoinTraderValidationError, InsufficientBalanceError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _require_liquidity_desk_permission(request: Request, actor: User) -> None:
    assert_admin_capability(request, actor, AdminCapability.MANAGE_LIQUIDITY_DESK)


@router.get("/api/coin-traders", response_model=list[CoinTraderPublicProfileView])
def list_coin_traders(
    country_code: str | None = Query(default=None),
    coin_unit: LedgerUnit | None = Query(default=None),
    service: CoinTraderService = Depends(_service),
) -> list[CoinTraderPublicProfileView]:
    return service.list_traders(country_code=country_code, coin_unit=coin_unit)


@router.get("/api/coin-traders/market-reference", response_model=CoinTraderMarketReferenceView)
def get_coin_trader_market_reference(
    service: CoinTraderService = Depends(_service),
) -> CoinTraderMarketReferenceView:
    return service.marketplace.get_market_reference()


@router.get("/api/coin-traders/marketplace", response_model=CoinTraderMarketplaceResponse)
def list_coin_trader_marketplace_offers(
    coin_unit: LedgerUnit = Query(default=LedgerUnit.COIN),
    side: str = Query(default="sell"),
    fiat_currency: str = Query(default="NGN"),
    fiat_amount: Decimal | None = Query(default=None, gt=0),
    payment_method: str | None = Query(default=None),
    verified_only: bool = Query(default=False),
    min_completion_rate: float | None = Query(default=None, ge=0, le=100),
    min_available_coin: Decimal | None = Query(default=None, gt=0),
    country_code: str | None = Query(default=None),
    sort_by: str | None = Query(default=None),
    service: CoinTraderService = Depends(_service),
) -> CoinTraderMarketplaceResponse:
    try:
        return service.marketplace.list_marketplace_offers(
            coin_unit=coin_unit,
            side=side,
            fiat_currency=fiat_currency,
            fiat_amount=fiat_amount,
            payment_method=payment_method,
            verified_only=verified_only,
            min_completion_rate=min_completion_rate,
            min_available_coin=min_available_coin,
            country_code=country_code,
            sort_by=sort_by,
        )
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders/quote", response_model=CoinTradeOrderQuoteView)
def quote_coin_trader_order(
    payload: CoinTradeOrderQuoteRequest,
    service: CoinTraderService = Depends(_service),
) -> CoinTradeOrderQuoteView:
    try:
        return service.marketplace.quote_advert_order(payload)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.get("/api/coin-traders/me", response_model=CoinTraderProfileView)
def get_my_coin_trader_profile(
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderProfileView:
    try:
        return service.get_my_profile(current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.get("/api/coin-traders/me/dashboard", response_model=CoinTraderDashboardView)
def get_my_coin_trader_dashboard(
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderDashboardView:
    try:
        return service.marketplace.get_merchant_dashboard(actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.get("/api/coin-traders/me/adverts", response_model=list[CoinTraderAdvertView])
def list_my_coin_trader_adverts(
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> list[CoinTraderAdvertView]:
    try:
        return service.marketplace.list_my_adverts(actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.put("/api/coin-traders/me/adverts", response_model=CoinTraderAdvertView)
@router.post("/api/coin-traders/me/adverts", response_model=CoinTraderAdvertView)
def upsert_my_coin_trader_advert(
    payload: CoinTraderAdvertUpsertRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderAdvertView:
    try:
        return service.marketplace.upsert_my_advert(payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.patch("/api/coin-traders/me/adverts/{advert_id}/status", response_model=CoinTraderAdvertView)
@router.post("/api/coin-traders/me/adverts/{advert_id}/status", response_model=CoinTraderAdvertView)
def update_my_coin_trader_advert_status(
    advert_id: str,
    payload: CoinTraderAdvertStatusUpdateRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderAdvertView:
    try:
        return service.marketplace.update_my_advert_status(advert_id, payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/apply", response_model=CoinTraderProfileView, status_code=status.HTTP_201_CREATED)
def apply_for_coin_trader_profile(
    payload: CoinTraderProfileCreateRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderProfileView:
    try:
        return service.create_or_update_profile(payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.put("/api/coin-traders/me", response_model=CoinTraderProfileView)
def update_my_coin_trader_profile(
    payload: CoinTraderProfileUpdateRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderProfileView:
    try:
        return service.update_my_profile(payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.put("/api/coin-traders/me/rates", response_model=CoinTraderRateView)
def upsert_my_coin_trader_rate(
    payload: CoinTraderRateUpsertRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderRateView:
    try:
        return service.upsert_rate(payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/me/liquidity/quote", response_model=CoinTraderLiquidityQuoteView)
def quote_my_liquidity_purchase(
    payload: CoinTraderLiquidityQuoteRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderLiquidityQuoteView:
    try:
        quote = service.quote_liquidity_purchase(
            actor=current_user,
            amount=payload.amount,
            provider=payload.provider,
            coin_unit=payload.coin_unit,
            input_unit=payload.input_unit,
        )
        return CoinTraderLiquidityQuoteView.model_validate(quote)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/me/liquidity/purchase", response_model=CoinTraderLiquidityPurchaseSessionView)
def initiate_my_liquidity_purchase(
    payload: CoinTraderLiquidityPurchaseRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderLiquidityPurchaseSessionView:
    try:
        session_data = service.initiate_liquidity_purchase(
            actor=current_user,
            amount=payload.amount,
            provider=payload.provider,
            coin_unit=payload.coin_unit,
            callback_url=payload.callback_url,
        )
        return CoinTraderLiquidityPurchaseSessionView.model_validate(session_data)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/me/liquidity/verify/{reference}")
def verify_my_liquidity_purchase(
    reference: str,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        return service.verify_liquidity_purchase(
            actor=current_user,
            reference=reference,
        )
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders", response_model=CoinTradeOrderView, status_code=status.HTTP_201_CREATED)
def create_coin_trade_order(
    payload: CoinTradeOrderCreateRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeOrderView:
    try:
        return service.create_order(payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.get("/api/coin-traders/orders", response_model=list[CoinTradeOrderView])
def list_my_coin_trade_orders(
    as_trader: bool = Query(default=False),
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> list[CoinTradeOrderView]:
    try:
        return service.list_orders(actor=current_user, trader=as_trader)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders/{order_id}/accept", response_model=CoinTradeOrderView)
def accept_coin_trade_order(
    order_id: str,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeOrderView:
    try:
        return service.accept_order(order_id, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders/{order_id}/proof", response_model=CoinTradeOrderView)
def submit_coin_trade_order_proof(
    order_id: str,
    payload: CoinTradeProofRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeOrderView:
    try:
        return service.submit_proof(order_id, payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders/{order_id}/confirm", response_model=CoinTradeOrderView)
def confirm_coin_trade_order(
    order_id: str,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeOrderView:
    try:
        return service.confirm_and_release(order_id, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders/{order_id}/cancel", response_model=CoinTradeOrderView)
def cancel_coin_trade_order(
    order_id: str,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeOrderView:
    try:
        return service.cancel_order(order_id, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post("/api/coin-traders/orders/{order_id}/dispute", response_model=CoinTradeOrderView)
def dispute_coin_trade_order(
    order_id: str,
    payload: CoinTradeDisputeRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeOrderView:
    try:
        return service.dispute_order(order_id, payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post(
    "/api/coin-traders/orders/{order_id}/messages",
    response_model=CoinTradeMessageView,
    status_code=status.HTTP_201_CREATED,
)
def post_coin_trade_order_message(
    order_id: str,
    payload: CoinTradeMessageCreateRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeMessageView:
    try:
        return service.add_order_message(order_id, payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.get("/api/coin-traders/orders/{order_id}/messages", response_model=list[CoinTradeMessageView])
def list_coin_trade_order_messages(
    order_id: str,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> list[CoinTradeMessageView]:
    try:
        return service.list_order_messages(order_id, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.post(
    "/api/coin-traders/orders/{order_id}/rating",
    response_model=CoinTradeRatingView,
    status_code=status.HTTP_201_CREATED,
)
def rate_coin_trade_order(
    order_id: str,
    payload: CoinTradeRatingCreateRequest,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTradeRatingView:
    try:
        return service.marketplace.submit_order_rating(order_id, payload, actor=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@router.get("/api/coin-traders/{profile_id}", response_model=CoinTraderPublicProfileView)
def get_coin_trader_profile(
    profile_id: str, service: CoinTraderService = Depends(_service)
) -> CoinTraderPublicProfileView:
    try:
        return service.get_profile(profile_id)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.get("/api/admin/coin-traders", response_model=list[CoinTraderProfileView])
def admin_list_coin_traders(
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> list[CoinTraderProfileView]:
    _require_liquidity_desk_permission(request, current_user)
    return service.admin_list_profiles()


@admin_router.post("/api/admin/coin-traders/{profile_id}/approve", response_model=CoinTraderProfileView)
def admin_approve_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminDecisionRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderProfileView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.approve_trader(profile_id, payload, admin=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.post("/api/admin/coin-traders/{profile_id}/reject", response_model=CoinTraderProfileView)
def admin_reject_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminRejectRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderProfileView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.reject_trader(profile_id, payload, admin=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.post("/api/admin/coin-traders/{profile_id}/freeze", response_model=CoinTraderProfileView)
def admin_freeze_coin_trader(
    profile_id: str,
    payload: CoinTraderAdminRejectRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderProfileView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.freeze_trader(profile_id, admin=current_user, note=payload.note)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.get("/api/admin/coin-traders/orders", response_model=list[CoinTradeOrderView])
def admin_list_coin_trade_orders(
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> list[CoinTradeOrderView]:
    _require_liquidity_desk_permission(request, current_user)
    return service.admin_list_orders()


@admin_router.post(
    "/api/admin/coin-traders/{profile_id}/liquidity/issue",
    response_model=CoinTraderAdminLiquidityTransferView,
)
def admin_issue_coin_trader_liquidity(
    profile_id: str,
    payload: CoinTraderAdminLiquidityRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderAdminLiquidityTransferView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.admin_issue_liquidity(profile_id, payload, admin=current_user)
    except (
        CoinTraderNotFoundError,
        CoinTraderPermissionError,
        CoinTraderValidationError,
        InsufficientBalanceError,
    ) as exc:
        _raise_coin_trader_error(exc)


@admin_router.post(
    "/api/admin/coin-traders/{profile_id}/liquidity/redeem",
    response_model=CoinTraderAdminLiquidityTransferView,
)
def admin_redeem_coin_trader_liquidity(
    profile_id: str,
    payload: CoinTraderAdminLiquidityRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderAdminLiquidityTransferView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.admin_redeem_liquidity(profile_id, payload, admin=current_user)
    except (
        CoinTraderNotFoundError,
        CoinTraderPermissionError,
        CoinTraderValidationError,
        InsufficientBalanceError,
    ) as exc:
        _raise_coin_trader_error(exc)


@admin_router.post("/api/admin/coin-traders/orders/{order_id}/resolve", response_model=CoinTradeOrderView)
def admin_resolve_coin_trade_order(
    order_id: str,
    payload: CoinTradeAdminResolutionRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTradeOrderView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.admin_resolve_order(order_id, payload, admin=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.post(
    "/api/admin/coin-traders/orders/expire-stale",
    response_model=list[CoinTradeOrderView],
)
def admin_expire_stale_coin_trade_orders(
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> list[CoinTradeOrderView]:
    _require_liquidity_desk_permission(request, current_user)
    return service.expire_stale_orders()


@admin_router.get("/api/admin/coin-traders/overview", response_model=CoinTraderAdminOverviewView)
def admin_coin_trader_overview(
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderAdminOverviewView:
    _require_liquidity_desk_permission(request, current_user)
    return service.marketplace.admin_overview()


@admin_router.get("/api/admin/coin-traders/adverts", response_model=list[CoinTraderAdvertView])
def admin_list_coin_trader_adverts(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> list[CoinTraderAdvertView]:
    _require_liquidity_desk_permission(request, current_user)
    return service.marketplace.admin_list_adverts(status_filter=status_filter)


@admin_router.post("/api/admin/coin-traders/adverts/{advert_id}/pause", response_model=CoinTraderAdvertView)
def admin_pause_coin_trader_advert(
    advert_id: str,
    payload: CoinTraderAdminAdvertPauseRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderAdvertView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.marketplace.admin_pause_advert(advert_id, payload, admin=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.post("/api/admin/coin-traders/adverts/{advert_id}/resume", response_model=CoinTraderAdvertView)
def admin_resume_coin_trader_advert(
    advert_id: str,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderAdvertView:
    _require_liquidity_desk_permission(request, current_user)
    try:
        return service.marketplace.admin_resume_advert(advert_id, admin=current_user)
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
        _raise_coin_trader_error(exc)


@admin_router.get("/api/admin/coin-traders/audit-logs", response_model=list[CoinTraderAdminAuditLogView])
def admin_list_coin_trader_audit_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=250),
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> list[CoinTraderAdminAuditLogView]:
    _require_liquidity_desk_permission(request, current_user)
    return service.marketplace.admin_list_audit_logs(limit=limit)


@admin_router.get("/api/admin/coin-traders/config", response_model=CoinTraderMarketReferenceView)
def admin_get_coin_trader_config(
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderMarketReferenceView:
    _require_liquidity_desk_permission(request, current_user)
    return service.marketplace.get_market_reference()


@admin_router.put("/api/admin/coin-traders/config", response_model=CoinTraderMarketReferenceView)
def admin_update_coin_trader_config(
    payload: CoinTraderAdminConfigUpdateRequest,
    request: Request,
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_admin),
) -> CoinTraderMarketReferenceView:
    _require_liquidity_desk_permission(request, current_user)
    return service.marketplace.admin_update_config(payload, admin=current_user)


__all__ = ["admin_router", "router"]
