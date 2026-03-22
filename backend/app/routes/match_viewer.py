from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.competition_match import CompetitionMatch
from app.replay_archive.service import ensure_replay_archive
from app.schemas.match_viewer import MatchViewStateView
from app.services.match_timeline_service import MatchTimelineService

router = APIRouter(prefix="/match-viewer", tags=["match-viewer"])


def get_match_timeline_service() -> MatchTimelineService:
    return MatchTimelineService()


@router.get("/{match_key}", response_model=MatchViewStateView)
def read_match_viewer_timeline(
    match_key: str,
    request: Request,
    session: Session = Depends(get_session),
    service: MatchTimelineService = Depends(get_match_timeline_service),
) -> MatchViewStateView:
    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        stored = (match.metadata_json or {}).get("match_viewer")
        if isinstance(stored, dict):
            return MatchViewStateView.model_validate(stored)

    replay_archive = ensure_replay_archive(request.app)
    replay_key = match_key if match_key.startswith("replay:") else f"replay:{match_key}"
    record = replay_archive.repository.get_latest_record(replay_key)
    if record is not None:
        return service.build_from_archive_record(record)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Match viewer payload for {match_key} was not found.",
    )


__all__ = ["get_match_timeline_service", "router"]

