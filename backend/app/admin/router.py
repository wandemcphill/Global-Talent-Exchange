from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.models.user import User

from .schemas import (
    LiquidityBandConfigPayload,
    SupplyTierConfigPayload,
    SuspicionThresholdsPayload,
    ValueControlsPayload,
)
from .service import ConfigAdminService

router = APIRouter(prefix="/admin/config", tags=["admin"])


def get_config_admin_service() -> ConfigAdminService:
    return ConfigAdminService()


@router.get("/supply-tiers", response_model=SupplyTierConfigPayload)
def get_supply_tiers(
    request: Request,
    _: User = Depends(get_current_admin),
) -> SupplyTierConfigPayload:
    return SupplyTierConfigPayload.model_validate(request.app.state.settings.supply_tiers)


@router.put("/supply-tiers", response_model=SupplyTierConfigPayload)
def update_supply_tiers(
    payload: SupplyTierConfigPayload,
    request: Request,
    session: Session = Depends(get_session),
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> SupplyTierConfigPayload:
    try:
        settings = service.update_supply_tiers(request.app, session, payload.to_domain())
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SupplyTierConfigPayload.model_validate(settings.supply_tiers)


@router.get("/liquidity-bands", response_model=LiquidityBandConfigPayload)
def get_liquidity_bands(
    request: Request,
    _: User = Depends(get_current_admin),
) -> LiquidityBandConfigPayload:
    return LiquidityBandConfigPayload.model_validate(request.app.state.settings.liquidity_bands)


@router.put("/liquidity-bands", response_model=LiquidityBandConfigPayload)
def update_liquidity_bands(
    payload: LiquidityBandConfigPayload,
    request: Request,
    session: Session = Depends(get_session),
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> LiquidityBandConfigPayload:
    try:
        settings = service.update_liquidity_bands(request.app, session, payload.to_domain())
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LiquidityBandConfigPayload.model_validate(settings.liquidity_bands)


@router.get("/suspicion-thresholds", response_model=SuspicionThresholdsPayload)
def get_suspicion_thresholds(
    request: Request,
    _: User = Depends(get_current_admin),
) -> SuspicionThresholdsPayload:
    return SuspicionThresholdsPayload.model_validate(request.app.state.settings.suspicion_thresholds)


@router.put("/suspicion-thresholds", response_model=SuspicionThresholdsPayload)
def update_suspicion_thresholds(
    payload: SuspicionThresholdsPayload,
    request: Request,
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> SuspicionThresholdsPayload:
    try:
        settings = service.update_suspicion_thresholds(request.app, payload.to_domain())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SuspicionThresholdsPayload.model_validate(settings.suspicion_thresholds)


@router.get("/value-controls", response_model=ValueControlsPayload)
def get_value_controls(
    request: Request,
    _: User = Depends(get_current_admin),
) -> ValueControlsPayload:
    return ValueControlsPayload.model_validate(
        {
            "ftv_msv_blend_weights": {
                "ftv_weight": request.app.state.settings.value_engine_weighting.ftv_weight,
                "msv_weight": request.app.state.settings.value_engine_weighting.msv_weight,
            },
            "price_band_limits": request.app.state.settings.value_engine_weighting.price_band_limits,
        }
    )


@router.put("/value-controls", response_model=ValueControlsPayload)
def update_value_controls(
    payload: ValueControlsPayload,
    request: Request,
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> ValueControlsPayload:
    try:
        updated_config = payload.merge_into(request.app.state.settings.value_engine_weighting)
        settings = service.update_value_controls(request.app, updated_config)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ValueControlsPayload.model_validate(
        {
            "ftv_msv_blend_weights": {
                "ftv_weight": settings.value_engine_weighting.ftv_weight,
                "msv_weight": settings.value_engine_weighting.msv_weight,
            },
            "price_band_limits": settings.value_engine_weighting.price_band_limits,
        }
    )
