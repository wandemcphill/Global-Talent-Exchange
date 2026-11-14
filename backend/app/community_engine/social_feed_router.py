from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_admin,
    get_current_social_user,
    get_optional_current_user,
    get_session,
)
from app.community_engine.schemas import ChatBlockRequest
from app.community_engine.social_feed_service import CommunitySocialError, CommunitySocialService
from app.models.moderation_report import ModerationReport
from app.models.user import User

social_feed_router = APIRouter(tags=["community-social"])


class ChannelCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="general", max_length=48)


class ChannelMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    reply_to_message_id: str | None = None
    linked_entities: dict[str, Any] = Field(default_factory=dict)


class PostCreateRequest(BaseModel):
    post_type: str = Field(default="football_discussion", max_length=48)
    title: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    channel_slug: str | None = Field(default=None, max_length=80)
    club_id: str | None = None
    player_id: str | None = None
    competition_id: str | None = None
    competition_source: str | None = None
    tags: list[str] = Field(default_factory=list)
    poll_options: list[str] = Field(default_factory=list)


class PostUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=4000)


class ReactionToggleRequest(BaseModel):
    reaction_type: str = Field(default="like", min_length=1, max_length=24)


class PollVoteRequest(BaseModel):
    option_id: str = Field(min_length=1, max_length=64)


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_comment_id: str | None = None


class CompetitionApplyRequest(BaseModel):
    club_id: str | None = None
    note: str | None = Field(default=None, max_length=500)
    passcode: str | None = None


class CompetitionReviewRequest(BaseModel):
    decision: str = Field(pattern="^(accept|reject)$")
    review_note: str | None = Field(default=None, max_length=240)


class MuteRequest(BaseModel):
    muted: bool = True
    reason: str | None = Field(default=None, max_length=240)


class CommunityReportRequest(BaseModel):
    target_type: str = Field(min_length=2, max_length=32)
    target_id: str = Field(min_length=1, max_length=64)
    reason_code: str = Field(default="community_guideline", max_length=48)
    description: str = Field(default="", max_length=1000)
    subject_user_id: str | None = None


class ModerationResolveRequest(BaseModel):
    report_id: str | None = None
    target_type: str = Field(min_length=2, max_length=32)
    target_id: str = Field(min_length=1, max_length=64)
    action: str = Field(pattern="^(hide|restore|lock|unlock|dismiss)$")
    note: str | None = Field(default=None, max_length=500)


def _handle(fn, session: Session, **kwargs):
    try:
        result = fn(**kwargs)
        session.commit()
        return result
    except CommunitySocialError as exc:
        session.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@social_feed_router.get("/channels")
def list_channels(session: Session = Depends(get_session)) -> dict[str, Any]:
    service = CommunitySocialService(session)
    channels = service.list_channels()
    session.commit()
    return {"channels": channels}


@social_feed_router.post("/channels", status_code=status.HTTP_201_CREATED)
def create_channel(
    payload: ChannelCreateRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).create_channel,
        session,
        actor=actor,
        name=payload.name,
        description=payload.description,
        category=payload.category,
    )


@social_feed_router.get("/channels/{slug}/messages")
def list_channel_messages(
    slug: str,
    before_seq: int | None = Query(default=None, ge=1),
    after_seq: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    actor: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    service = CommunitySocialService(session)
    try:
        data = service.list_channel_messages(
            slug=slug, actor=actor, before_seq=before_seq, after_seq=after_seq, limit=limit
        )
        session.commit()
        return data
    except CommunitySocialError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@social_feed_router.post("/channels/{slug}/messages", status_code=status.HTTP_201_CREATED)
def post_channel_message(
    slug: str,
    payload: ChannelMessageRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).post_channel_message,
        session,
        slug=slug,
        actor=actor,
        body=payload.body,
        reply_to_message_id=payload.reply_to_message_id,
        linked_entities=payload.linked_entities,
    )


