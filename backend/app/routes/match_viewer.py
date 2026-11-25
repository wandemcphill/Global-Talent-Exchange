from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_current_user
from app.db import get_session
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.models.user import User
from app.infinite_league.service import ensure_infinite_league_runtime
from app.live_matches.service import ensure_live_match_hub
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.fast_match import FastMatchSession, FastMatchSessionStatus
from app.replay_archive.service import ensure_replay_archive
from app.match_engine.simulation.offside_var import (
    BROADCAST_CATEGORY_DURATION_WINDOWS,
    BROADCAST_CATEGORY_MAX_SECONDS,
    MatchBroadcastCategory,
    resolve_match_broadcast_category,
)
from app.schemas.match_viewer import MatchMode, MatchViewerSessionView, MatchViewStateView
from app.services.ads.engine import AdDecisionEngine
from app.services.match_viewer_presentation_service import MatchViewerPresentationService
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from app.services.match_timeline_service import MatchTimelineService

router = APIRouter(prefix="/match-viewer", tags=["match-viewer"])
logger = logging.getLogger(__name__)


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


def _protected_runtime_enabled(app) -> bool:
    settings = getattr(app.state, "settings", None)
    environment = str(getattr(settings, "app_env", "") or "").strip().lower()
    return environment in {"production", "prod", "staging"}


_SPORTING_TACTICAL_ROLES: frozenset[str] = frozenset(
    {
        "first_team_manager",
        "general_manager",
        "technical_director",
    }
)


def _has_sporting_tactical_staff_appointment(
    user_id: str,
    participating_club_ids: set[str],
    session: Session,
) -> bool:
    """Checks only current, persisted appointments on clubs actually playing this match.

    The owner-console roster is the authoritative source for these roles. No synthetic
    delegation-policy model or client-supplied role claims are trusted here.
    """
    from app.owner_console.models import OwnerClubState

    states = session.scalars(select(OwnerClubState).where(OwnerClubState.club_id.in_(participating_club_ids))).all()
    for state in states:
        manager = state.manager_json if isinstance(state.manager_json, dict) else {}
        manager_name = str(manager.get("name") or manager.get("display_name") or "").strip()
        if manager_name and not manager.get("is_vacant"):
            if user_id in {
                str(manager.get("user_id") or ""),
                str(manager.get("delegate_user_id") or ""),
            }:
                return True

        facilities = state.facilities_json if isinstance(state.facilities_json, dict) else {}
        executive_staff = facilities.get("_executive_staff")
        if not isinstance(executive_staff, dict):
            continue
        for role_key, staff_record in executive_staff.items():
            if role_key not in _SPORTING_TACTICAL_ROLES or not isinstance(staff_record, dict):
                continue
            staff_name = str(staff_record.get("name") or staff_record.get("display_name") or "").strip()
            if not staff_name or staff_record.get("is_vacant"):
                continue
            if user_id in {
                str(staff_record.get("user_id") or ""),
                str(staff_record.get("delegate_user_id") or ""),
            }:
                return True
    return False


def _is_owner_or_manager(
    user: User | None,
    match: CompetitionMatch | None,
    session: Session,
) -> bool:
    if user is None:
        return False
    if getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False):
        return True
    if match is None:
        return False
    participating_club_ids = {match.home_club_id, match.away_club_id} - {None, ""}
    if not participating_club_ids:
        return False

    try:
        from sqlalchemy import func
        from app.owner_console.models import OwnerClubState

        owned_state = session.scalar(
            select(func.count(OwnerClubState.id)).where(
                OwnerClubState.owner_user_id == user.id,
                OwnerClubState.club_id.in_(participating_club_ids),
            )
        )
        if owned_state and owned_state > 0:
            return True
    except Exception:
        pass

    try:
        from sqlalchemy import func
        from app.models.club_profile import ClubProfile

        owned_profile = session.scalar(
            select(func.count(ClubProfile.id)).where(
                ClubProfile.owner_user_id == user.id,
                ClubProfile.id.in_(participating_club_ids),
            )
        )
        if owned_profile and owned_profile > 0:
            return True
    except Exception:
        pass

    try:
        return _has_sporting_tactical_staff_appointment(
            str(user.id),
            {str(cid) for cid in participating_club_ids if cid},
            session,
        )
    except Exception:
        # Any missing, malformed, or unavailable authority record fails closed.
        return False


