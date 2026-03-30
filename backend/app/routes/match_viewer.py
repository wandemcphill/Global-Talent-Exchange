from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.infinite_league.service import ensure_infinite_league_runtime
from app.live_matches.service import ensure_live_match_hub
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


def _metadata_team_name(metadata_json: dict[str, object], *, side: str) -> str | None:
    direct_key = f"{side}_team_name"
    direct_value = metadata_json.get(direct_key)
    if isinstance(direct_value, str) and direct_value.strip():
        return direct_value
    replay_payload = metadata_json.get("replay_payload")
    if isinstance(replay_payload, dict):
        summary = replay_payload.get("summary")
        if isinstance(summary, dict):
            stats = summary.get(f"{side}_stats")
            if isinstance(stats, dict):
                team_name = stats.get("team_name")
                if isinstance(team_name, str) and team_name.strip():
                    return team_name
    return None


def _resolve_live_view_state(
    *,
    match_key: str,
    request: Request,
    match: CompetitionMatch | None,
    service: MatchTimelineService,
) -> tuple[MatchViewStateView, dict[str, object]] | None:
    metadata_json = dict(match.metadata_json or {}) if match is not None else {}
    live_hub = ensure_live_match_hub(request.app)
    live_state = live_hub.get_state(match_key)
    if live_state is not None:
        events, _ = live_hub.get_events_since(match_key, 0)
        return (
            service.build_from_live_stream(
                match_id=match_key,
                source="live_match_hub",
                home_team_id=match.home_club_id if match is not None else None,
                home_team_name=(
                    _metadata_team_name(metadata_json, side="home")
                    or (match.home_club_id if match is not None else None)
                ),
                away_team_id=match.away_club_id if match is not None else None,
                away_team_name=(
                    _metadata_team_name(metadata_json, side="away")
                    or (match.away_club_id if match is not None else None)
                ),
                events=events,
                live_state=live_state,
            ),
            metadata_json,
        )
    infinite_stream = ensure_infinite_league_runtime(request.app).live_stream(match_key)
    if infinite_stream is not None:
        return (
            service.build_from_live_stream(
                match_id=infinite_stream.match_id,
                source="infinite_league_runtime",
                home_team_id=infinite_stream.home_team_id,
                home_team_name=infinite_stream.home_team_name,
                away_team_id=infinite_stream.away_team_id,
                away_team_name=infinite_stream.away_team_name,
                events=list(infinite_stream.events),
                live_state=None,
            ),
            metadata_json,
        )
    return None


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

    live_view = _resolve_live_view_state(
        match_key=match_key,
        request=request,
        match=match,
        service=service,
    )
    if live_view is not None:
        base_view, metadata_json = live_view
        return _attach_monetization(
            scaling_service.transform(base_view, mode=mode),
            match_key=match_key,
            ad_engine=ad_engine,
            metadata_json=metadata_json,
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

    live_view = _resolve_live_view_state(
        match_key=match_key,
        request=request,
        match=match,
        service=service,
    )
    if live_view is not None:
        base_view, metadata_json = live_view
        secured = integrity_service.build_viewer_session(
            match_id=match_key,
            view_state=scaling_service.transform(base_view, mode=mode),
            fairness_metadata=None,
            mode=mode,
            continuation_token=token,
        )
        return MatchViewerSessionView.model_validate(
            _attach_monetization(
                secured,
                match_key=match_key,
                ad_engine=ad_engine,
                metadata_json=metadata_json,
            ).model_dump(mode="json")
        )

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

