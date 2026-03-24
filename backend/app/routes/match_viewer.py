from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.models.competition_match import CompetitionMatch
from app.replay_archive.service import ensure_replay_archive
from app.schemas.match_viewer import MatchMode, MatchViewerSessionView, MatchViewStateView
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from app.services.match_timeline_service import MatchTimelineService

router = APIRouter(prefix="/match-viewer", tags=["match-viewer"])


def get_match_timeline_service() -> MatchTimelineService:
    return MatchTimelineService()


def get_match_viewer_scaling_service() -> MatchViewerScalingService:
    return MatchViewerScalingService()


def get_match_integrity_service() -> MatchIntegrityService:
    return MatchIntegrityService()


@router.get("/{match_key}", response_model=MatchViewStateView)
def read_match_viewer_timeline(
    match_key: str,
    request: Request,
    mode: MatchMode = Query(default=MatchMode.STANDARD),
    session: Session = Depends(get_session),
    service: MatchTimelineService = Depends(get_match_timeline_service),
    scaling_service: MatchViewerScalingService = Depends(get_match_viewer_scaling_service),
    integrity_service: MatchIntegrityService = Depends(get_match_integrity_service),
) -> MatchViewStateView:
    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        stored = (match.metadata_json or {}).get("match_viewer")
        fairness = (match.metadata_json or {}).get("fairness")
        if isinstance(stored, dict):
            base_view = MatchViewStateView.model_validate(stored)
            if isinstance(fairness, dict):
                try:
                    return integrity_service.build_viewer_session(
                        match_id=match_key,
                        view_state=scaling_service.transform(base_view, mode=mode),
                        fairness_metadata=fairness,
                        mode=mode,
                        canonical_view_state=base_view,
                    )
                except MatchIntegrityViolation as exc:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
            return scaling_service.transform(base_view, mode=mode)

    replay_archive = ensure_replay_archive(request.app)
    replay_key = match_key if match_key.startswith("replay:") else f"replay:{match_key}"
    record = replay_archive.repository.get_latest_record(replay_key)
    if record is not None:
        return scaling_service.transform(service.build_from_archive_record(record), mode=mode)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Match viewer payload for {match_key} was not found.",
    )


@router.get("/{match_key}/session", response_model=MatchViewerSessionView)
def read_match_viewer_session(
    match_key: str,
    request: Request,
    mode: MatchMode = Query(default=MatchMode.STANDARD),
    token: str | None = Query(default=None),
    session: Session = Depends(get_session),
    service: MatchTimelineService = Depends(get_match_timeline_service),
    scaling_service: MatchViewerScalingService = Depends(get_match_viewer_scaling_service),
    integrity_service: MatchIntegrityService = Depends(get_match_integrity_service),
) -> MatchViewerSessionView:
    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        stored = (match.metadata_json or {}).get("match_viewer")
        fairness = (match.metadata_json or {}).get("fairness")
        if isinstance(stored, dict):
            canonical_view = MatchViewStateView.model_validate(stored)
            base_view = scaling_service.transform(canonical_view, mode=mode)
            try:
                return integrity_service.build_viewer_session(
                    match_id=match_key,
                    view_state=base_view,
                    fairness_metadata=fairness if isinstance(fairness, dict) else None,
                    mode=mode,
                    continuation_token=token,
                    canonical_view_state=canonical_view,
                )
            except MatchIntegrityViolation as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    replay_archive = ensure_replay_archive(request.app)
    replay_key = match_key if match_key.startswith("replay:") else f"replay:{match_key}"
    record = replay_archive.repository.get_latest_record(replay_key)
    if record is not None:
        base_view = scaling_service.transform(service.build_from_archive_record(record), mode=mode)
        try:
            return integrity_service.build_viewer_session(
                match_id=match_key,
                view_state=base_view,
                fairness_metadata=None,
                mode=mode,
                continuation_token=token,
            )
        except MatchIntegrityViolation as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Match viewer payload for {match_key} was not found.",
    )


__all__ = [
    "get_match_integrity_service",
    "get_match_timeline_service",
    "get_match_viewer_scaling_service",
    "router",
]

