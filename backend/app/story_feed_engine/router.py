from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_admin, get_session
from backend.app.models.user import User
from backend.app.story_feed_engine.schemas import StoryDigestResponse, StoryFeedItemResponse, StoryFeedPublishRequest
from backend.app.story_feed_engine.service import StoryFeedService

router = APIRouter(prefix="/story-feed", tags=["story-feed"])
admin_router = APIRouter(prefix="/admin/story-feed", tags=["story-feed-admin"])


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
        StoryFeedItemResponse.model_validate(item, from_attributes=True)
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
        top_stories=[StoryFeedItemResponse.model_validate(item, from_attributes=True) for item in digest["top_stories"]],
        country_spotlight=[StoryFeedItemResponse.model_validate(item, from_attributes=True) for item in digest["country_spotlight"]],
        feature_stories=[StoryFeedItemResponse.model_validate(item, from_attributes=True) for item in digest["feature_stories"]],
    )


@admin_router.post("", response_model=StoryFeedItemResponse)
def publish_story(payload: StoryFeedPublishRequest, session: Session = Depends(get_session), current_admin: User = Depends(get_current_admin)):
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
    )
    session.commit()
    session.refresh(item)
    return StoryFeedItemResponse.model_validate(item, from_attributes=True)
