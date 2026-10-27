from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.match_engine.services import ensure_local_match_execution_runtime
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.notifications.schemas import (
    NotificationEventMatrixItemView,
    NotificationPreferenceUpdate,
    NotificationPreferenceView,
    NotificationSubscriptionCreate,
    NotificationSubscriptionView,
    NotificationTestEventRequest,
    NotificationTestEventView as _SchemaNotificationTestEventView,
    NotificationView as _SchemaNotificationView,
    PlatformAnnouncementCreate,
    PlatformAnnouncementView,
)
from app.notifications.service import (
    NotificationEventMatrixService,
    NotificationServiceError,
    NotificationSettingsService,
)
from app.replay_archive.router import router as replay_router
from app.replay_archive.service import ensure_replay_archive


class NotificationView(_SchemaNotificationView):
    deep_link_route: str | None = None
    target_type: str | None = None
    target_id: str | None = None


class NotificationTestEventView(_SchemaNotificationTestEventView):
    notification: NotificationView


def _first_non_empty_str(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_routing_fields(
    *,
    raw_metadata: dict[str, Any] | None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    fixture_id: str | None = None,
    competition_id: str | None = None,
    topic: str | None = None,
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    meta = dict(raw_metadata or {})
    clean_resource_type = (resource_type or "").strip() or None
    clean_resource_id = (resource_id or "").strip() or None
    clean_fixture_id = (fixture_id or "").strip() or None
    clean_competition_id = (competition_id or "").strip() or None
    clean_topic = (topic or "").strip() or None

    match_ref = clean_fixture_id or _first_non_empty_str(
        meta, "fixture_id", "fixtureId", "match_id", "matchId", "match_key", "matchKey"
    )

    target_type = (
        _first_non_empty_str(meta, "target_type", "targetType", "resource_type", "resourceType") or clean_resource_type
    )
    if not target_type:
        if match_ref:
            target_type = "match"
        elif clean_competition_id or _first_non_empty_str(meta, "competition_id", "competitionId"):
            target_type = "competition"
        elif _first_non_empty_str(meta, "player_id", "playerId"):
            target_type = "player"
        elif _first_non_empty_str(meta, "club_id", "clubId"):
            target_type = "club"
        elif clean_resource_id:
            target_type = clean_topic or "resource"

    target_id = (
        _first_non_empty_str(meta, "target_id", "targetId", "resource_id", "resourceId")
        or clean_resource_id
        or match_ref
        or clean_competition_id
        or _first_non_empty_str(meta, "competition_id", "competitionId", "player_id", "playerId", "club_id", "clubId")
    )

    deep_link_route = _first_non_empty_str(
        meta,
        "deep_link_route",
        "deepLinkRoute",
        "deep_link",
        "deepLink",
        "action_route",
        "actionRoute",
        "route",
    )
    if not deep_link_route:
        if match_ref or (
            target_type
            and target_type.lower() in {"match", "fixture", "competition_match"}
            and (clean_resource_id or target_id)
        ):
            resolved_match_id = clean_resource_id or match_ref or target_id
            deep_link_route = f"/matches/{resolved_match_id}"
        elif clean_competition_id or _first_non_empty_str(meta, "competition_id", "competitionId"):
            resolved_comp_id = clean_competition_id or _first_non_empty_str(meta, "competition_id", "competitionId")
            deep_link_route = f"/competitions/{resolved_comp_id}"
        elif target_type and target_type.lower() == "player" and target_id:
            deep_link_route = f"/players/{target_id}"
        elif target_type and target_type.lower() == "club" and target_id:
            deep_link_route = f"/clubs/{target_id}"

    if deep_link_route is not None and not _first_non_empty_str(meta, "deep_link_route"):
        meta["deep_link_route"] = deep_link_route
    if target_type is not None and not _first_non_empty_str(meta, "target_type"):
        meta["target_type"] = target_type
    if target_id is not None and not _first_non_empty_str(meta, "target_id"):
        meta["target_id"] = target_id
    if clean_resource_type is not None and not _first_non_empty_str(meta, "resource_type"):
        meta["resource_type"] = clean_resource_type

    return deep_link_route, target_type, target_id, meta


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
    combined: list[NotificationView] = [_notification_record_view(item) for item in db_items]
    for item in live_items:
        deep_link_route, target_type, target_id, metadata = _extract_routing_fields(
            raw_metadata=item.metadata,
            resource_type=getattr(item, "resource_type", None),
            resource_id=item.resource_id,
            fixture_id=item.fixture_id,
            competition_id=item.competition_id,
            topic=item.topic,
        )
        combined.append(
            NotificationView(
                notification_id=item.notification_id,
                user_id=item.user_id,
                topic=item.topic,
                template_key=item.template_key,
                resource_id=item.resource_id,
                fixture_id=item.fixture_id,
                competition_id=item.competition_id,
                message=item.message,
                metadata=metadata,
                deep_link_route=deep_link_route,
                target_type=target_type,
                target_id=target_id,
                created_at=item.created_at,
                read_at=None,
                is_read=False,
            )
        )
    combined.sort(key=_notification_created_at_key, reverse=True)
    return combined[:limit]


def _notification_created_at_key(item: NotificationView) -> datetime:
    created_at = item.created_at
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=timezone.utc)
    return created_at.astimezone(timezone.utc)


def _notification_record_view(item: NotificationRecord) -> NotificationView:
    deep_link_route, target_type, target_id, metadata = _extract_routing_fields(
        raw_metadata=item.metadata_json,
        resource_type=item.resource_type,
        resource_id=item.resource_id,
        fixture_id=item.fixture_id,
        competition_id=item.competition_id,
        topic=item.topic,
    )
    return NotificationView(
        notification_id=item.id,
        user_id=item.user_id,
        topic=item.topic,
        template_key=item.template_key,
        resource_id=item.resource_id,
        fixture_id=item.fixture_id,
        competition_id=item.competition_id,
        message=item.message,
        metadata=metadata,
        deep_link_route=deep_link_route,
        target_type=target_type,
        target_id=target_id,
        created_at=item.created_at,
        read_at=item.read_at,
        is_read=item.read_at is not None,
    )


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
def get_preferences(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> NotificationPreferenceView:
    service = NotificationSettingsService(session)
    pref = service.get_or_create_preferences(actor=current_user)
    session.commit()
    session.refresh(pref)
    return NotificationPreferenceView.model_validate(pref)


@notifications_router.put("/preferences", response_model=NotificationPreferenceView)
def update_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationPreferenceView:
    service = NotificationSettingsService(session)
    pref = service.update_preferences(actor=current_user, payload=payload)
    session.commit()
    session.refresh(pref)
    return NotificationPreferenceView.model_validate(pref)


@notifications_router.get("/subscriptions", response_model=list[NotificationSubscriptionView])
def list_subscriptions(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> list[NotificationSubscriptionView]:
    service = NotificationSettingsService(session)
    return [
        NotificationSubscriptionView.model_validate(item) for item in service.list_subscriptions(actor=current_user)
    ]


@notifications_router.post(
    "/subscriptions", response_model=NotificationSubscriptionView, status_code=status.HTTP_201_CREATED
)
def upsert_subscription(
    payload: NotificationSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSubscriptionView:
    service = NotificationSettingsService(session)
    item = service.upsert_subscription(actor=current_user, payload=payload)
    session.commit()
    session.refresh(item)
    return NotificationSubscriptionView.model_validate(item)


@notifications_router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: str, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> None:
    service = NotificationSettingsService(session)
    service.remove_subscription(actor=current_user, subscription_id=subscription_id)
    session.commit()


@notifications_router.get("/announcements", response_model=list[PlatformAnnouncementView])
def list_announcements(session: Session = Depends(get_session)) -> list[PlatformAnnouncementView]:
    service = NotificationSettingsService(session)
    return [PlatformAnnouncementView.model_validate(item) for item in service.list_announcements(active_only=True)]


@admin_router.get("/announcements", response_model=list[PlatformAnnouncementView])
def admin_list_announcements(
    _: User = Depends(get_current_admin), session: Session = Depends(get_session)
) -> list[PlatformAnnouncementView]:
    service = NotificationSettingsService(session)
    return [PlatformAnnouncementView.model_validate(item) for item in service.list_announcements(active_only=False)]


@admin_router.post("/announcements", response_model=PlatformAnnouncementView)
def publish_announcement(
    payload: PlatformAnnouncementCreate,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> PlatformAnnouncementView:
    service = NotificationSettingsService(session)
    item = service.publish_announcement(actor=actor, payload=payload)
    session.commit()
    session.refresh(item)
    return PlatformAnnouncementView.model_validate(item)


@admin_router.get("/event-matrix", response_model=list[NotificationEventMatrixItemView])
def admin_notification_event_matrix(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[NotificationEventMatrixItemView]:
    return NotificationEventMatrixService(session).list_matrix()


@admin_router.post("/test-event", response_model=NotificationTestEventView)
def admin_test_notification_event(
    payload: NotificationTestEventRequest,
    actor: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> NotificationTestEventView:
    service = NotificationEventMatrixService(session)
    try:
        record, matrix_item = service.publish_test_event(actor=actor, payload=payload)
    except NotificationServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    session.commit()
    session.refresh(record)
    return NotificationTestEventView(
        notification=_notification_record_view(record),
        matrix_item=matrix_item,
    )


router.include_router(notifications_router)
router.include_router(admin_router)
router.include_router(replay_router)
