from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_current_social_user, get_session
from app.community_engine.schemas import (
    ChatBlockRequest,
    ChatMuteRequest,
    DiscussionCategoryView,
    DiscussionReactionCreate,
    DiscussionReactionView,
    DiscussionReplyCreate,
    DiscussionThreadCreate,
    LiveThreadMessageView,
    LiveThreadView,
    ModerationReportCreate,
    ModerationReportView,
    PrivateMessageCreate,
    PrivateMessageParticipantView,
    PrivateMessageThreadCreate,
    PrivateMessageThreadView,
    PrivateMessageView,
)
from app.community_engine.service import CommunityEngineError, CommunityEngineService
from app.models.user import User

router = APIRouter(tags=["social-integrity"])
chat_router = APIRouter(prefix="/chats", tags=["chats"])
discussion_router = APIRouter(prefix="/discussions", tags=["discussions"])
admin_chat_router = APIRouter(prefix="/admin/chat", tags=["admin-chat"])
admin_discussion_router = APIRouter(prefix="/admin/discussions", tags=["admin-discussions"])


def get_service(session: Session = Depends(get_session)) -> CommunityEngineService:
    return CommunityEngineService(session)


def _raise(exc: CommunityEngineError) -> None:
    message = str(exc)
    if "not found" in message.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    if "not a participant" in message.lower() or "blocked" in message.lower() or "locked" in message.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


def _private_thread_view(service: CommunityEngineService, thread) -> PrivateMessageThreadView:
    participants = service.list_private_thread_participants(thread_id=thread.id)
    return PrivateMessageThreadView.model_validate(thread).model_copy(update={"participants": participants})


