from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.club_social.schemas import (
    ChallengeAcceptRequest,
    ChallengeCreateRequest,
    ChallengeLinkCreateRequest,
    ChallengeLinkView,
    ChallengePageView,
    ChallengeShareEventRequest,
    ChallengeShareEventView,
    ClubChallengesView,
    ClubIdentityMetricsView,
    ClubRivalriesView,
    MatchChatFeedView,
    MatchChatMessageCreateRequest,
    MatchLiveReactionCreateRequest,
    MatchLiveReactionFeedView,
    MatchReactionFeedView,
    MatchShareEventRequest,
    MatchShareLinkCreateRequest,
    MatchShareLinkView,
    MatchSharePageView,
    RivalryDetailView,
    RivalryMatchRecordRequest,
    SocialFollowRequest,
    SocialFollowingView,
    SocialFollowView,
)
from app.club_social.service import ClubSocialError, ClubSocialService
from app.db import get_session
from app.models.user import User

router = APIRouter(tags=["club_social"])


def get_service(session: Session = Depends(get_session)) -> ClubSocialService:
    return ClubSocialService(session)


def _raise(exc: ClubSocialError) -> None:
    detail = str(exc)
    if detail.endswith("_not_found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    if detail.endswith("_required"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail) from exc
    if detail in {"challenge_already_accepted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


@router.post("/api/clubs/{club_id}/challenges", response_model=ChallengePageView, status_code=status.HTTP_201_CREATED)
def create_challenge(
    club_id: str,
    payload: ChallengeCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> ChallengePageView:
    try:
        challenge = service.create_challenge(actor=current_user, club_id=club_id, **payload.model_dump())
        body = service.challenge_page(challenge_id=challenge.id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengePageView.model_validate(body)


@router.get("/api/clubs/{club_id}/challenges", response_model=ClubChallengesView)
def list_club_challenges(
    club_id: str,
    direction: str = Query(default="all"),
    status_filter: str | None = Query(default=None, alias="status"),
    service: ClubSocialService = Depends(get_service),
) -> ClubChallengesView:
    try:
        challenges = service.list_club_challenges(club_id=club_id, direction=direction, status=status_filter)
    except ClubSocialError as exc:
        _raise(exc)
    return ClubChallengesView(club_id=club_id, challenges=challenges)


@router.post("/api/challenges/{challenge_id}/publish", response_model=ChallengePageView)
def publish_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> ChallengePageView:
    try:
        body = service.publish_challenge(actor=current_user, challenge_id=challenge_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengePageView.model_validate(body)


@router.post("/api/challenges/{challenge_id}/accept", response_model=ChallengePageView)
def accept_challenge(
    challenge_id: str,
    payload: ChallengeAcceptRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> ChallengePageView:
    try:
        body = service.accept_challenge(actor=current_user, challenge_id=challenge_id, **payload.model_dump())
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengePageView.model_validate(body)


@router.post("/api/challenges/{challenge_id}/links", response_model=ChallengeLinkView, status_code=status.HTTP_201_CREATED)
def create_challenge_link(
    challenge_id: str,
    payload: ChallengeLinkCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> ChallengeLinkView:
    try:
        link = service.create_challenge_link(actor=current_user, challenge_id=challenge_id, **payload.model_dump())
        body = service._challenge_link_view(link)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengeLinkView.model_validate(body)


@router.post("/api/challenges/{challenge_id}/share-events", response_model=ChallengeShareEventView, status_code=status.HTTP_201_CREATED)
def record_challenge_share_event(
    challenge_id: str,
    payload: ChallengeShareEventRequest,
    service: ClubSocialService = Depends(get_service),
) -> ChallengeShareEventView:
    try:
        event = service.record_share_event(challenge_id=challenge_id, actor_user_id=None, **payload.model_dump())
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengeShareEventView.model_validate(
        {
            "id": event.id,
            "challenge_id": event.challenge_id,
            "link_id": event.link_id,
            "actor_user_id": event.actor_user_id,
            "event_type": event.event_type,
            "source_platform": event.source_platform,
            "country_code": event.country_code,
            "metadata_json": event.metadata_json or {},
            "created_at": event.created_at,
        }
    )


@router.get("/api/challenges/links/{link_code}", response_model=ChallengePageView)
def get_challenge_by_link(link_code: str, service: ClubSocialService = Depends(get_service)) -> ChallengePageView:
    try:
        body = service.challenge_page(link_code=link_code)
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengePageView.model_validate(body)


@router.get("/api/challenges/{challenge_id}", response_model=ChallengePageView)
def get_challenge(challenge_id: str, service: ClubSocialService = Depends(get_service)) -> ChallengePageView:
    try:
        body = service.challenge_page(challenge_id=challenge_id)
    except ClubSocialError as exc:
        _raise(exc)
    return ChallengePageView.model_validate(body)


@router.get("/api/clubs/{club_id}/identity/metrics", response_model=ClubIdentityMetricsView)
def get_identity_metrics(club_id: str, service: ClubSocialService = Depends(get_service)) -> ClubIdentityMetricsView:
    try:
        metrics = service.refresh_identity_metrics(club_id=club_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ClubIdentityMetricsView.model_validate(metrics, from_attributes=True)


@router.post("/api/clubs/{club_id}/identity/metrics/refresh", response_model=ClubIdentityMetricsView)
def refresh_identity_metrics(club_id: str, service: ClubSocialService = Depends(get_service)) -> ClubIdentityMetricsView:
    try:
        metrics = service.refresh_identity_metrics(club_id=club_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return ClubIdentityMetricsView.model_validate(metrics, from_attributes=True)


@router.post("/api/social/follows", response_model=SocialFollowView, status_code=status.HTTP_201_CREATED)
def follow_target(
    payload: SocialFollowRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> SocialFollowView:
    try:
        follow = service.follow_target(actor=current_user, **payload.model_dump())
        body = service._follow_view(follow)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return SocialFollowView.model_validate(body)


@router.delete("/api/social/follows", response_model=dict)
def unfollow_target(
    payload: SocialFollowRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> dict[str, str]:
    try:
        service.unfollow_target(actor=current_user, target_type=payload.target_type, club_id=payload.club_id, player_id=payload.player_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return {"status": "deleted"}


@router.get("/api/social/follows/me", response_model=SocialFollowingView)
def list_my_follows(
    target_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> SocialFollowingView:
    try:
        follows = service.list_follows(actor=current_user, target_type=target_type)
    except ClubSocialError as exc:
        _raise(exc)
    return SocialFollowingView(follows=follows)


@router.get("/api/matches/{match_id}/reactions", response_model=MatchReactionFeedView)
def list_match_reactions(match_id: str, limit: int = Query(default=30, ge=1, le=100), service: ClubSocialService = Depends(get_service)) -> MatchReactionFeedView:
    return MatchReactionFeedView(match_id=match_id, reactions=service.list_match_reactions(match_id, limit=limit))


@router.post("/api/matches/{match_id}/share-links", response_model=MatchShareLinkView, status_code=status.HTTP_201_CREATED)
def create_match_share_link(
    match_id: str,
    payload: MatchShareLinkCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> MatchShareLinkView:
    try:
        link = service.create_match_share_link(actor=current_user, match_id=match_id, **payload.model_dump())
        body = service._match_share_link_view(link)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return MatchShareLinkView.model_validate(body)


@router.post("/api/match-share-links/{share_code}/events", response_model=dict, status_code=status.HTTP_201_CREATED)
def record_match_share_event(
    share_code: str,
    payload: MatchShareEventRequest,
    service: ClubSocialService = Depends(get_service),
) -> dict[str, str]:
    try:
        service.record_match_share_event(
            share_code=share_code,
            actor_user_id=None,
            **payload.model_dump(),
        )
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return {"status": "recorded"}


@router.get("/api/match-share-links/{share_code}", response_model=MatchSharePageView)
def get_match_share_page(share_code: str, service: ClubSocialService = Depends(get_service)) -> MatchSharePageView:
    try:
        body = service.match_share_page(share_code=share_code)
    except ClubSocialError as exc:
        _raise(exc)
    return MatchSharePageView.model_validate(body)


@router.post("/api/matches/{match_id}/live-reactions", response_model=MatchLiveReactionFeedView, status_code=status.HTTP_201_CREATED)
def create_live_reaction(
    match_id: str,
    payload: MatchLiveReactionCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> MatchLiveReactionFeedView:
    try:
        service.create_live_reaction(actor=current_user, match_id=match_id, **payload.model_dump())
        reactions = service.list_live_reactions(match_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return MatchLiveReactionFeedView(match_id=match_id, reactions=reactions)


@router.get("/api/matches/{match_id}/live-reactions", response_model=MatchLiveReactionFeedView)
def list_live_reactions(
    match_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    service: ClubSocialService = Depends(get_service),
) -> MatchLiveReactionFeedView:
    try:
        reactions = service.list_live_reactions(match_id, limit=limit)
    except ClubSocialError as exc:
        _raise(exc)
    return MatchLiveReactionFeedView(match_id=match_id, reactions=reactions)


@router.post("/api/matches/{match_id}/chat", response_model=MatchChatFeedView, status_code=status.HTTP_201_CREATED)
def create_match_chat_message(
    match_id: str,
    payload: MatchChatMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    service: ClubSocialService = Depends(get_service),
) -> MatchChatFeedView:
    try:
        service.create_chat_message(actor=current_user, match_id=match_id, **payload.model_dump())
        messages = service.list_chat_messages(match_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return MatchChatFeedView(match_id=match_id, messages=messages)


@router.get("/api/matches/{match_id}/chat", response_model=MatchChatFeedView)
def list_match_chat_messages(
    match_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    service: ClubSocialService = Depends(get_service),
) -> MatchChatFeedView:
    try:
        messages = service.list_chat_messages(match_id, limit=limit)
    except ClubSocialError as exc:
        _raise(exc)
    return MatchChatFeedView(match_id=match_id, messages=messages)


@router.get("/api/clubs/{club_id}/rivalries", response_model=ClubRivalriesView)
def list_rivalries(club_id: str, service: ClubSocialService = Depends(get_service)) -> ClubRivalriesView:
    try:
        rivalries = service.list_rivalries(club_id=club_id)
    except ClubSocialError as exc:
        _raise(exc)
    return ClubRivalriesView(club_id=club_id, rivalries=rivalries)


@router.get("/api/clubs/{club_id}/rivalries/{opponent_club_id}", response_model=RivalryDetailView)
def get_rivalry_detail(club_id: str, opponent_club_id: str, service: ClubSocialService = Depends(get_service)) -> RivalryDetailView:
    try:
        body = service.rivalry_detail(club_id=club_id, opponent_club_id=opponent_club_id)
    except ClubSocialError as exc:
        _raise(exc)
    return RivalryDetailView.model_validate(body)


@router.post("/api/rivalries/matches", response_model=RivalryDetailView, status_code=status.HTTP_201_CREATED)
def record_rivalry_match(payload: RivalryMatchRecordRequest, service: ClubSocialService = Depends(get_service)) -> RivalryDetailView:
    try:
        service.record_match_outcome(**payload.model_dump())
        body = service.rivalry_detail(club_id=payload.home_club_id, opponent_club_id=payload.away_club_id)
        service.session.commit()
    except ClubSocialError as exc:
        _raise(exc)
    return RivalryDetailView.model_validate(body)
