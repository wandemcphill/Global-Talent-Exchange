from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai_reporter.schemas import AIReporterRunRequest, AIReporterRunResponse, AIReporterStoryView
from app.ai_reporter.service import AIReporterService
from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User

router = APIRouter(prefix="/ai-reporter", tags=["ai-reporter"])


@router.get("/feed", response_model=list[AIReporterStoryView])
def list_ai_reporter_feed(
    beat: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[AIReporterStoryView]:
    return AIReporterService(session).list_reporter_feed(beat=beat, limit=limit)


@router.post("/run", response_model=AIReporterRunResponse)
def run_ai_reporter(
    payload: AIReporterRunRequest,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> AIReporterRunResponse:
    response = AIReporterService(session).run_daily_digest(
        beats=payload.beats or None,
        limit_per_beat=payload.limit_per_beat,
        dry_run=payload.dry_run,
    )
    if not payload.dry_run:
        session.commit()
    return response

