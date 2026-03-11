from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.notifications.schemas import NotificationView

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=list[NotificationView])
def list_notifications(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[NotificationView]:
    notifications = request.app.state.notifications.list_for_user(current_user.id, limit=limit)
    return [NotificationView.model_validate(item) for item in notifications]
