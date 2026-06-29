from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.live_match.schemas import (
    CreateLiveMatchRequest,
    HalftimeReadyRequest,
    LiveMatchSessionView,
    LiveTeamTacticsView,
    SetLiveTacticsRequest,
)
from app.live_match.service import (
    LiveMatchEngine,
    LiveMatchError,
    LiveMatchSession,
    get_live_match_engine,
)
from app.models.user import User

router = APIRouter(prefix="/live-match", tags=["live-match"])


def _engine() -> LiveMatchEngine:
    return get_live_match_engine()


def _raise(exc: LiveMatchError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _tactics_view(session: LiveMatchSession, side: str) -> LiveTeamTacticsView:
    tactics = session.tactics_for(side)
    return LiveTeamTacticsView(
        formation=tactics.formation,
        mentality=tactics.mentality,
        pressing=tactics.pressing,
        tempo=tactics.tempo,
    )


def _view(session: LiveMatchSession) -> LiveMatchSessionView:
    remaining: int | None = None
    if session.phase == "half_time" and session.halftime_deadline is not None:
        delta = (session.halftime_deadline - datetime.now(tz=timezone.utc)).total_seconds()
        remaining = max(0, ceil(delta))
    return LiveMatchSessionView(
        match_id=session.match_id,
        minute=session.minute,
        phase=session.phase,
        home_name=session.home_name,
        away_name=session.away_name,
        home_score=session.home_score,
        away_score=session.away_score,
        home_tactics=_tactics_view(session, "home"),
        away_tactics=_tactics_view(session, "away"),
        halftime_seconds_remaining=remaining,
        halftime_ready=sorted(session.halftime_ready),
        events=list(session.events[-40:]),
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
    )
    return _view(session)


@router.get("/sessions/{match_id}", response_model=LiveMatchSessionView)
def get_session(
    match_id: str,
    engine: LiveMatchEngine = Depends(_engine),
) -> LiveMatchSessionView:
    try:
        return _view(engine.get(match_id))
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
        return _view(
            engine.set_tactics(
                match_id=match_id,
                side=payload.side,
                formation=payload.formation,
                mentality=payload.mentality,
                pressing=payload.pressing,
                tempo=payload.tempo,
            )
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
        return _view(engine.mark_halftime_ready(match_id=match_id, side=payload.side))
    except LiveMatchError as exc:
        _raise(exc)
        raise
