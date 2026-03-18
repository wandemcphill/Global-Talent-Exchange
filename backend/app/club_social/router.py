from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.club_social.schemas import (
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
    MatchReactionFeedView,
    RivalryDetailView,
    RivalryMatchRecordRequest,
)
from backend.app.club_social.service import ClubSocialError, ClubSocialService
from backend.app.db import get_session
from backend.app.models.user import User

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


@router.get("/api/matches/{match_id}/reactions", response_model=MatchReactionFeedView)
def list_match_reactions(match_id: str, limit: int = Query(default=30, ge=1, le=100), service: ClubSocialService = Depends(get_service)) -> MatchReactionFeedView:
    return MatchReactionFeedView(match_id=match_id, reactions=service.list_match_reactions(match_id, limit=limit))


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
