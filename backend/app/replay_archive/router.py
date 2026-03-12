from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.replay_archive.schemas import CountdownView, ReplayArchiveRecord, ReplaySummaryView
from backend.app.replay_archive.service import ensure_replay_archive

router = APIRouter(prefix="/replays", tags=["replay-archive"])


@router.get("/me", response_model=list[ReplaySummaryView])
def list_replays_for_current_user(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> list[ReplaySummaryView]:
    replay_archive = ensure_replay_archive(request.app)
    return replay_archive.list_for_user(current_user.id, limit=limit)


@router.get("/public/featured", response_model=list[ReplaySummaryView])
def list_featured_public_matches(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[ReplaySummaryView]:
    replay_archive = ensure_replay_archive(request.app)
    return replay_archive.list_featured_public(limit=limit)


@router.get("/countdown/{fixture_id}", response_model=CountdownView)
def read_public_countdown_view(
    fixture_id: str,
    request: Request,
) -> CountdownView:
    replay_archive = ensure_replay_archive(request.app)
    countdown = replay_archive.get_public_countdown(fixture_id)
    if countdown is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Countdown metadata for fixture {fixture_id} is not publicly available.",
        )
    return countdown


@router.get("/{replay_id}", response_model=ReplayArchiveRecord)
def read_replay_detail(
    replay_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ReplayArchiveRecord:
    replay_archive = ensure_replay_archive(request.app)
    replay = replay_archive.get_for_user(replay_id, user_id=current_user.id)
    if replay is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replay {replay_id} was not found.",
        )
    return replay
