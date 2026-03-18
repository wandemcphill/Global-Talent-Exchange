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
from backend.app.schemas.creator_fan_engagement import (
    CreatorClubFollowCreateRequest,
    CreatorClubFollowView,
    CreatorFanCompetitionCreateRequest,
    CreatorFanCompetitionEntryView,
    CreatorFanCompetitionJoinRequest,
    CreatorFanCompetitionView,
    CreatorFanGroupCreateRequest,
    CreatorFanGroupJoinRequest,
    CreatorFanGroupMembershipView,
    CreatorFanGroupView,
    CreatorFanStateView,
    CreatorFanWallView,
    CreatorMatchChatMessageCreateRequest,
    CreatorMatchChatMessageView,
    CreatorMatchChatRoomView,
    CreatorRivalrySignalView,
    CreatorTacticalAdviceCreateRequest,
    CreatorTacticalAdviceView,
)
from backend.app.models.user import User
from backend.app.services.creator_fan_engagement_service import (
    CreatorFanEngagementError,
    CreatorFanEngagementService,
)

router = APIRouter(prefix='/community', tags=['community'])


def get_service(session: Session = Depends(get_session)) -> CommunityEngineService:
    return CommunityEngineService(session)


def get_creator_fan_service(session: Session = Depends(get_session)) -> CreatorFanEngagementService:
    return CreatorFanEngagementService(session)


