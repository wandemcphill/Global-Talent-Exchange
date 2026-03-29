from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import IdentityContext, get_current_user, get_session, require_identity
from app.models.user import User
from app.users.affinity_service import UserAffinityService
from app.users.follow_service import FollowGraphError, FollowGraphNotFoundError, build_follow_graph_service
from app.users.schemas import (
    FollowListResponse,
    FollowMutationView,
    SuggestedFollowResponse,
    UserAffinityProfileView,
    UserPublic,
)

router = APIRouter(tags=["users"])
users_router = APIRouter(prefix="/users", tags=["users"])
follow_router = APIRouter(tags=["users"])


def get_user_affinity_service(session: Session = Depends(get_session)) -> UserAffinityService:
    return UserAffinityService(session)


def get_follow_graph_service(
    request: Request,
    session: Session = Depends(get_session),
):
    return build_follow_graph_service(app=request.app, session=session)


def _raise_follow_graph_error(exc: FollowGraphError) -> None:
    if isinstance(exc, FollowGraphNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@users_router.get("/me", response_model=UserPublic)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@users_router.get("/me/profile", response_model=UserAffinityProfileView)
def read_current_user_affinity_profile(
    format_key: str | None = Query(default=None, alias="format"),
    creator_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: UserAffinityService = Depends(get_user_affinity_service),
) -> UserAffinityProfileView:
    return UserAffinityProfileView.model_validate(
        service.get_profile(
            current_user,
            format_key=format_key,
            creator_id=creator_id,
        )
    )


@follow_router.post("/follow/{user_id}", response_model=FollowMutationView)
def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    identity: IdentityContext = Depends(require_identity),
    service=Depends(get_follow_graph_service),
    session: Session = Depends(get_session),
) -> FollowMutationView:
    _ = identity
    try:
        payload = service.follow(actor=current_user, following_id=user_id)
    except FollowGraphError as exc:
        _raise_follow_graph_error(exc)
    session.commit()
    return FollowMutationView.model_validate(payload)


@follow_router.delete("/follow/{user_id}", response_model=FollowMutationView)
def unfollow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    identity: IdentityContext = Depends(require_identity),
    service=Depends(get_follow_graph_service),
    session: Session = Depends(get_session),
) -> FollowMutationView:
    _ = identity
    try:
        payload = service.unfollow(actor=current_user, following_id=user_id)
    except FollowGraphError as exc:
        _raise_follow_graph_error(exc)
    session.commit()
    return FollowMutationView.model_validate(payload)


@users_router.get("/suggestions", response_model=SuggestedFollowResponse)
def read_follow_suggestions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service=Depends(get_follow_graph_service),
) -> SuggestedFollowResponse:
    payload = service.suggest_users(actor=current_user, limit=max(limit, 1))
    return SuggestedFollowResponse.model_validate(payload)


@users_router.get("/{user_id}/followers", response_model=FollowListResponse)
def read_user_followers(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service=Depends(get_follow_graph_service),
) -> FollowListResponse:
    try:
        payload = service.list_followers(user_id=user_id, limit=max(limit, 1))
    except FollowGraphError as exc:
        _raise_follow_graph_error(exc)
    return FollowListResponse.model_validate(payload)


@users_router.get("/{user_id}/following", response_model=FollowListResponse)
def read_user_following(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    service=Depends(get_follow_graph_service),
) -> FollowListResponse:
    try:
        payload = service.list_following(user_id=user_id, limit=max(limit, 1))
    except FollowGraphError as exc:
        _raise_follow_graph_error(exc)
    return FollowListResponse.model_validate(payload)


router.include_router(users_router)
router.include_router(follow_router)
