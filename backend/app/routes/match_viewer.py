from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.models.competition_match import CompetitionMatch
from app.replay_archive.service import ensure_replay_archive
from app.schemas.match_viewer import MatchMode, MatchViewerSessionView, MatchViewStateView
from app.services.ads.engine import AdDecisionEngine
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from app.services.match_timeline_service import MatchTimelineService

router = APIRouter(prefix="/match-viewer", tags=["match-viewer"])


def get_match_timeline_service() -> MatchTimelineService:
    return MatchTimelineService()


def get_match_viewer_scaling_service() -> MatchViewerScalingService:
    return MatchViewerScalingService()


def get_match_integrity_service() -> MatchIntegrityService:
    return MatchIntegrityService()


def get_ad_decision_engine() -> AdDecisionEngine:
    return AdDecisionEngine()


def _attach_monetization(
    view_state: MatchViewStateView,
    *,
    match_key: str,
    ad_engine: AdDecisionEngine,
    metadata_json: dict[str, object] | None = None,
) -> MatchViewStateView:
    ad_profile = metadata_json.get("ad_profile") if isinstance(metadata_json, dict) else None
    match_context = {
        "home_team_name": view_state.home_team.team_name,
        "away_team_name": view_state.away_team.team_name,
        "competition_name": view_state.source,
    }
    if isinstance(metadata_json, dict):
        for key in ("country", "market_country", "competition_name"):
            value = metadata_json.get(key)
            if isinstance(value, str) and value.strip():
                match_context[key] = value
    return view_state.model_copy(
        update={
            "monetization": ad_engine.build_viewer_monetization(
                match_id=match_key,
                view_state=view_state,
                ad_profile=ad_profile if isinstance(ad_profile, dict) else None,
                match_context=match_context,
            )
        }
    )


@router.get("/{match_key}", response_model=MatchViewStateView)
def read_match_viewer_timeline(
    match_key: str,
    request: Request,
    mode: MatchMode = Query(default=MatchMode.STANDARD),
    session: Session = Depends(get_session),
    service: MatchTimelineService = Depends(get_match_timeline_service),
    scaling_service: MatchViewerScalingService = Depends(get_match_viewer_scaling_service),
    integrity_service: MatchIntegrityService = Depends(get_match_integrity_service),
    ad_engine: AdDecisionEngine = Depends(get_ad_decision_engine),
) -> MatchViewStateView:
    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        stored = (match.metadata_json or {}).get("match_viewer")
        fairness = (match.metadata_json or {}).get("fairness")
        if isinstance(stored, dict):
            base_view = MatchViewStateView.model_validate(stored)
            if isinstance(fairness, dict):
                try:
                    secured = integrity_service.build_viewer_session(
                        match_id=match_key,
                        view_state=scaling_service.transform(base_view, mode=mode),
                        fairness_metadata=fairness,
                        mode=mode,
                        canonical_view_state=base_view,
                    )
                    return _attach_monetization(
                        secured,
                        match_key=match_key,
                        ad_engine=ad_engine,
                        metadata_json=match.metadata_json or {},
                    )
                except MatchIntegrityViolation as exc:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
            return _attach_monetization(
                scaling_service.transform(base_view, mode=mode),
                match_key=match_key,
                ad_engine=ad_engine,
                metadata_json=match.metadata_json or {},
            )

    replay_archive = ensure_replay_archive(request.app)
    replay_key = match_key if match_key.startswith("replay:") else f"replay:{match_key}"
    record = replay_archive.repository.get_latest_record(replay_key)
    if record is not None:
        return _attach_monetization(
            scaling_service.transform(service.build_from_archive_record(record), mode=mode),
            match_key=match_key,
            ad_engine=ad_engine,
        )

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
    ad_engine: AdDecisionEngine = Depends(get_ad_decision_engine),
) -> MatchViewerSessionView:
    match = session.get(CompetitionMatch, match_key)
    if match is not None:
        stored = (match.metadata_json or {}).get("match_viewer")
        fairness = (match.metadata_json or {}).get("fairness")
        if isinstance(stored, dict):
            canonical_view = MatchViewStateView.model_validate(stored)
            base_view = scaling_service.transform(canonical_view, mode=mode)
            try:
                secured = integrity_service.build_viewer_session(
                    match_id=match_key,
                    view_state=base_view,
                    fairness_metadata=fairness if isinstance(fairness, dict) else None,
                    mode=mode,
                    continuation_token=token,
                    canonical_view_state=canonical_view,
                )
                return MatchViewerSessionView.model_validate(
                    _attach_monetization(
                        secured,
                        match_key=match_key,
                        ad_engine=ad_engine,
                        metadata_json=match.metadata_json or {},
                    ).model_dump(mode="json")
                )
            except MatchIntegrityViolation as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    replay_archive = ensure_replay_archive(request.app)
    replay_key = match_key if match_key.startswith("replay:") else f"replay:{match_key}"
    record = replay_archive.repository.get_latest_record(replay_key)
    if record is not None:
        base_view = scaling_service.transform(service.build_from_archive_record(record), mode=mode)
        try:
            secured = integrity_service.build_viewer_session(
                match_id=match_key,
                view_state=base_view,
                fairness_metadata=None,
                mode=mode,
                continuation_token=token,
            )
            return MatchViewerSessionView.model_validate(
                _attach_monetization(
                    secured,
                    match_key=match_key,
                    ad_engine=ad_engine,
                ).model_dump(mode="json")
            )
        except MatchIntegrityViolation as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Match viewer payload for {match_key} was not found.",
    )


__all__ = [
    "get_ad_decision_engine",
    "get_match_integrity_service",
    "get_match_timeline_service",
    "get_match_viewer_scaling_service",
    "router",
]

