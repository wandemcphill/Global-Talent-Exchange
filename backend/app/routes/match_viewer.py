from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.infinite_league.service import ensure_infinite_league_runtime
from app.live_matches.service import ensure_live_match_hub
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.replay_archive.service import ensure_replay_archive
from app.schemas.match_viewer import MatchMode, MatchViewerSessionView, MatchViewStateView
from app.services.ads.engine import AdDecisionEngine
from app.services.match_viewer_presentation_service import MatchViewerPresentationService
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from app.services.match_timeline_service import MatchTimelineService

router = APIRouter(prefix="/match-viewer", tags=["match-viewer"])


@dataclass(slots=True)
class _ResolvedMatchViewerContext:
    canonical_view: MatchViewStateView
    metadata_json: dict[str, object]
    fairness_metadata: dict[str, object] | None
    match: CompetitionMatch | None


def get_match_timeline_service() -> MatchTimelineService:
    return MatchTimelineService()


def get_match_viewer_scaling_service() -> MatchViewerScalingService:
    return MatchViewerScalingService()


def get_match_integrity_service() -> MatchIntegrityService:
    return MatchIntegrityService()


def get_ad_decision_engine() -> AdDecisionEngine:
    return AdDecisionEngine()


def get_match_viewer_presentation_service() -> MatchViewerPresentationService:
    return MatchViewerPresentationService()


def _attach_presentation(
    view_state: MatchViewStateView,
    *,
    match_key: str,
    presentation_service: MatchViewerPresentationService,
    metadata_json: dict[str, object] | None = None,
    match: CompetitionMatch | None = None,
) -> MatchViewStateView:
    return view_state.model_copy(
        update={
            "presentation_package": presentation_service.build(
                match_key=match_key,
                view_state=view_state,
                metadata_json=metadata_json,
                match=match,
            )
        }
    )


