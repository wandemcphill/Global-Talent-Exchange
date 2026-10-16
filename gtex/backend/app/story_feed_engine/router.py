from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.story_feed_engine.schemas import (
    StoryDigestResponse,
    StoryFeedItemResponse,
    StoryFeedPublishRequest,
    StoryFeedRejectRequest,
    StoryFeedScheduleRequest,
)
from app.story_feed_engine.service import (
    StoryFeedModerationError,
    StoryFeedNotFoundError,
    StoryFeedService,
)

router = APIRouter(prefix="/story-feed", tags=["story-feed"])
admin_router = APIRouter(prefix="/admin/story-feed", tags=["story-feed-admin"])


def _to_response(item) -> StoryFeedItemResponse:
    return StoryFeedItemResponse.model_validate(item, from_attributes=True)


@router.get("", response_model=list[StoryFeedItemResponse])
def list_story_feed(
    limit: int = 50,
    story_type: str | None = None,
    country_code: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    featured_only: bool = False,
    session: Session = Depends(get_session),
):
    service = StoryFeedService(session)
    return [
        _to_response(item)
        for item in service.list_feed(
            limit=limit,
            story_type=story_type,
            country_code=country_code,
            subject_type=subject_type,
            subject_id=subject_id,
            featured_only=featured_only,
        )
    ]


@router.get("/digest", response_model=StoryDigestResponse)
def get_story_digest(country_code: str | None = None, session: Session = Depends(get_session)):
    digest = StoryFeedService(session).digest(country_code=country_code)
    return StoryDigestResponse(
        top_stories=[_to_response(item) for item in digest["top_stories"]],
        country_spotlight=[_to_response(item) for item in digest["country_spotlight"]],
        feature_stories=[_to_response(item) for item in digest["feature_stories"]],
    )


@admin_router.get("", response_model=list[StoryFeedItemResponse])
def admin_list_story_feed(
    limit: int = 100,
    story_type: str | None = None,
    country_code: str | None = None,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    _ = current_admin
    service = StoryFeedService(session)
    return [
        _to_response(item)
        for item in service.list_feed(
            limit=limit,
            story_type=story_type,
            country_code=country_code,
            include_moderated=True,
        )
    ]


@admin_router.post("", response_model=StoryFeedItemResponse)
def publish_story(
    payload: StoryFeedPublishRequest,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    try:
        item = StoryFeedService(session).publish(
            story_type=payload.story_type,
            title=payload.title,
            body=payload.body,
            audience=payload.audience,
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            country_code=payload.country_code,
            metadata_json=payload.metadata_json,
            featured=payload.featured,
            published_by_user_id=current_admin.id,
            scheduled_for=payload.scheduled_for,
        )
    except StoryFeedModerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return _to_response(item)


@admin_router.post("/{story_id}/schedule", response_model=StoryFeedItemResponse)
def schedule_story(
    story_id: str,
    payload: StoryFeedScheduleRequest,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    try:
        item = StoryFeedService(session).schedule(
            story_id=story_id,
            scheduled_for=payload.scheduled_for,
            moderated_by_user_id=current_admin.id,
        )
    except StoryFeedNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StoryFeedModerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return _to_response(item)


@admin_router.post("/{story_id}/reject", response_model=StoryFeedItemResponse)
def reject_story(
    story_id: str,
    payload: StoryFeedRejectRequest | None = None,
    session: Session = Depends(get_session),
    current_admin: User = Depends(get_current_admin),
):
    body = payload or StoryFeedRejectRequest()
    try:
        item = StoryFeedService(session).reject(
            story_id=story_id,
            reason=body.reason,
            moderated_by_user_id=current_admin.id,
        )
    except StoryFeedNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    session.refresh(item)
    return _to_response(item)
