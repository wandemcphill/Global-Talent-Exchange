from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.community_engine.schemas import (
    CommunityDigestView,
    CompetitionWatchlistCreate,
    CompetitionWatchlistView,
    LiveThreadCreate,
    LiveThreadMessageCreate,
    LiveThreadMessageView,
    LiveThreadView,
    PrivateMessageCreate,
    PrivateMessageThreadCreate,
    PrivateMessageThreadView,
    PrivateMessageView,
)
from backend.app.community_engine.service import CommunityEngineError, CommunityEngineService
from backend.app.models.user import User

router = APIRouter(prefix='/community', tags=['community'])


def get_service(session: Session = Depends(get_session)) -> CommunityEngineService:
    return CommunityEngineService(session)


def _raise(exc: CommunityEngineError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get('/digest', response_model=CommunityDigestView)
def get_digest(current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> CommunityDigestView:
    return CommunityDigestView.model_validate(service.digest(actor=current_user))


@router.get('/watchlist', response_model=list[CompetitionWatchlistView])
def list_watchlist(current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> list[CompetitionWatchlistView]:
    return [CompetitionWatchlistView.model_validate(item) for item in service.list_watchlist(actor=current_user)]


@router.post('/watchlist', response_model=CompetitionWatchlistView, status_code=status.HTTP_201_CREATED)
def add_watchlist(payload: CompetitionWatchlistCreate, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> CompetitionWatchlistView:
    try:
        item = service.add_watchlist(actor=current_user, **payload.model_dump())
    except CommunityEngineError as exc:
        _raise(exc)
    return CompetitionWatchlistView.model_validate(item)


@router.delete('/watchlist/{competition_key}', status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist(competition_key: str, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> None:
    try:
        service.remove_watchlist(actor=current_user, competition_key=competition_key)
    except CommunityEngineError as exc:
        _raise(exc)


@router.get('/live-threads', response_model=list[LiveThreadView])
def list_live_threads(competition_key: str | None = None, service: CommunityEngineService = Depends(get_service)) -> list[LiveThreadView]:
    return [LiveThreadView.model_validate(item) for item in service.list_live_threads(competition_key=competition_key)]


@router.post('/live-threads', response_model=LiveThreadView, status_code=status.HTTP_201_CREATED)
def create_live_thread(payload: LiveThreadCreate, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> LiveThreadView:
    try:
        thread = service.create_live_thread(actor=current_user, **payload.model_dump())
    except CommunityEngineError as exc:
        _raise(exc)
    return LiveThreadView.model_validate(thread)


@router.get('/live-threads/{thread_id}', response_model=LiveThreadView)
def get_live_thread(thread_id: str, service: CommunityEngineService = Depends(get_service)) -> LiveThreadView:
    try:
        thread = service.get_live_thread(thread_id=thread_id)
    except CommunityEngineError as exc:
        _raise(exc)
    return LiveThreadView.model_validate(thread)


@router.get('/live-threads/{thread_id}/messages', response_model=list[LiveThreadMessageView])
def list_live_thread_messages(thread_id: str, service: CommunityEngineService = Depends(get_service)) -> list[LiveThreadMessageView]:
    try:
        items = service.list_live_thread_messages(thread_id=thread_id)
    except CommunityEngineError as exc:
        _raise(exc)
    return [LiveThreadMessageView.model_validate(item) for item in items]


@router.post('/live-threads/{thread_id}/messages', response_model=LiveThreadMessageView, status_code=status.HTTP_201_CREATED)
def post_live_thread_message(thread_id: str, payload: LiveThreadMessageCreate, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> LiveThreadMessageView:
    try:
        item = service.post_live_thread_message(actor=current_user, thread_id=thread_id, **payload.model_dump())
    except CommunityEngineError as exc:
        _raise(exc)
    return LiveThreadMessageView.model_validate(item)


@router.get('/private-messages/threads', response_model=list[PrivateMessageThreadView])
def list_private_threads(current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> list[PrivateMessageThreadView]:
    threads = service.list_private_threads(actor=current_user)
    output: list[PrivateMessageThreadView] = []
    for thread in threads:
        participants = service.list_private_thread_participants(thread_id=thread.id)
        payload = PrivateMessageThreadView.model_validate(thread).model_copy(update={'participants': participants})
        output.append(payload)
    return output


@router.post('/private-messages/threads', response_model=PrivateMessageThreadView, status_code=status.HTTP_201_CREATED)
def create_private_thread(payload: PrivateMessageThreadCreate, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> PrivateMessageThreadView:
    try:
        thread = service.create_private_thread(actor=current_user, **payload.model_dump())
        participants = service.list_private_thread_participants(thread_id=thread.id)
    except CommunityEngineError as exc:
        _raise(exc)
    return PrivateMessageThreadView.model_validate(thread).model_copy(update={'participants': participants})


@router.get('/private-messages/threads/{thread_id}', response_model=PrivateMessageThreadView)
def get_private_thread(thread_id: str, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> PrivateMessageThreadView:
    try:
        thread = service.get_private_thread(actor=current_user, thread_id=thread_id)
        participants = service.list_private_thread_participants(thread_id=thread.id)
    except CommunityEngineError as exc:
        _raise(exc)
    return PrivateMessageThreadView.model_validate(thread).model_copy(update={'participants': participants})


@router.get('/private-messages/threads/{thread_id}/messages', response_model=list[PrivateMessageView])
def list_private_messages(thread_id: str, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> list[PrivateMessageView]:
    try:
        messages = service.list_private_messages(actor=current_user, thread_id=thread_id)
    except CommunityEngineError as exc:
        _raise(exc)
    return [PrivateMessageView.model_validate(item) for item in messages]


@router.post('/private-messages/threads/{thread_id}/messages', response_model=PrivateMessageView, status_code=status.HTTP_201_CREATED)
def post_private_message(thread_id: str, payload: PrivateMessageCreate, current_user: User = Depends(get_current_user), service: CommunityEngineService = Depends(get_service)) -> PrivateMessageView:
    try:
        message = service.post_private_message(actor=current_user, thread_id=thread_id, **payload.model_dump())
    except CommunityEngineError as exc:
        _raise(exc)
    return PrivateMessageView.model_validate(message)
