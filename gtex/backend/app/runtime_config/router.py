from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.runtime_config.schemas import RuntimeConfigSnapshot, RuntimeConfigUpdateRequest
from app.runtime_config.service import RuntimeConfigService, ensure_runtime_config_loader

router = APIRouter()
config_router = APIRouter(prefix="/config", tags=["runtime-config"])


@config_router.get("/current", response_model=RuntimeConfigSnapshot)
def read_runtime_config(
    request: Request,
    _: User = Depends(get_current_admin),
) -> RuntimeConfigSnapshot:
    return ensure_runtime_config_loader(request.app).get_snapshot(force_refresh=True)


@config_router.post("/update", response_model=RuntimeConfigSnapshot)
def update_runtime_config(
    payload: RuntimeConfigUpdateRequest,
    request: Request,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> RuntimeConfigSnapshot:
    snapshot = RuntimeConfigService(
        session=session,
        settings=getattr(request.app.state, "settings", None),
    ).update(actor_id=actor.id, payload=payload)
    session.commit()
    ensure_runtime_config_loader(request.app).get_snapshot(force_refresh=True)
    request.app.state.runtime_config_loader._snapshot = snapshot
    return snapshot


router.include_router(config_router)
