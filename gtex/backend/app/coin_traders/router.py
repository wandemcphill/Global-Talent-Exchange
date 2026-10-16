from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.admin.capabilities import AdminCapability, assert_admin_capability
from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.coin_traders.schemas import (
    CoinTraderAdminLiquidityRequest,
    CoinTraderAdminLiquidityTransferView,
    CoinTradeAdminResolutionRequest,
    CoinTradeDisputeRequest,
    CoinTradeOrderCreateRequest,
    CoinTradeOrderView,
    CoinTradeProofRequest,
    CoinTraderAdminDecisionRequest,
    CoinTraderAdminRejectRequest,
    CoinTraderProfileCreateRequest,
    CoinTraderProfileUpdateRequest,
    CoinTraderProfileView,
    CoinTraderRateUpsertRequest,
    CoinTraderRateView,
)
from app.coin_traders.service import (
    CoinTraderNotFoundError,
    CoinTraderPermissionError,
    CoinTraderService,
    CoinTraderValidationError,
)
from app.models.user import User
from app.models.wallet import LedgerUnit

router = APIRouter(tags=["coin-traders"])
admin_router = APIRouter(tags=["admin-coin-traders"])


def _service(session: Session = Depends(get_session)) -> CoinTraderService:
    return CoinTraderService(session)


def _raise_coin_trader_error(exc: Exception) -> None:
    if isinstance(exc, CoinTraderNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CoinTraderPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, CoinTraderValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _require_liquidity_desk_permission(request: Request, actor: User) -> None:
    assert_admin_capability(request, actor, AdminCapability.MANAGE_LIQUIDITY_DESK)


@router.get("/api/coin-traders", response_model=list[CoinTraderProfileView])
def list_coin_traders(
    country_code: str | None = Query(default=None),
    coin_unit: LedgerUnit | None = Query(default=None),
    service: CoinTraderService = Depends(_service),
) -> list[CoinTraderProfileView]:
    return service.list_traders(country_code=country_code, coin_unit=coin_unit)


@router.get("/api/coin-traders/me", response_model=CoinTraderProfileView)
def get_my_coin_trader_profile(
    service: CoinTraderService = Depends(_service),
    current_user: User = Depends(get_current_user),
) -> CoinTraderProfileView:
    try:
        return service.get_my_profile(current_user)
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


@router.get("/api/coin-traders/{profile_id}", response_model=CoinTraderProfileView)
def get_coin_trader_profile(profile_id: str, service: CoinTraderService = Depends(_service)) -> CoinTraderProfileView:
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
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
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
    except (CoinTraderNotFoundError, CoinTraderPermissionError, CoinTraderValidationError) as exc:
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


__all__ = ["admin_router", "router"]