def _attach_monetization(
    view_state: MatchViewStateView,
    *,
    match_key: str,
    session: Session,
    ad_engine: AdDecisionEngine,
    metadata_json: dict[str, object] | None = None,
    match: CompetitionMatch | None = None,
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
    monetization = ad_engine.build_viewer_monetization(
        match_id=match_key,
        view_state=view_state,
        ad_profile=ad_profile if isinstance(ad_profile, dict) else None,
        match_context=match_context,
    )
    gift_metadata = _match_gift_metadata(
        session=session,
        match=match,
        metadata_json=metadata_json if isinstance(metadata_json, dict) else None,
    )
    if gift_metadata:
        monetization = monetization.model_copy(
            update={
                "metadata": {
                    **dict(monetization.metadata or {}),
                    **gift_metadata,
                }
            }
        )
    return view_state.model_copy(update={"monetization": monetization})


def _match_gift_metadata(
    *,
    session: Session,
    match: CompetitionMatch | None,
    metadata_json: dict[str, object] | None,
) -> dict[str, object]:
    if match is None:
        return {}
    competition = session.get(UserCompetition, match.competition_id)
    if competition is None:
        return {}
    recipient_user_id = competition.host_user_id.strip()
    if not recipient_user_id:
        return {}
    return {
        "gift_recipient_user_id": recipient_user_id,
        "gift_recipient_label": _match_gift_recipient_label(
            competition=competition,
            metadata_json=metadata_json,
        ),
        "gift_source_scope": _match_gift_source_scope(
            competition=competition,
            metadata_json=metadata_json,
        ),
    }


def _match_gift_recipient_label(
    *,
    competition: UserCompetition,
    metadata_json: dict[str, object] | None,
) -> str:
    if isinstance(metadata_json, dict):
        for key in ("creator_name", "creator_label", "host_name", "host_label"):
            value = metadata_json.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if competition.name.strip():
        return competition.name.strip()
    return "Match host"


def _match_gift_source_scope(
    *,
    competition: UserCompetition,
    metadata_json: dict[str, object] | None,
) -> str:
    if isinstance(metadata_json, dict):
        explicit = metadata_json.get("gift_source_scope")
        if isinstance(explicit, str) and explicit.strip():
            normalized = explicit.strip().lower()
            if normalized in {"user_hosted", "gtex_competition"}:
                return normalized
    normalized_source_type = (competition.source_type or "").strip().lower()
    normalized_host_user = competition.host_user_id.strip().lower()
    if normalized_source_type in {
        "gtex",
        "gtex_official",
        "gtex_platform",
        "official",
        "platform",
    }:
        return "gtex_competition"
    if normalized_host_user.startswith("gtex") or normalized_host_user == "platform":
        return "gtex_competition"
    return "user_hosted"


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


def _resolve_match_viewer_context(
    *,
    match_key: str,
    request: Request,
    session: Session,
    service: MatchTimelineService,
) -> _ResolvedMatchViewerContext | None:
    match = session.get(CompetitionMatch, match_key)
    metadata_json = dict(match.metadata_json or {}) if match is not None else {}
    if match is not None:
        stored = metadata_json.get("match_viewer")
        fairness = metadata_json.get("fairness")
        if isinstance(stored, dict):
            return _ResolvedMatchViewerContext(
                canonical_view=MatchViewStateView.model_validate(stored),
                metadata_json=metadata_json,
                fairness_metadata=fairness if isinstance(fairness, dict) else None,
                match=match,
            )

    replay_archive = ensure_replay_archive(request.app)
    replay_key = match_key if match_key.startswith("replay:") else f"replay:{match_key}"
    record = replay_archive.repository.get_latest_record(replay_key)
    if record is not None:
        return _ResolvedMatchViewerContext(
            canonical_view=service.build_from_archive_record(record),
            metadata_json={},
            fairness_metadata=None,
            match=None,
        )

    live_view = _resolve_live_view_state(
        match_key=match_key,
        request=request,
        match=match,
        service=service,
    )
    if live_view is None:
        return None
    canonical_view, live_metadata = live_view
    return _ResolvedMatchViewerContext(
        canonical_view=canonical_view,
        metadata_json=live_metadata,
        fairness_metadata=None,
        match=match,
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
    presentation_service: MatchViewerPresentationService = Depends(get_match_viewer_presentation_service),
    ad_engine: AdDecisionEngine = Depends(get_ad_decision_engine),
) -> MatchViewStateView:
    resolved = _resolve_match_viewer_context(
        match_key=match_key,
        request=request,
        session=session,
        service=service,
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match viewer payload for {match_key} was not found.",
        )

    if resolved.fairness_metadata is not None:
        try:
            secured = integrity_service.build_viewer_session(
                match_id=match_key,
                view_state=scaling_service.transform(resolved.canonical_view, mode=mode),
                fairness_metadata=resolved.fairness_metadata,
                mode=mode,
                canonical_view_state=resolved.canonical_view,
            )
            secured = _attach_presentation(
                secured,
                match_key=match_key,
                presentation_service=presentation_service,
                metadata_json=resolved.metadata_json,
                match=resolved.match,
            )
            return _attach_monetization(
                secured,
                match_key=match_key,
                session=session,
                ad_engine=ad_engine,
                metadata_json=resolved.metadata_json,
                match=resolved.match,
            )
        except MatchIntegrityViolation as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    transformed = _attach_presentation(
        scaling_service.transform(resolved.canonical_view, mode=mode),
        match_key=match_key,
        presentation_service=presentation_service,
        metadata_json=resolved.metadata_json,
        match=resolved.match,
    )
    return _attach_monetization(
        transformed,
        match_key=match_key,
        session=session,
        ad_engine=ad_engine,
        metadata_json=resolved.metadata_json,
        match=resolved.match,
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
    presentation_service: MatchViewerPresentationService = Depends(get_match_viewer_presentation_service),
    ad_engine: AdDecisionEngine = Depends(get_ad_decision_engine),
) -> MatchViewerSessionView:
    resolved = _resolve_match_viewer_context(
        match_key=match_key,
        request=request,
        session=session,
        service=service,
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match viewer payload for {match_key} was not found.",
        )

    base_view = scaling_service.transform(resolved.canonical_view, mode=mode)
    try:
        secured = integrity_service.build_viewer_session(
            match_id=match_key,
            view_state=base_view,
            fairness_metadata=resolved.fairness_metadata,
            mode=mode,
            continuation_token=token,
            canonical_view_state=resolved.canonical_view,
        )
        secured = _attach_presentation(
            secured,
            match_key=match_key,
            presentation_service=presentation_service,
            metadata_json=resolved.metadata_json,
            match=resolved.match,
        )
        return MatchViewerSessionView.model_validate(
            _attach_monetization(
                secured,
                match_key=match_key,
                session=session,
                ad_engine=ad_engine,
                metadata_json=resolved.metadata_json,
                match=resolved.match,
            ).model_dump(mode="json")
        )
    except MatchIntegrityViolation as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc


__all__ = [
    "get_ad_decision_engine",
    "get_match_integrity_service",
    "get_match_viewer_presentation_service",
    "get_match_timeline_service",
    "get_match_viewer_scaling_service",
    "router",
]
