from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_current_user, get_session
from app.models.user import User
from app.platform_experience.schemas import (
    PlatformBroadcastGuideView,
    PlatformModeView,
    PlatformSwitchRequest,
)
from app.platform_experience.service import PlatformExperienceService


router = APIRouter(tags=["platform-experience"])


def _service(request: Request, session: Session = Depends(get_session)) -> PlatformExperienceService:
    return PlatformExperienceService(session, app=request.app)


@router.get("/platform/mode", response_model=PlatformModeView)
def get_platform_mode(
    request: Request,
    device_id: str | None = Query(default=None),
    current_user: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> PlatformModeView:
    payload = PlatformExperienceService(session, app=request.app).get_mode(
        current_user=current_user,
        device_id=device_id,
    )
    return PlatformModeView.model_validate(payload)


@router.post("/platform/switch", response_model=PlatformModeView)
def switch_platform_mode(
    payload: PlatformSwitchRequest,
    service: PlatformExperienceService = Depends(_service),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PlatformModeView:
    response = service.switch_mode(current_user=current_user, payload=payload)
    session.commit()
    return PlatformModeView.model_validate(response)


@router.get("/broadcast/channels", response_model=PlatformBroadcastGuideView)
def get_broadcast_channels(
    service: PlatformExperienceService = Depends(_service),
    _: User | None = Depends(get_optional_current_user),
) -> PlatformBroadcastGuideView:
    return PlatformBroadcastGuideView.model_validate(service.broadcast_guide())


__all__ = ["router"]
