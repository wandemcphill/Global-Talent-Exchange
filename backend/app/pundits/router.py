from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.infinite_league.service import ensure_infinite_league_runtime
from app.pundits.schemas import PunditDebateResponse, PunditShowResponse
from app.pundits.service import PunditService
from app.viral.service import ViralFeedError

router = APIRouter(tags=["pundits"])


@router.get("/shows/pre-match/{match_id}", response_model=PunditShowResponse)
def read_pre_match_show(match_id: str, session: Session = Depends(get_session)) -> PunditShowResponse:
    try:
        return PunditService(session).build_pre_match_show(match_id)
    except ViralFeedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/shows/post-match/{match_id}", response_model=PunditShowResponse)
def read_post_match_show(match_id: str, session: Session = Depends(get_session)) -> PunditShowResponse:
    try:
        return PunditService(session).build_post_match_show(match_id)
    except ViralFeedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/shows/debate", response_model=PunditShowResponse)
def read_debate_show(
    match_id: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> PunditShowResponse:
    try:
        return PunditService(session).build_debate_show(match_id=match_id, topic=topic)
    except ViralFeedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/pundits/matches/{match_key}", response_model=PunditDebateResponse)
def read_match_pundit_debate(
    match_key: str,
    request: Request,
    format: str = "chat",
    session: Session = Depends(get_session),
) -> PunditDebateResponse:
    try:
        return PunditService(session).build_match_debate(match_key, format=format)
    except ViralFeedError as exc:
        generated = ensure_infinite_league_runtime(request.app).build_pundit_debate(match_key, format=format)
        if generated is not None:
            return generated
        raise HTTPException(status_code=404, detail=str(exc)) from exc
