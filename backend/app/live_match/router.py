from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.live_match.schemas import (
    CreateLiveMatchRequest,
    HalftimeReadyRequest,
    LiveMatchSessionView,
    SetLiveTacticsRequest,
)
from app.live_match.service import (
    LiveMatchEngine,
    LiveMatchError,
    LiveMatchSession,
    get_live_match_engine,
    session_public_state,
)
from app.models.user import User

router = APIRouter(prefix="/live-match", tags=["live-match"])


def _engine() -> LiveMatchEngine:
    return get_live_match_engine()


def _raise(exc: LiveMatchError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _view(session: LiveMatchSession, *, user_id: str | None = None) -> LiveMatchSessionView:
    return LiveMatchSessionView(
        **session_public_state(session),
        your_side=session.side_for_user(user_id),
    )


@router.post("/sessions", response_model=LiveMatchSessionView, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: CreateLiveMatchRequest,
    engine: LiveMatchEngine = Depends(_engine),
    current_user: User = Depends(get_current_user),
) -> LiveMatchSessionView:
    session = engine.create(
        match_id=payload.match_id,
        home_id=payload.home_id,
        away_id=payload.away_id,
        home_name=payload.home_name,
        away_name=payload.away_name,
        home_overall=payload.home_overall,
        away_overall=payload.away_overall,
        home_formation=payload.home_formation,
        away_formation=payload.away_formation,
        home_user_id=payload.home_user_id,
        away_user_id=payload.away_user_id,
    )
    return _view(session, user_id=current_user.id)


@router.get("/sessions/{match_id}", response_model=LiveMatchSessionView)
def get_session(
    match_id: str,
    engine: LiveMatchEngine = Depends(_engine),
    current_user: User = Depends(get_current_user),
) -> LiveMatchSessionView:
    try:
        return _view(engine.get(match_id), user_id=current_user.id)
    except LiveMatchError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/sessions/{match_id}/tick", response_model=LiveMatchSessionView)
def tick_session(
    match_id: str,
    engine: LiveMatchEngine = Depends(_engine),
) -> LiveMatchSessionView:
    try:
        return _view(engine.tick(match_id))
    except LiveMatchError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/sessions/{match_id}/tactics", response_model=LiveMatchSessionView)
def set_tactics(
    match_id: str,
    payload: SetLiveTacticsRequest,
    engine: LiveMatchEngine = Depends(_engine),
    current_user: User = Depends(get_current_user),
) -> LiveMatchSessionView:
    try:
        side = engine.resolve_owned_side(match_id=match_id, user_id=current_user.id, side=payload.side)
        return _view(
            engine.set_tactics(
                match_id=match_id,
                side=side,
                formation=payload.formation,
                mentality=payload.mentality,
                pressing=payload.pressing,
                tempo=payload.tempo,
            ),
            user_id=current_user.id,
        )
    except LiveMatchError as exc:
        _raise(exc)
        raise


@router.post("/sessions/{match_id}/halftime/ready", response_model=LiveMatchSessionView)
def halftime_ready(
    match_id: str,
    payload: HalftimeReadyRequest,
    engine: LiveMatchEngine = Depends(_engine),
    current_user: User = Depends(get_current_user),
) -> LiveMatchSessionView:
    try:
        side = engine.resolve_owned_side(match_id=match_id, user_id=current_user.id, side=payload.side)
        return _view(engine.mark_halftime_ready(match_id=match_id, side=side), user_id=current_user.id)
    except LiveMatchError as exc:
        _raise(exc)
        raise
