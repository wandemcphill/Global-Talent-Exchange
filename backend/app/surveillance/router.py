from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.models.user import User

from .schemas import (
    CircularTradeAlertView,
    HolderConcentrationAlertView,
    SuspiciousClusterAlertView,
    SuspiciousPlayerAlertView,
    ThinMarketAlertView,
)
from .service import SurveillanceService

router = APIRouter(prefix="/surveillance", tags=["surveillance"])


def get_surveillance_service(request: Request) -> SurveillanceService:
    return SurveillanceService(settings=request.app.state.settings)


@router.get("/suspicious-players", response_model=list[SuspiciousPlayerAlertView])
def list_suspicious_players(
    request: Request,
    session: Session = Depends(get_session),
    service: SurveillanceService = Depends(get_surveillance_service),
    lookback_days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> list[SuspiciousPlayerAlertView]:
    return [
        SuspiciousPlayerAlertView.model_validate(alert)
        for alert in service.list_suspicious_players(session, lookback_days=lookback_days, limit=limit)
    ]


@router.get("/suspicious-clusters", response_model=list[SuspiciousClusterAlertView])
def list_suspicious_clusters(
    request: Request,
    service: SurveillanceService = Depends(get_surveillance_service),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> list[SuspiciousClusterAlertView]:
    return [
        SuspiciousClusterAlertView.model_validate(alert)
        for alert in service.list_suspicious_clusters(request.app.state.market_engine, limit=limit)
    ]


@router.get("/thin-market-alerts", response_model=list[ThinMarketAlertView])
def list_thin_market_alerts(
    request: Request,
    session: Session = Depends(get_session),
    service: SurveillanceService = Depends(get_surveillance_service),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> list[ThinMarketAlertView]:
    return [
        ThinMarketAlertView.model_validate(alert)
        for alert in service.list_thin_market_alerts(session, limit=limit)
    ]


@router.get("/holder-concentration-alerts", response_model=list[HolderConcentrationAlertView])
def list_holder_concentration_alerts(
    request: Request,
    service: SurveillanceService = Depends(get_surveillance_service),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> list[HolderConcentrationAlertView]:
    return [
        HolderConcentrationAlertView.model_validate(alert)
        for alert in service.list_holder_concentration_alerts(request.app.state.market_engine, limit=limit)
    ]


@router.get("/circular-trade-alerts", response_model=list[CircularTradeAlertView])
def list_circular_trade_alerts(
    request: Request,
    service: SurveillanceService = Depends(get_surveillance_service),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> list[CircularTradeAlertView]:
    return [
        CircularTradeAlertView.model_validate(alert)
        for alert in service.list_circular_trade_alerts(request.app.state.market_engine, limit=limit)
    ]