@chat_router.get("/threads", response_model=list[PrivateMessageThreadView])
def list_chat_threads(
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> list[PrivateMessageThreadView]:
    return [_private_thread_view(service, thread) for thread in service.list_private_threads(actor=current_user)]


@chat_router.post("/threads", response_model=PrivateMessageThreadView, status_code=status.HTTP_201_CREATED)
def create_chat_thread(
    payload: PrivateMessageThreadCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> PrivateMessageThreadView:
    try:
        thread = service.create_private_thread(actor=current_user, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return _private_thread_view(service, thread)


@chat_router.get("/threads/{thread_id}", response_model=PrivateMessageThreadView)
def get_chat_thread(
    thread_id: str,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> PrivateMessageThreadView:
    try:
        thread = service.get_private_thread(actor=current_user, thread_id=thread_id)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return _private_thread_view(service, thread)


@chat_router.get("/threads/{thread_id}/messages", response_model=list[PrivateMessageView])
def list_chat_messages(
    thread_id: str,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> list[PrivateMessageView]:
    try:
        messages = service.list_private_messages(actor=current_user, thread_id=thread_id)
    except CommunityEngineError as exc:
        _raise(exc)
    return [PrivateMessageView.model_validate(item) for item in messages]


@chat_router.post(
    "/threads/{thread_id}/messages", response_model=PrivateMessageView, status_code=status.HTTP_201_CREATED
)
def post_chat_message(
    thread_id: str,
    payload: PrivateMessageCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> PrivateMessageView:
    try:
        message = service.post_private_message(actor=current_user, thread_id=thread_id, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return PrivateMessageView.model_validate(message)


@chat_router.post("/threads/{thread_id}/read", response_model=PrivateMessageThreadView)
def mark_chat_thread_read(
    thread_id: str,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> PrivateMessageThreadView:
    try:
        thread = service.mark_private_thread_read(actor=current_user, thread_id=thread_id)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return _private_thread_view(service, thread)


@chat_router.post("/threads/{thread_id}/mute", response_model=PrivateMessageParticipantView)
def mute_chat_thread(
    thread_id: str,
    payload: ChatMuteRequest,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> PrivateMessageParticipantView:
    try:
        participant = service.mute_private_thread(actor=current_user, thread_id=thread_id, muted=payload.muted)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return PrivateMessageParticipantView.model_validate(participant)


@chat_router.post(
    "/messages/{message_id}/report", response_model=ModerationReportView, status_code=status.HTTP_201_CREATED
)
def report_chat_message(
    message_id: str,
    payload: ModerationReportCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> ModerationReportView:
    try:
        report = service.report_private_message(actor=current_user, message_id=message_id, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return ModerationReportView.model_validate(report)


@chat_router.post("/users/{user_id}/block", response_model=dict[str, str], status_code=status.HTTP_201_CREATED)
def block_chat_user(
    user_id: str,
    payload: ChatBlockRequest,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> dict[str, str]:
    try:
        block = service.block_user(actor=current_user, target_user_id=user_id, reason=payload.reason)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return {"id": block.id, "blocked_user_id": block.blocked_user_id, "status": "blocked"}


@discussion_router.get("/categories", response_model=list[DiscussionCategoryView])
def list_discussion_categories(service: CommunityEngineService = Depends(get_service)) -> list[DiscussionCategoryView]:
    return [DiscussionCategoryView.model_validate(item) for item in service.discussion_categories()]


@discussion_router.get("/threads", response_model=list[LiveThreadView])
def list_discussion_threads(
    category: str | None = None,
    service: CommunityEngineService = Depends(get_service),
) -> list[LiveThreadView]:
    try:
        threads = service.list_discussion_threads(category=category)
    except CommunityEngineError as exc:
        _raise(exc)
    return [LiveThreadView.model_validate(item) for item in threads]


@discussion_router.post("/threads", response_model=LiveThreadView, status_code=status.HTTP_201_CREATED)
def create_discussion_thread(
    payload: DiscussionThreadCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> LiveThreadView:
    try:
        thread = service.create_discussion_thread(actor=current_user, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return LiveThreadView.model_validate(thread)


@discussion_router.get("/threads/{thread_id}", response_model=LiveThreadView)
def get_discussion_thread(
    thread_id: str,
    service: CommunityEngineService = Depends(get_service),
) -> LiveThreadView:
    try:
        thread = service.get_discussion_thread(thread_id=thread_id)
    except CommunityEngineError as exc:
        _raise(exc)
    return LiveThreadView.model_validate(thread)


@discussion_router.get("/threads/{thread_id}/replies", response_model=list[LiveThreadMessageView])
def list_discussion_replies(
    thread_id: str,
    service: CommunityEngineService = Depends(get_service),
) -> list[LiveThreadMessageView]:
    try:
        replies = service.list_discussion_replies(thread_id=thread_id)
    except CommunityEngineError as exc:
        _raise(exc)
    return [LiveThreadMessageView.model_validate(item) for item in replies]


@discussion_router.post(
    "/threads/{thread_id}/replies", response_model=LiveThreadMessageView, status_code=status.HTTP_201_CREATED
)
def post_discussion_reply(
    thread_id: str,
    payload: DiscussionReplyCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> LiveThreadMessageView:
    try:
        reply = service.post_discussion_reply(actor=current_user, thread_id=thread_id, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return LiveThreadMessageView.model_validate(reply)


@discussion_router.post(
    "/replies/{reply_id}/react", response_model=DiscussionReactionView, status_code=status.HTTP_201_CREATED
)
def react_discussion_reply(
    reply_id: str,
    payload: DiscussionReactionCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> DiscussionReactionView:
    try:
        reaction = service.react_to_discussion_entity(
            actor=current_user,
            entity_type="reply",
            entity_id=reply_id,
            reaction_type=payload.reaction_type,
        )
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return DiscussionReactionView.model_validate(reaction)


@discussion_router.post(
    "/threads/{thread_id}/react", response_model=DiscussionReactionView, status_code=status.HTTP_201_CREATED
)
def react_discussion_thread(
    thread_id: str,
    payload: DiscussionReactionCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> DiscussionReactionView:
    try:
        reaction = service.react_to_discussion_entity(
            actor=current_user,
            entity_type="thread",
            entity_id=thread_id,
            reaction_type=payload.reaction_type,
        )
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return DiscussionReactionView.model_validate(reaction)


@discussion_router.post(
    "/threads/{thread_id}/report", response_model=ModerationReportView, status_code=status.HTTP_201_CREATED
)
def report_discussion_thread(
    thread_id: str,
    payload: ModerationReportCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> ModerationReportView:
    try:
        report = service.report_discussion_thread(actor=current_user, thread_id=thread_id, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return ModerationReportView.model_validate(report)


@discussion_router.post(
    "/replies/{reply_id}/report", response_model=ModerationReportView, status_code=status.HTTP_201_CREATED
)
def report_discussion_reply(
    reply_id: str,
    payload: ModerationReportCreate,
    current_user: User = Depends(get_current_social_user),
    service: CommunityEngineService = Depends(get_service),
) -> ModerationReportView:
    try:
        report = service.report_discussion_reply(actor=current_user, reply_id=reply_id, **payload.model_dump())
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return ModerationReportView.model_validate(report)


@admin_chat_router.get("/reports", response_model=list[ModerationReportView])
def list_chat_reports(
    _: User = Depends(get_current_admin),
    service: CommunityEngineService = Depends(get_service),
) -> list[ModerationReportView]:
    reports = service.list_reports(target_types={"chat_message"})
    return [ModerationReportView.model_validate(item) for item in reports]


@admin_chat_router.post("/messages/{message_id}/hide", response_model=PrivateMessageView)
def admin_hide_chat_message(
    message_id: str,
    _: User = Depends(get_current_admin),
    service: CommunityEngineService = Depends(get_service),
) -> PrivateMessageView:
    try:
        message = service.hide_private_message(message_id=message_id)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return PrivateMessageView.model_validate(message)


@admin_discussion_router.get("/reports", response_model=list[ModerationReportView])
def list_discussion_reports(
    _: User = Depends(get_current_admin),
    service: CommunityEngineService = Depends(get_service),
) -> list[ModerationReportView]:
    reports = service.list_reports(target_types={"discussion_thread", "discussion_reply"})
    return [ModerationReportView.model_validate(item) for item in reports]


@admin_discussion_router.post("/threads/{thread_id}/lock", response_model=LiveThreadView)
def admin_lock_discussion_thread(
    thread_id: str,
    admin: User = Depends(get_current_admin),
    service: CommunityEngineService = Depends(get_service),
) -> LiveThreadView:
    try:
        thread = service.lock_discussion_thread(actor=admin, thread_id=thread_id)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return LiveThreadView.model_validate(thread)


@admin_discussion_router.post("/replies/{reply_id}/hide", response_model=LiveThreadMessageView)
def admin_hide_discussion_reply(
    reply_id: str,
    _: User = Depends(get_current_admin),
    service: CommunityEngineService = Depends(get_service),
) -> LiveThreadMessageView:
    try:
        reply = service.hide_discussion_reply(reply_id=reply_id)
        service.session.commit()
    except CommunityEngineError as exc:
        service.session.rollback()
        _raise(exc)
    return LiveThreadMessageView.model_validate(reply)


router.include_router(chat_router)
router.include_router(discussion_router)
router.include_router(admin_chat_router)
router.include_router(admin_discussion_router)