def _attach_presentation(
    view_state: MatchViewStateView,
    *,
    match_key: str,
    presentation_service: MatchViewerPresentationService,
    metadata_json: dict[str, object] | None = None,
    match: CompetitionMatch | None = None,
    include_coach_notes: bool = False,
) -> MatchViewStateView:
    return view_state.model_copy(
        update={
            "presentation_package": presentation_service.build(
                match_key=match_key,
                view_state=view_state,
                metadata_json=metadata_json,
                match=match,
                include_coach_notes=include_coach_notes,
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


def _attach_match_report_metadata(
    view_state: MatchViewStateView,
    *,
    metadata_json: dict[str, object] | None = None,
    match: CompetitionMatch | None = None,
) -> MatchViewStateView:
    meta = dict(metadata_json or {}) if isinstance(metadata_json, dict) else {}
    is_fast_match = isinstance(meta.get("fast_match"), dict)
    match_status_raw = str(meta.get("match_status") or (match.status if match is not None else "") or "").strip()
    is_completed_match = match_status_raw.lower() in {"completed", "played", "settled", "full_time", "fulltime", "ft"}
    # A quick game the owner chose to watch is a live 2D broadcast. The result
    # report is attached only after they simulate, or after full time is filed.
    if meta.get("watch_live") is True:
        is_simulated = False
        is_completed_match = False
    else:
        is_simulated = bool(meta.get("is_simulated") or view_state.is_simulated or is_fast_match)

    report = meta.get("match_report") if isinstance(meta.get("match_report"), dict) else None
    if report is None and isinstance(view_state.match_report, dict):
        report = dict(view_state.match_report)
    if report is None and isinstance(meta.get("replay_payload"), dict):
        try:
            from app.match_engine.schemas import MatchReplayPayloadView
            from app.match_engine.services.match_report import build_simulated_match_report

            replay_view = MatchReplayPayloadView.model_validate(meta["replay_payload"])
            report = build_simulated_match_report(
                replay_view,
                home_team_name=view_state.home_team.team_name,
                away_team_name=view_state.away_team.team_name,
            )
        except Exception:
            report = None
    if report is None and (is_simulated or is_completed_match):
        from app.match_engine.services.match_report import build_simulated_match_report_from_payload

        home_score = meta.get("home_score")
        away_score = meta.get("away_score")
        if (home_score is None or away_score is None) and match is not None and match.home_score is not None:
            home_score = match.home_score
            away_score = match.away_score
        if (home_score is None or away_score is None) and view_state.frames:
            home_score = view_state.frames[-1].home_score
            away_score = view_state.frames[-1].away_score
        if (home_score is None or away_score is None) and view_state.events:
            home_score = view_state.events[-1].home_score
            away_score = view_state.events[-1].away_score
        report = build_simulated_match_report_from_payload(
            match_id=view_state.match_id,
            home_team_id=view_state.home_team.team_id,
            away_team_id=view_state.away_team.team_id,
            home_team_name=view_state.home_team.team_name,
            away_team_name=view_state.away_team.team_name,
            home_score=int(home_score or 0),
            away_score=int(away_score or 0),
            events=[ev.model_dump(mode="json") for ev in view_state.events],
            narrative=meta,
            result_label=(
                str((meta.get("fast_match") or {}).get("result") or "") or None
                if isinstance(meta.get("fast_match"), dict)
                else None
            ),
        )
    if meta.get("watch_live") is True:
        report = None

    stats = (
        dict(report.get("stats") or {})
        if isinstance(report, dict) and isinstance(report.get("stats"), dict)
        else (dict(view_state.stats) if isinstance(view_state.stats, dict) else None)
    )
    resolved_status = match_status_raw or ("completed" if is_simulated else view_state.match_status)
    return view_state.model_copy(
        update={
            "stats": stats,
            "match_report": report,
            "is_simulated": is_simulated,
            "match_status": resolved_status,
        }
    )


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
    allow_synthetic_visuals = not _protected_runtime_enabled(request.app)
    if live_state is not None:
        events, _ = live_hub.get_events_since(match_key, 0)
        try:
            view_state = service.build_from_live_stream(
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
                allow_synthetic_visuals=allow_synthetic_visuals,
            )
        except ValueError:
            if _protected_runtime_enabled(request.app):
                return None
            raise
        return view_state, metadata_json
    infinite_stream = ensure_infinite_league_runtime(request.app).live_stream(match_key)
    if infinite_stream is not None:
        if _protected_runtime_enabled(request.app):
            return None
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
                allow_synthetic_visuals=True,
            ),
            metadata_json,
        )
    return None


def _fast_match_is_settled(fast_match: FastMatchSession) -> bool:
    status = fast_match.status
    return status is FastMatchSessionStatus.SETTLED or str(status) == FastMatchSessionStatus.SETTLED.value


def _fast_match_watch_view(
    *,
    fast_match: FastMatchSession,
    session: Session,
    service: MatchTimelineService,
) -> MatchViewStateView | None:
    """Return the 2D timeline for a quick game.

    A ready session stores the engine request and an empty viewer payload until
    someone opens the match. Build that film once so Watch lands on the pitch.
    """
    raw = fast_match.viewer_payload_json if isinstance(fast_match.viewer_payload_json, dict) else {}
    if raw:
        try:
            return MatchViewStateView.model_validate(raw)
        except Exception:
            logger.info("Stored quick-game viewer payload for %s is not a timeline. Rebuilding.", fast_match.match_id)
    request_raw = fast_match.simulation_request_json if isinstance(fast_match.simulation_request_json, dict) else {}
    if not request_raw:
        return None
    from app.match_engine.schemas import MatchSimulationRequest
    from app.match_engine.services.match_simulation_service import MatchSimulationService

    try:
        request = MatchSimulationRequest.model_validate(request_raw)
        replay = MatchSimulationService().build_replay_payload(request)
        view = service.build_from_replay_payload(replay)
    except Exception:
        logger.exception("Quick-game viewer timeline could not be built for %s", fast_match.match_id)
        return None
    stored = view.model_dump(mode="json")
    fast_match.viewer_payload_json = stored
    try:
        session.commit()
    except Exception:
        logger.exception("Quick-game viewer timeline could not be stored for %s", fast_match.match_id)
        session.rollback()
    return view


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

    fast_match = session.scalar(
        select(FastMatchSession).where(
            (FastMatchSession.live_match_key == match_key) | (FastMatchSession.match_id == match_key)
        )
    )
    if fast_match is not None:
        settled = _fast_match_is_settled(fast_match)
        stored_meta = dict(fast_match.metadata_json or {})
        fast_meta = {
            "match_id": fast_match.match_id,
            "live_match_key": fast_match.live_match_key,
            "entry_currency": fast_match.entry_currency,
            "fan_coin_entry_fee": str(fast_match.fan_coin_entry_fee),
            "charge_required_now": fast_match.charge_required_now,
            "result": fast_match.result,
        }
        watch_view = _fast_match_watch_view(fast_match=fast_match, session=session, service=service)
        if watch_view is not None:
            return _ResolvedMatchViewerContext(
                canonical_view=watch_view,
                metadata_json={
                    **stored_meta,
                    "is_simulated": settled,
                    "watch_live": not settled,
                    "match_status": "completed" if settled else "live",
                    "fast_match": fast_meta,
                },
                fairness_metadata=None,
                match=None,
            )

    try:
        from app.owner_console.models import OwnerMatch
        from app.services.owner_competition_lifecycle_mapping_service import (
            OwnerCompetitionLifecycleMappingService,
        )

        owner_match = session.get(OwnerMatch, match_key)
        if owner_match is not None:
            mapped_canonical = OwnerCompetitionLifecycleMappingService(session).canonical_match_for_legacy_match(
                owner_match.id
            )
            if mapped_canonical is not None:
                mapped_meta = dict(mapped_canonical.metadata_json or {})
                mapped_stored = mapped_meta.get("match_viewer")
                if isinstance(mapped_stored, dict):
                    return _ResolvedMatchViewerContext(
                        canonical_view=MatchViewStateView.model_validate(mapped_stored),
                        metadata_json=mapped_meta,
                        fairness_metadata=(
                            mapped_meta.get("fairness") if isinstance(mapped_meta.get("fairness"), dict) else None
                        ),
                        match=mapped_canonical,
                    )
            narrative = dict(owner_match.narrative_json or {})
            stored_viewer = narrative.get("match_viewer")
            if isinstance(stored_viewer, dict):
                return _ResolvedMatchViewerContext(
                    canonical_view=MatchViewStateView.model_validate(stored_viewer),
                    metadata_json={
                        **narrative,
                        "is_simulated": owner_match.status == "played" or bool(narrative.get("is_simulated")),
                        "match_status": owner_match.status,
                        "home_score": owner_match.home_goals,
                        "away_score": owner_match.away_goals,
                    },
                    fairness_metadata=None,
                    match=None,
                )
    except Exception:
        pass

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


def _resolve_server_broadcast_params(
    canonical_view: MatchViewStateView,
    metadata_json: dict[str, object],
) -> tuple[MatchMode, int]:
    """Derive server-authoritative broadcast mode and duration from competition category only.

    Viewer query overrides (mode, speed, target_duration_seconds) are ignored so every
    spectator receives the same universal broadcast timeline (Section 3.1 & 3.2).
    """
    comp_meta = metadata_json.get("competition") if isinstance(metadata_json.get("competition"), dict) else {}
    replay_payload = (
        metadata_json.get("replay_payload") if isinstance(metadata_json.get("replay_payload"), dict) else {}
    )
    summary = replay_payload.get("summary") if isinstance(replay_payload.get("summary"), dict) else {}
    category = resolve_match_broadcast_category(
        is_final=bool(metadata_json.get("is_final") or comp_meta.get("is_final") or summary.get("is_final")),
        stage=str(metadata_json.get("stage") or comp_meta.get("stage") or summary.get("stage") or ""),
        competition_type=str(
            metadata_json.get("competition_type")
            or comp_meta.get("competition_type")
            or summary.get("competition_type")
            or ""
        ),
        approved_shorter_presentation=bool(
            metadata_json.get("approved_shorter_presentation") or comp_meta.get("approved_shorter_presentation")
        ),
        metadata={
            "competition_category": getattr(canonical_view, "competition_category", None),
            **(canonical_view.broadcast_session if isinstance(canonical_view.broadcast_session, dict) else {}),
        },
    )
    min_win, max_win = BROADCAST_CATEGORY_DURATION_WINDOWS[category]
    hard_cap = BROADCAST_CATEGORY_MAX_SECONDS[category]
    server_mode = (
        MatchMode.CINEMATIC
        if category
        in {MatchBroadcastCategory.FINAL, MatchBroadcastCategory.SEMI_FINAL, MatchBroadcastCategory.MAJOR_KNOCKOUT}
        else MatchMode.STANDARD
    )
    persisted_session = (
        canonical_view.broadcast_session
        if isinstance(canonical_view.broadcast_session, dict)
        else metadata_json.get("broadcast_session") if isinstance(metadata_json.get("broadcast_session"), dict) else {}
    )
    assigned = persisted_session.get("assigned_duration_seconds")
    if isinstance(assigned, (int, float)) and assigned >= 60:
        server_duration = max(min_win, min(hard_cap, int(assigned)))
    else:
        raw_dur = int(canonical_view.duration_seconds or max_win)
        server_duration = max(min_win, min(hard_cap, raw_dur))
    return server_mode, server_duration


@router.get("/{match_key}", response_model=MatchViewStateView)
def read_match_viewer_timeline(
    match_key: str,
    request: Request,
    mode: MatchMode = Query(default=MatchMode.STANDARD),
    target_duration_seconds: int | None = Query(default=None, ge=60, le=900),
    session: Session = Depends(get_session),
    service: MatchTimelineService = Depends(get_match_timeline_service),
    scaling_service: MatchViewerScalingService = Depends(get_match_viewer_scaling_service),
    integrity_service: MatchIntegrityService = Depends(get_match_integrity_service),
    presentation_service: MatchViewerPresentationService = Depends(get_match_viewer_presentation_service),
    ad_engine: AdDecisionEngine = Depends(get_ad_decision_engine),
    current_user: User | None = Depends(get_optional_current_user),
) -> MatchViewStateView:
    del mode, target_duration_seconds
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

    server_mode, server_duration = _resolve_server_broadcast_params(
        resolved.canonical_view,
        resolved.metadata_json,
    )

    if resolved.fairness_metadata is not None:
        try:
            secured = integrity_service.build_viewer_session(
                match_id=match_key,
                view_state=scaling_service.transform(
                    resolved.canonical_view,
                    mode=server_mode,
                    target_duration_seconds=server_duration,
                ),
                fairness_metadata=resolved.fairness_metadata,
                mode=server_mode,
                canonical_view_state=resolved.canonical_view,
            )
            can_view_coach_notes = _is_owner_or_manager(current_user, resolved.match, session)
            secured = _attach_presentation(
                secured,
                match_key=match_key,
                presentation_service=presentation_service,
                metadata_json=resolved.metadata_json,
                match=resolved.match,
                include_coach_notes=can_view_coach_notes,
            )
            return _attach_match_report_metadata(
                _attach_monetization(
                    secured,
                    match_key=match_key,
                    session=session,
                    ad_engine=ad_engine,
                    metadata_json=resolved.metadata_json,
                    match=resolved.match,
                ),
                metadata_json=resolved.metadata_json,
                match=resolved.match,
            )
        except MatchIntegrityViolation as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    can_view_coach_notes = _is_owner_or_manager(current_user, resolved.match, session)
    transformed = _attach_presentation(
        scaling_service.transform(
            resolved.canonical_view,
            mode=server_mode,
            target_duration_seconds=server_duration,
        ),
        match_key=match_key,
        presentation_service=presentation_service,
        metadata_json=resolved.metadata_json,
        match=resolved.match,
        include_coach_notes=can_view_coach_notes,
    )
    return _attach_match_report_metadata(
        _attach_monetization(
            transformed,
            match_key=match_key,
            session=session,
            ad_engine=ad_engine,
            metadata_json=resolved.metadata_json,
            match=resolved.match,
        ),
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
    current_user: User | None = Depends(get_optional_current_user),
) -> MatchViewerSessionView:
    del mode
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

    server_mode, server_duration = _resolve_server_broadcast_params(
        resolved.canonical_view,
        resolved.metadata_json,
    )
    base_view = scaling_service.transform(
        resolved.canonical_view,
        mode=server_mode,
        target_duration_seconds=server_duration,
    )
    try:
        secured = integrity_service.build_viewer_session(
            match_id=match_key,
            view_state=base_view,
            fairness_metadata=resolved.fairness_metadata,
            mode=server_mode,
            continuation_token=token,
            canonical_view_state=resolved.canonical_view,
        )
        can_view_coach_notes = _is_owner_or_manager(current_user, resolved.match, session)
        secured = _attach_presentation(
            secured,
            match_key=match_key,
            presentation_service=presentation_service,
            metadata_json=resolved.metadata_json,
            match=resolved.match,
            include_coach_notes=can_view_coach_notes,
        )
        return MatchViewerSessionView.model_validate(
            _attach_match_report_metadata(
                _attach_monetization(
                    secured,
                    match_key=match_key,
                    session=session,
                    ad_engine=ad_engine,
                    metadata_json=resolved.metadata_json,
                    match=resolved.match,
                ),
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