@social_feed_router.post("/channels/messages/{message_id}/pin")
def toggle_channel_pin(
    message_id: str,
    pinned: bool | None = Query(default=None),
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).toggle_channel_pin,
        session,
        message_id=message_id,
        actor=actor,
        pinned=pinned,
    )


@social_feed_router.get("/posts")
def list_posts(
    post_type: str | None = Query(default=None),
    channel_slug: str | None = Query(default=None),
    club_id: str | None = Query(default=None),
    competition_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort: str = Query(default="recent"),
    saved_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    actor: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return CommunitySocialService(session).list_posts(
        actor=actor,
        post_type=post_type,
        channel_slug=channel_slug,
        club_id=club_id,
        competition_id=competition_id,
        search=search,
        sort=sort,
        saved_only=saved_only,
        limit=limit,
        offset=offset,
    )


@social_feed_router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreateRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).create_post,
        session,
        actor=actor,
        post_type=payload.post_type,
        title=payload.title,
        body=payload.body,
        channel_slug=payload.channel_slug,
        club_id=payload.club_id,
        player_id=payload.player_id,
        competition_id=payload.competition_id,
        competition_source=payload.competition_source,
        tags=payload.tags,
        poll_options=payload.poll_options,
    )


@social_feed_router.patch("/posts/{post_id}")
def update_post(
    post_id: str,
    payload: PostUpdateRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).update_or_delete_post,
        session,
        post_id=post_id,
        actor=actor,
        title=payload.title,
        body=payload.body,
        delete=False,
    )


@social_feed_router.delete("/posts/{post_id}")
def delete_post(
    post_id: str,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).update_or_delete_post,
        session,
        post_id=post_id,
        actor=actor,
        delete=True,
    )


@social_feed_router.post("/posts/{post_id}/reactions")
def toggle_post_reaction(
    post_id: str,
    payload: ReactionToggleRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).toggle_post_reaction,
        session,
        post_id=post_id,
        actor=actor,
        reaction_type=payload.reaction_type,
    )


@social_feed_router.post("/posts/{post_id}/bookmark")
def toggle_post_bookmark(
    post_id: str,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).toggle_bookmark,
        session,
        post_id=post_id,
        actor=actor,
    )


@social_feed_router.post("/posts/{post_id}/vote")
def vote_post_poll(
    post_id: str,
    payload: PollVoteRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).vote_poll,
        session,
        post_id=post_id,
        actor=actor,
        option_id=payload.option_id,
    )


@social_feed_router.get("/posts/{post_id}/comments")
def list_post_comments(
    post_id: str,
    actor: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        comments = CommunitySocialService(session).list_post_comments(post_id=post_id, actor=actor)
        return {"comments": comments}
    except CommunitySocialError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@social_feed_router.post("/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED)
def create_post_comment(
    post_id: str,
    payload: CommentCreateRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).add_post_comment,
        session,
        post_id=post_id,
        actor=actor,
        body=payload.body,
        parent_comment_id=payload.parent_comment_id,
    )


@social_feed_router.get("/competitions")
def discover_competitions(
    source: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=100),
    actor: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    items = CommunitySocialService(session).list_discoverable_competitions(
        actor=actor,
        source_filter=source,
        status_filter=status_filter,
        search=search,
        limit=limit,
    )
    return {"competitions": items}


@social_feed_router.post("/competitions/{competition_id}/apply")
def apply_to_competition(
    competition_id: str,
    payload: CompetitionApplyRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).apply_to_hosted_competition,
        session,
        competition_id=competition_id,
        actor=actor,
        club_id=payload.club_id,
        note=payload.note,
        passcode=payload.passcode,
    )


@social_feed_router.get("/competitions/{competition_id}/applications")
def list_competition_applications(
    competition_id: str,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        items = CommunitySocialService(session).list_competition_applications(
            competition_id=competition_id, actor=actor
        )
        return {"applications": items}
    except CommunitySocialError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@social_feed_router.post("/competitions/applications/{application_id}/review")
def review_competition_application(
    application_id: str,
    payload: CompetitionReviewRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).review_competition_application,
        session,
        application_id=application_id,
        actor=actor,
        decision=payload.decision,
        review_note=payload.review_note,
    )


