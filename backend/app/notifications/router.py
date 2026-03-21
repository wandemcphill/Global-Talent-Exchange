from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.match_engine.services import ensure_local_match_execution_runtime
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.notifications.schemas import (
    NotificationPreferenceUpdate,
    NotificationPreferenceView,
    NotificationSubscriptionCreate,
    NotificationSubscriptionView,
    NotificationView,
    PlatformAnnouncementCreate,
    PlatformAnnouncementView,
)
from app.notifications.service import NotificationSettingsService
from app.replay_archive.router import router as replay_router
from app.replay_archive.service import ensure_replay_archive


@asynccontextmanager
async def _support_router_lifespan(app: FastAPI):
    ensure_replay_archive(app)
    ensure_local_match_execution_runtime(app)
    yield


router = APIRouter(lifespan=_support_router_lifespan)
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
admin_router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


def _map_records(request: Request, current_user: User, session: Session, limit: int) -> list[NotificationView]:
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


@notifications_router.get("/me", response_model=list[NotificationView])
def list_notifications(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[NotificationView]:
    return _map_records(request, current_user, session, limit)


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


@notifications_router.get("/preferences", response_model=NotificationPreferenceView)
def get_preferences(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> NotificationPreferenceView:
    service = NotificationSettingsService(session)
    pref = service.get_or_create_preferences(actor=current_user)
    session.commit()
    session.refresh(pref)
    return NotificationPreferenceView.model_validate(pref)


@notifications_router.put("/preferences", response_model=NotificationPreferenceView)
def update_preferences(payload: NotificationPreferenceUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> NotificationPreferenceView:
    service = NotificationSettingsService(session)
    pref = service.update_preferences(actor=current_user, payload=payload)
    session.commit()
    session.refresh(pref)
    return NotificationPreferenceView.model_validate(pref)


@notifications_router.get("/subscriptions", response_model=list[NotificationSubscriptionView])
def list_subscriptions(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[NotificationSubscriptionView]:
    service = NotificationSettingsService(session)
    return [NotificationSubscriptionView.model_validate(item) for item in service.list_subscriptions(actor=current_user)]


@notifications_router.post("/subscriptions", response_model=NotificationSubscriptionView, status_code=status.HTTP_201_CREATED)
def upsert_subscription(payload: NotificationSubscriptionCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> NotificationSubscriptionView:
    service = NotificationSettingsService(session)
    item = service.upsert_subscription(actor=current_user, payload=payload)
    session.commit()
    session.refresh(item)
    return NotificationSubscriptionView.model_validate(item)


@notifications_router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: str, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> None:
    service = NotificationSettingsService(session)
    service.remove_subscription(actor=current_user, subscription_id=subscription_id)
    session.commit()


@notifications_router.get("/announcements", response_model=list[PlatformAnnouncementView])
def list_announcements(session: Session = Depends(get_session)) -> list[PlatformAnnouncementView]:
    service = NotificationSettingsService(session)
    return [PlatformAnnouncementView.model_validate(item) for item in service.list_announcements(active_only=True)]


@admin_router.get("/announcements", response_model=list[PlatformAnnouncementView])
def admin_list_announcements(_: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> list[PlatformAnnouncementView]:
    service = NotificationSettingsService(session)
    return [PlatformAnnouncementView.model_validate(item) for item in service.list_announcements(active_only=False)]


@admin_router.post("/announcements", response_model=PlatformAnnouncementView)
def publish_announcement(payload: PlatformAnnouncementCreate, actor: User = Depends(get_current_admin), session: Session = Depends(get_session)) -> PlatformAnnouncementView:
    service = NotificationSettingsService(session)
    item = service.publish_announcement(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return PlatformAnnouncementView.model_validate(item)


router.include_router(notifications_router)
router.include_router(admin_router)
router.include_router(replay_router)
