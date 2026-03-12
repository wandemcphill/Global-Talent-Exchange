from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Query, Request

from backend.app.auth.dependencies import get_current_user
from backend.app.match_engine.services import ensure_local_match_execution_runtime
from backend.app.models.user import User
from backend.app.notifications.schemas import NotificationView
from backend.app.replay_archive.router import router as replay_router
from backend.app.replay_archive.service import ensure_replay_archive


@asynccontextmanager
async def _support_router_lifespan(app: FastAPI):
    ensure_replay_archive(app)
    ensure_local_match_execution_runtime(app)
    yield


router = APIRouter(lifespan=_support_router_lifespan)
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("/me", response_model=list[NotificationView])
def list_notifications(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[NotificationView]:
    notifications = request.app.state.notifications.list_for_user(current_user.id, limit=limit)
    return [NotificationView.model_validate(item) for item in notifications]


router.include_router(notifications_router)
router.include_router(replay_router)
