from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.infinite_league.service import ensure_infinite_league_runtime
from app.pundits.schemas import PunditDebateResponse
from app.pundits.service import PunditService
from app.viral.service import ViralFeedError

router = APIRouter(prefix="/api/pundits", tags=["pundits"])


@router.get("/matches/{match_key}", response_model=PunditDebateResponse)
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
