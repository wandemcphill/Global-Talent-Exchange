from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_optional_current_user, get_session
from app.models.user import User

from .schemas import (
    AdminCommandRouteView,
    BetaAccessGrantRequest,
    BetaAccessGrantView,
    ClientFeatureFlagView,
    LaunchControlDashboardView,
    LaunchControlFeatureFlagView,
    LaunchControlFlagUpdateRequest,
    LaunchControlKillSwitchRequest,
    LaunchControlReasonRequest,
    ModuleHealthView,
)
from .service import LaunchControlService

router = APIRouter(tags=["launch-control"])


@router.get("/admin/launch-control", response_model=LaunchControlDashboardView)
def get_launch_control_dashboard(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> LaunchControlDashboardView:
    return LaunchControlService(session).dashboard()


@router.get("/admin/feature-flags", response_model=list[LaunchControlFeatureFlagView])
def list_feature_flags(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[LaunchControlFeatureFlagView]:
    service = LaunchControlService(session)
    return [service.map_flag(flag) for flag in service.list_flags()]


@router.patch("/admin/feature-flags/{feature_key}", response_model=LaunchControlFeatureFlagView)
def update_feature_flag(
    feature_key: str,
    payload: LaunchControlFlagUpdateRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> LaunchControlFeatureFlagView:
    service = LaunchControlService(session)
    flag = service.update_flag(actor=actor, feature_key=feature_key, payload=payload)
    session.commit()
    session.refresh(flag)
    return service.map_flag(flag)


@router.post("/admin/feature-flags/{feature_key}/enable", response_model=LaunchControlFeatureFlagView)
def enable_feature_flag(
    feature_key: str,
    payload: LaunchControlReasonRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> LaunchControlFeatureFlagView:
    service = LaunchControlService(session)
    flag = service.set_enabled(actor=actor, feature_key=feature_key, enabled=True, reason=payload.reason if payload else None)
    session.commit()
    session.refresh(flag)
    return service.map_flag(flag)


@router.post("/admin/feature-flags/{feature_key}/disable", response_model=LaunchControlFeatureFlagView)
def disable_feature_flag(
    feature_key: str,
    payload: LaunchControlReasonRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> LaunchControlFeatureFlagView:
    service = LaunchControlService(session)
    flag = service.set_enabled(actor=actor, feature_key=feature_key, enabled=False, reason=payload.reason if payload else None)
    session.commit()
    session.refresh(flag)
    return service.map_flag(flag)


@router.post("/admin/feature-flags/{feature_key}/kill-switch", response_model=LaunchControlFeatureFlagView)
def set_feature_flag_kill_switch(
    feature_key: str,
    payload: LaunchControlKillSwitchRequest | None = None,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> LaunchControlFeatureFlagView:
    resolved_payload = payload or LaunchControlKillSwitchRequest()
    service = LaunchControlService(session)
    flag = service.set_kill_switch(
        actor=actor,
        feature_key=feature_key,
        enabled=resolved_payload.enabled,
        reason=resolved_payload.reason,
    )
    session.commit()
    session.refresh(flag)
    return service.map_flag(flag)


@router.get("/admin/command-router", response_model=list[AdminCommandRouteView])
def get_admin_command_router(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[AdminCommandRouteView]:
    return LaunchControlService(session).command_router()


@router.get("/admin/modules/health", response_model=list[ModuleHealthView])
def get_admin_modules_health(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[ModuleHealthView]:
    return LaunchControlService(session).module_health()


@router.get("/admin/beta-access", response_model=list[BetaAccessGrantView])
def list_beta_access_grants(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[BetaAccessGrantView]:
    service = LaunchControlService(session)
    return [service.map_beta_grant(grant) for grant in service.list_beta_grants()]


@router.post("/admin/beta-access", response_model=BetaAccessGrantView)
def upsert_beta_access_grant(
    payload: BetaAccessGrantRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> BetaAccessGrantView:
    service = LaunchControlService(session)
    try:
        grant = service.upsert_beta_grant(actor=actor, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    session.refresh(grant)
    return service.map_beta_grant(grant)


@router.delete("/admin/beta-access/{feature_key}/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_beta_access_grant(
    feature_key: str,
    user_id: str,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> Response:
    service = LaunchControlService(session)
    try:
        service.revoke_beta_grant(actor=actor, feature_key=feature_key, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/feature-flags/client", response_model=list[ClientFeatureFlagView])
def list_client_feature_flags(
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> list[ClientFeatureFlagView]:
    return LaunchControlService(session).client_flags(user=current_user)