@social_feed_router.get("/discovery/people")
def discover_people(
    q: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=80),
    actor: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"people": CommunitySocialService(session).search_users_directory(actor=actor, query=q, limit=limit)}


@social_feed_router.get("/discovery/clubs")
def discover_clubs(
    q: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=80),
    actor: User | None = Depends(get_optional_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"clubs": CommunitySocialService(session).list_clubs_showcase(actor=actor, query=q, limit=limit)}


@social_feed_router.get("/discovery/players")
def discover_players(
    q: str | None = Query(default=None),
    regens_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=80),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {
        "players": CommunitySocialService(session).search_public_players_and_regens(
            query=q, regens_only=regens_only, limit=limit
        )
    }


@social_feed_router.get("/private-messages/threads/{thread_id}/messages/page")
def list_pm_messages_page(
    thread_id: str,
    before_seq: int | None = Query(default=None, ge=1),
    after_seq: int | None = Query(default=None, ge=0),
    limit: int = Query(default=40, ge=1, le=100),
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return CommunitySocialService(session).list_pm_messages_paginated(
            thread_id=thread_id, actor=actor, before_seq=before_seq, after_seq=after_seq, limit=limit
        )
    except CommunitySocialError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@social_feed_router.post("/private-messages/threads/{thread_id}/leave")
def leave_pm_thread(
    thread_id: str,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).leave_pm_thread,
        session,
        thread_id=thread_id,
        actor=actor,
    )


@social_feed_router.post("/users/{target_user_id}/block", status_code=status.HTTP_201_CREATED)
def block_user(
    target_user_id: str,
    payload: ChatBlockRequest | None = None,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).block_user,
        session,
        actor=actor,
        target_user_id=target_user_id,
        reason=payload.reason if payload is not None else None,
    )


@social_feed_router.delete("/users/{target_user_id}/block")
def unblock_user(
    target_user_id: str,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).unblock_user,
        session,
        actor=actor,
        target_user_id=target_user_id,
    )


@social_feed_router.post("/users/{target_user_id}/mute")
def mute_user(
    target_user_id: str,
    payload: MuteRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).toggle_mute_user,
        session,
        actor=actor,
        target_user_id=target_user_id,
        muted=payload.muted,
        reason=payload.reason,
    )


@social_feed_router.post("/reports", status_code=status.HTTP_201_CREATED)
def submit_community_report(
    payload: CommunityReportRequest,
    actor: User = Depends(get_current_social_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).create_moderation_report,
        session,
        actor=actor,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason_code=payload.reason_code,
        description=payload.description,
        subject_user_id=payload.subject_user_id,
    )


@social_feed_router.get("/admin/moderation/reports")
def list_community_moderation_reports(
    admin_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    _ = admin_user
    reports = list(
        session.scalars(select(ModerationReport).order_by(ModerationReport.created_at.desc()).limit(100)).all()
    )
    return {
        "reports": [
            {
                "id": r.id,
                "reporter_user_id": r.reporter_user_id,
                "subject_user_id": r.subject_user_id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason_code": r.reason_code,
                "description": r.description,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "priority": r.priority.value if hasattr(r.priority, "value") else str(r.priority),
                "report_count_for_target": r.report_count_for_target,
                "resolution_note": r.resolution_note,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    }


@social_feed_router.post("/admin/moderation/resolve")
def resolve_community_moderation(
    payload: ModerationResolveRequest,
    admin_user: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return _handle(
        CommunitySocialService(session).resolve_community_moderation,
        session,
        admin_user=admin_user,
        report_id=payload.report_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        action=payload.action,
        note=payload.note,
    )


__all__ = ["social_feed_router"]