def _raise(exc: CommunityEngineError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _raise_fan(exc: CreatorFanEngagementError) -> None:
    reason = exc.reason or str(exc)
    if reason.endswith("_not_found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=reason) from exc
    if reason in {"fan_chat_rate_limited", "tactical_advice_rate_limited"}:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=reason) from exc
    if reason in {"chat_room_closed", "fan_chat_access_denied"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason) from exc


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


@router.get('/creator-matches/{match_id}/chat-room', response_model=CreatorMatchChatRoomView)
def get_creator_match_chat_room(
    match_id: str,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorMatchChatRoomView:
    try:
        payload = service.get_chat_room(actor=current_user, match_id=match_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return CreatorMatchChatRoomView.model_validate(payload)


@router.get('/creator-matches/{match_id}/chat-room/messages', response_model=list[CreatorMatchChatMessageView])
def list_creator_match_chat_messages(
    match_id: str,
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> list[CreatorMatchChatMessageView]:
    try:
        items = service.list_chat_messages(match_id=match_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return [CreatorMatchChatMessageView.model_validate(item) for item in items]


@router.post('/creator-matches/{match_id}/chat-room/messages', response_model=CreatorMatchChatMessageView, status_code=status.HTTP_201_CREATED)
def post_creator_match_chat_message(
    match_id: str,
    payload: CreatorMatchChatMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorMatchChatMessageView:
    try:
        item = service.post_chat_message(actor=current_user, match_id=match_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorMatchChatMessageView.model_validate(item)


@router.get('/creator-matches/{match_id}/tactical-advice', response_model=list[CreatorTacticalAdviceView])
def list_creator_match_tactical_advice(
    match_id: str,
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> list[CreatorTacticalAdviceView]:
    try:
        items = service.list_tactical_advice(match_id=match_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return [
        CreatorTacticalAdviceView.model_validate(
            {
                **item.__dict__,
                'authority': 'advisory_only',
            }
        )
        for item in items
    ]


@router.post('/creator-matches/{match_id}/tactical-advice', response_model=CreatorTacticalAdviceView, status_code=status.HTTP_201_CREATED)
def create_creator_match_tactical_advice(
    match_id: str,
    payload: CreatorTacticalAdviceCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorTacticalAdviceView:
    try:
        item = service.create_tactical_advice(actor=current_user, match_id=match_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorTacticalAdviceView.model_validate({**item.__dict__, 'authority': 'advisory_only'})


@router.get('/creator-matches/{match_id}/fan-wall', response_model=CreatorFanWallView)
def get_creator_match_fan_wall(
    match_id: str,
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorFanWallView:
    try:
        payload = service.get_fan_wall(match_id=match_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return CreatorFanWallView.model_validate(payload)


@router.get('/creator-matches/{match_id}/rivalry-signals', response_model=list[CreatorRivalrySignalView])
def list_creator_match_rivalry_signals(
    match_id: str,
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> list[CreatorRivalrySignalView]:
    try:
        items = service.list_rivalry_signals(match_id=match_id)
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return [CreatorRivalrySignalView.model_validate(item) for item in items]


@router.get('/creator-clubs/{club_id}/fan-state', response_model=CreatorFanStateView)
def get_creator_fan_state(
    club_id: str,
    match_id: str | None = None,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorFanStateView:
    try:
        payload = service.get_fan_state(actor=current_user, club_id=club_id, match_id=match_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return CreatorFanStateView.model_validate(payload)


@router.post('/creator-clubs/{club_id}/follow', response_model=CreatorClubFollowView, status_code=status.HTTP_201_CREATED)
def follow_creator_club(
    club_id: str,
    payload: CreatorClubFollowCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorClubFollowView:
    try:
        follow = service.follow_creator_club(actor=current_user, club_id=club_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorClubFollowView.model_validate(follow)


@router.delete('/creator-clubs/{club_id}/follow', status_code=status.HTTP_204_NO_CONTENT)
def unfollow_creator_club(
    club_id: str,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> None:
    try:
        service.unfollow_creator_club(actor=current_user, club_id=club_id)
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)


@router.get('/creator-clubs/{club_id}/fan-groups', response_model=list[CreatorFanGroupView])
def list_creator_fan_groups(
    club_id: str,
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> list[CreatorFanGroupView]:
    try:
        items = service.list_fan_groups(club_id=club_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return [CreatorFanGroupView.model_validate(item) for item in items]


@router.post('/creator-clubs/{club_id}/fan-groups', response_model=CreatorFanGroupView, status_code=status.HTTP_201_CREATED)
def create_creator_fan_group(
    club_id: str,
    payload: CreatorFanGroupCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorFanGroupView:
    try:
        item = service.create_fan_group(actor=current_user, club_id=club_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorFanGroupView.model_validate(item)


@router.post('/fan-groups/{group_id}/join', response_model=CreatorFanGroupMembershipView, status_code=status.HTTP_201_CREATED)
def join_creator_fan_group(
    group_id: str,
    payload: CreatorFanGroupJoinRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorFanGroupMembershipView:
    try:
        membership = service.join_fan_group(actor=current_user, group_id=group_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorFanGroupMembershipView.model_validate(membership)


@router.get('/creator-clubs/{club_id}/fan-competitions', response_model=list[CreatorFanCompetitionView])
def list_creator_fan_competitions(
    club_id: str,
    match_id: str | None = None,
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> list[CreatorFanCompetitionView]:
    try:
        items = service.list_fan_competitions(club_id=club_id, match_id=match_id)
    except CreatorFanEngagementError as exc:
        _raise_fan(exc)
    return [CreatorFanCompetitionView.model_validate(item) for item in items]


@router.post('/creator-clubs/{club_id}/fan-competitions', response_model=CreatorFanCompetitionView, status_code=status.HTTP_201_CREATED)
def create_creator_fan_competition(
    club_id: str,
    payload: CreatorFanCompetitionCreateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorFanCompetitionView:
    try:
        item = service.create_fan_competition(actor=current_user, club_id=club_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorFanCompetitionView.model_validate(item)


@router.post('/fan-competitions/{fan_competition_id}/join', response_model=CreatorFanCompetitionEntryView, status_code=status.HTTP_201_CREATED)
def join_creator_fan_competition(
    fan_competition_id: str,
    payload: CreatorFanCompetitionJoinRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorFanEngagementService = Depends(get_creator_fan_service),
) -> CreatorFanCompetitionEntryView:
    try:
        entry = service.join_fan_competition(actor=current_user, fan_competition_id=fan_competition_id, **payload.model_dump())
        service.session.commit()
    except CreatorFanEngagementError as exc:
        service.session.rollback()
        _raise_fan(exc)
    return CreatorFanCompetitionEntryView.model_validate(entry)
