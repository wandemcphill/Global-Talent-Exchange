from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.match_engine.services import ensure_local_match_execution_runtime
from backend.app.models.user import User
from backend.app.models.notification_record import NotificationRecord
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
    session: Session = Depends(get_session),
) -> list[NotificationView]:
    db_items = session.scalars(
        select(NotificationRecord)
        .where(NotificationRecord.user_id == current_user.id)
        .order_by(NotificationRecord.created_at.desc())
        .limit(limit)
    ).all()
    live_items = request.app.state.notifications.list_for_user(current_user.id, limit=limit)
    combined: list[NotificationView] = [
        NotificationView(
            notification_id=item.id,
            user_id=item.user_id,
            topic=item.topic,
            template_key=item.template_key,
            resource_id=item.resource_id,
            fixture_id=item.fixture_id,
            competition_id=item.competition_id,
            message=item.message,
            metadata=item.metadata_json,
            created_at=item.created_at,
            read_at=item.read_at,
            is_read=item.read_at is not None,
        )
        for item in db_items
    ]
    combined.extend(
        NotificationView(
            notification_id=item.notification_id,
            user_id=item.user_id,
            topic=item.topic,
            template_key=item.template_key,
            resource_id=item.resource_id,
            fixture_id=item.fixture_id,
            competition_id=item.competition_id,
            message=item.message,
            metadata=item.metadata,
            created_at=item.created_at,
            read_at=None,
            is_read=False,
        )
        for item in live_items
    )
    combined.sort(key=lambda item: item.created_at, reverse=True)
    return combined[:limit]


@notifications_router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
def mark_notification_read(
    notification_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    record = session.get(NotificationRecord, notification_id)
    if record is None or record.user_id != current_user.id:
        return {"status": "ok"}
    if record.read_at is None:
        record.read_at = datetime.utcnow()
        session.commit()
    return {"status": "ok"}


@notifications_router.post("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    session.execute(
        NotificationRecord.__table__.update()
        .where(NotificationRecord.user_id == current_user.id, NotificationRecord.read_at.is_(None))
        .values(read_at=datetime.utcnow())
    )
    session.commit()
    return {"status": "ok"}


router.include_router(notifications_router)
router.include_router(replay_router)
