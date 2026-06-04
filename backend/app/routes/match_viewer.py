from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.infinite_league.service import ensure_infinite_league_runtime
from app.live_matches.generated_stream_policy import generated_live_match_streams_enabled
from app.live_matches.service import ensure_live_match_hub
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.economy_config import GiftCatalogItem
from app.replay_archive.service import ensure_replay_archive
from app.schemas.match_viewer import (
    MatchMode,
    MatchViewerAdStateView,
    MatchViewerAvailabilityStatus,
    MatchViewerCommentaryLineView,
    MatchViewerCommentaryStateView,
    MatchViewerEngagementView,
    MatchViewerEventSourceStateView,
    MatchViewerEventType,
    MatchViewerGiftCatalogItemView,
    MatchViewerGiftCatalogStateView,
    MatchViewerGiftContextView,
    MatchViewerGiftSessionStateView,
    MatchViewerGiftTargetView,
    MatchViewerReactionStateView,
    MatchViewerSessionView,
    MatchViewStateView,
)
from app.services.ads.engine import AdDecisionEngine
from app.services.match_viewer_presentation_service import MatchViewerPresentationService
from app.services.match_viewer_scaling_service import MatchViewerScalingService
from app.services.match_timeline_service import MatchTimelineService

router = APIRouter(prefix="/match-viewer", tags=["match-viewer"])

_CONTROL_EVENT_TYPES = {
    MatchViewerEventType.KICKOFF,
    MatchViewerEventType.HALFTIME,
    MatchViewerEventType.FULLTIME,
}
_CONTRACT_LABEL_BLOCKLIST = ("premium", "monetization", "3d", "production")


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


def _attach_engagement(
    view_state: MatchViewStateView,
    *,
    match_key: str,
    session: Session,
    ad_engine: AdDecisionEngine,
    metadata_json: dict[str, object] | None = None,
    match: CompetitionMatch | None = None,
) -> MatchViewStateView:
    engagement = MatchViewerEngagementView(
        ads=_match_ad_state(
            view_state,
            match_key=match_key,
            ad_engine=ad_engine,
            metadata_json=metadata_json,
        ),
        gifting=_match_gift_context(
            session=session,
            match=match,
            metadata_json=metadata_json if isinstance(metadata_json, dict) else None,
        ),
        event_source=_event_source_state(view_state),
        commentary=_commentary_state(view_state),
        reactions=_reaction_state(view_state),
    )
    return view_state.model_copy(update={"engagement": engagement})


def _match_ad_state(
    view_state: MatchViewStateView,
    *,
    match_key: str,
    ad_engine: AdDecisionEngine,
    metadata_json: dict[str, object] | None = None,
) -> MatchViewerAdStateView:
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
    ad_state = ad_engine.build_viewer_monetization(
        match_id=match_key,
        view_state=view_state,
        ad_profile=ad_profile if isinstance(ad_profile, dict) else None,
        match_context=match_context,
    )
    return MatchViewerAdStateView(
        status=(
            MatchViewerAvailabilityStatus.READY
            if ad_state.ads_enabled and ad_state.placements
            else MatchViewerAvailabilityStatus.EMPTY
        ),
        ads_enabled=bool(ad_state.ads_enabled and ad_state.placements),
        placements=ad_state.placements,
        metadata=_neutral_contract_metadata(ad_state.metadata),
        status_detail=None if ad_state.placements else "No ad placements are available for this match view.",
    )


def _match_gift_context(
    *,
    session: Session,
    match: CompetitionMatch | None,
    metadata_json: dict[str, object] | None,
) -> MatchViewerGiftContextView:
    target = _match_gift_target(session=session, match=match, metadata_json=metadata_json)
    catalog = _match_gift_catalog_state(session=session, metadata_json=metadata_json)
    session_state = _match_gift_session_state(
        target=target,
        catalog=catalog,
        metadata_json=metadata_json,
    )
    if target is None:
        return MatchViewerGiftContextView(
            status=MatchViewerAvailabilityStatus.BLOCKED,
            target=None,
            catalog=catalog,
            session=session_state,
            status_detail="Gift target metadata is not attached to this match.",
        )
    if session_state.status is MatchViewerAvailabilityStatus.READY:
        status_value = MatchViewerAvailabilityStatus.READY
        detail = None
    elif session_state.status is MatchViewerAvailabilityStatus.DEGRADED:
        status_value = MatchViewerAvailabilityStatus.DEGRADED
        detail = session_state.status_detail
    elif session_state.status is MatchViewerAvailabilityStatus.EMPTY:
        status_value = MatchViewerAvailabilityStatus.EMPTY
        detail = session_state.status_detail
    else:
        status_value = MatchViewerAvailabilityStatus.BLOCKED
        detail = session_state.blocked_reason
    return MatchViewerGiftContextView(
        status=status_value,
        target=target,
        catalog=catalog,
        session=session_state,
        status_detail=detail,
    )


def _match_gift_target(
    *,
    session: Session,
    match: CompetitionMatch | None,
    metadata_json: dict[str, object] | None,
) -> MatchViewerGiftTargetView | None:
    if match is None:
        return None
    competition = session.get(UserCompetition, match.competition_id)
    if competition is None:
        return None
    recipient_user_id = competition.host_user_id.strip()
    if not recipient_user_id:
        return None
    return MatchViewerGiftTargetView(
        recipient_user_id=recipient_user_id,
        recipient_label=_match_gift_recipient_label(
            competition=competition,
            metadata_json=metadata_json,
        ),
        source_scope=_match_gift_source_scope(
            competition=competition,
            metadata_json=metadata_json,
        ),
    )


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


def _match_gift_catalog_state(
    *,
    session: Session,
    metadata_json: dict[str, object] | None,
) -> MatchViewerGiftCatalogStateView:
    metadata_catalog = _metadata_gift_catalog(metadata_json)
    if metadata_catalog is not None:
        items, invalid_count = metadata_catalog
        if items:
            status_value = (
                MatchViewerAvailabilityStatus.DEGRADED
                if invalid_count
                else MatchViewerAvailabilityStatus.READY
            )
            return MatchViewerGiftCatalogStateView(
                status=status_value,
                source="match_metadata",
                items=items,
                status_detail=(
                    f"{invalid_count} gift catalog item(s) were ignored because they were incomplete."
                    if invalid_count
                    else None
                ),
            )
        return MatchViewerGiftCatalogStateView(
            status=MatchViewerAvailabilityStatus.EMPTY,
            source="match_metadata",
            items=[],
            status_detail="Match metadata contains an empty gift catalog.",
        )

    try:
        rows = list(
            session.scalars(
                select(GiftCatalogItem)
                .where(GiftCatalogItem.active.is_(True))
                .order_by(GiftCatalogItem.tier.asc(), GiftCatalogItem.fancoin_price.asc(), GiftCatalogItem.key.asc())
                .limit(24)
            ).all()
        )
    except SQLAlchemyError:
        return MatchViewerGiftCatalogStateView(
            status=MatchViewerAvailabilityStatus.BLOCKED,
            source="gift_engine_catalog",
            items=[],
            blocked_reason="gift_catalog_unavailable",
            status_detail="Gift catalog rows are not available to the match viewer route.",
        )

    items = [
        MatchViewerGiftCatalogItemView(
            key=row.key,
            display_name=row.display_name,
            tier=row.tier,
            fancoin_price=float(row.fancoin_price or 0.0),
            animation_key=row.animation_key,
            sound_key=row.sound_key,
            description=row.description,
        )
        for row in rows
    ]
    if not items:
        return MatchViewerGiftCatalogStateView(
            status=MatchViewerAvailabilityStatus.EMPTY,
            source="gift_engine_catalog",
            items=[],
            status_detail="No active gift catalog items are available.",
        )
    return MatchViewerGiftCatalogStateView(
        status=MatchViewerAvailabilityStatus.READY,
        source="gift_engine_catalog",
        items=items,
    )


def _match_gift_session_state(
    *,
    target: MatchViewerGiftTargetView | None,
    catalog: MatchViewerGiftCatalogStateView,
    metadata_json: dict[str, object] | None,
) -> MatchViewerGiftSessionStateView:
    if target is None:
        return MatchViewerGiftSessionStateView(
            status=MatchViewerAvailabilityStatus.BLOCKED,
            active=False,
            can_send=False,
            blocked_reason="gift_target_missing",
            status_detail="Gift target metadata is required before a gift session can open.",
        )
    if catalog.status is MatchViewerAvailabilityStatus.BLOCKED:
        return MatchViewerGiftSessionStateView(
            status=MatchViewerAvailabilityStatus.BLOCKED,
            active=False,
            can_send=False,
            blocked_reason=catalog.blocked_reason or "gift_catalog_unavailable",
            status_detail=catalog.status_detail,
        )
    if catalog.status is MatchViewerAvailabilityStatus.EMPTY:
        return MatchViewerGiftSessionStateView(
            status=MatchViewerAvailabilityStatus.EMPTY,
            active=False,
            can_send=False,
            status_detail="Gift session is empty because no active catalog items are available.",
        )

    raw_session = _metadata_gift_session(metadata_json)
    if raw_session is None:
        return MatchViewerGiftSessionStateView(
            status=MatchViewerAvailabilityStatus.DEGRADED,
            active=False,
            can_send=True,
            send_endpoint="/api/gift-engine/send",
            status_detail="Dedicated match gift session state is not attached; use the gift engine send endpoint with the provided target.",
        )

    raw_status = _string(raw_session.get("status"))
    status_value = _availability_status(raw_status) or MatchViewerAvailabilityStatus.READY
    active = bool(raw_session.get("active", status_value is MatchViewerAvailabilityStatus.READY))
    can_send = bool(raw_session.get("can_send", active and status_value is MatchViewerAvailabilityStatus.READY))
    return MatchViewerGiftSessionStateView(
        status=status_value,
        active=active,
        can_send=can_send,
        session_id=_string(raw_session.get("session_id") or raw_session.get("id")),
        send_endpoint=_string(raw_session.get("send_endpoint")) or "/api/gift-engine/send",
        blocked_reason=_string(raw_session.get("blocked_reason")),
        status_detail=_string(raw_session.get("status_detail") or raw_session.get("detail")),
    )


def _metadata_gift_catalog(
    metadata_json: dict[str, object] | None,
) -> tuple[list[MatchViewerGiftCatalogItemView], int] | None:
    if not isinstance(metadata_json, dict):
        return None
    raw_catalog = metadata_json.get("gift_catalog")
    if raw_catalog is None:
        engagement = metadata_json.get("engagement")
        if isinstance(engagement, dict):
            raw_catalog = engagement.get("gift_catalog")
    if raw_catalog is None:
        return None
    if not isinstance(raw_catalog, list):
        return [], 1

    items: list[MatchViewerGiftCatalogItemView] = []
    invalid_count = 0
    for raw_item in raw_catalog:
        if not isinstance(raw_item, dict):
            invalid_count += 1
            continue
        key = _string(raw_item.get("key") or raw_item.get("gift_key"))
        display_name = _string(raw_item.get("display_name") or raw_item.get("label") or raw_item.get("name"))
        if key is None or display_name is None:
            invalid_count += 1
            continue
        try:
            price = float(raw_item.get("fancoin_price") or raw_item.get("price") or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        items.append(
            MatchViewerGiftCatalogItemView(
                key=key,
                display_name=display_name,
                tier=_string(raw_item.get("tier")),
                fancoin_price=max(0.0, price),
                animation_key=_string(raw_item.get("animation_key")),
                sound_key=_string(raw_item.get("sound_key")),
                description=_string(raw_item.get("description")),
            )
        )
    return items, invalid_count


def _metadata_gift_session(metadata_json: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(metadata_json, dict):
        return None
    raw_session = metadata_json.get("gift_session")
    if isinstance(raw_session, dict):
        return raw_session
    engagement = metadata_json.get("engagement")
    if isinstance(engagement, dict) and isinstance(engagement.get("gift_session"), dict):
        return engagement["gift_session"]
    return None


def _event_source_state(view_state: MatchViewStateView) -> MatchViewerEventSourceStateView:
    event_count = len(view_state.events)
    presentation_only_count = sum(1 for event in view_state.events if "presentation_only" in event.flags)
    incident_count = sum(
        1
        for event in view_state.events
        if event.event_type not in _CONTROL_EVENT_TYPES and "presentation_only" not in event.flags
    )
    if event_count == 0:
        return MatchViewerEventSourceStateView(
            status=MatchViewerAvailabilityStatus.BLOCKED,
            source=view_state.source,
            backend_authored=True,
            event_count=0,
            incident_event_count=0,
            presentation_only_event_count=0,
            blocked_reason="event_source_missing",
        )
    if presentation_only_count:
        return MatchViewerEventSourceStateView(
            status=MatchViewerAvailabilityStatus.DEGRADED,
            source=view_state.source,
            backend_authored=False,
            event_count=event_count,
            incident_event_count=incident_count,
            presentation_only_event_count=presentation_only_count,
            degraded_reason="presentation_only_events_present",
        )
    if incident_count == 0:
        return MatchViewerEventSourceStateView(
            status=MatchViewerAvailabilityStatus.DEGRADED,
            source=view_state.source,
            backend_authored=True,
            event_count=event_count,
            incident_event_count=0,
            presentation_only_event_count=0,
            degraded_reason="incident_event_source_missing",
        )
    return MatchViewerEventSourceStateView(
        status=MatchViewerAvailabilityStatus.READY,
        source=view_state.source,
        backend_authored=True,
        event_count=event_count,
        incident_event_count=incident_count,
        presentation_only_event_count=0,
    )


def _commentary_state(view_state: MatchViewStateView) -> MatchViewerCommentaryStateView:
    event_source = _event_source_state(view_state)
    lines = [
        MatchViewerCommentaryLineView(
            event_id=event.event_id,
            clock_label=event.clock_label,
            event_type=event.event_type,
            text=event.commentary.strip(),
        )
        for event in view_state.events
        if event.event_type not in _CONTROL_EVENT_TYPES
        and "presentation_only" not in event.flags
        and event.commentary.strip()
    ]
    if event_source.status is MatchViewerAvailabilityStatus.BLOCKED:
        return MatchViewerCommentaryStateView(
            status=MatchViewerAvailabilityStatus.BLOCKED,
            lines=[],
            event_count=0,
            blocked_reason=event_source.blocked_reason,
        )
    if not lines:
        return MatchViewerCommentaryStateView(
            status=MatchViewerAvailabilityStatus.EMPTY,
            lines=[],
            event_count=event_source.incident_event_count,
            status_detail="No backend-authored incident commentary lines are available.",
            degraded_reason=event_source.degraded_reason,
        )
    return MatchViewerCommentaryStateView(
        status=(
            MatchViewerAvailabilityStatus.DEGRADED
            if event_source.status is MatchViewerAvailabilityStatus.DEGRADED
            else MatchViewerAvailabilityStatus.READY
        ),
        lines=lines[:24],
        event_count=event_source.incident_event_count,
        degraded_reason=event_source.degraded_reason,
    )


def _reaction_state(view_state: MatchViewStateView) -> MatchViewerReactionStateView:
    package = view_state.presentation_package
    cards = list(package.reactions if package is not None else [])
    if not cards:
        return MatchViewerReactionStateView(
            status=MatchViewerAvailabilityStatus.EMPTY,
            cards=[],
            status_detail="No backend-authored reaction cards are attached to this match view.",
        )
    return MatchViewerReactionStateView(
        status=MatchViewerAvailabilityStatus.READY,
        cards=cards[:8],
    )


def _neutral_contract_metadata(metadata: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(metadata, dict):
        return {}
    output: dict[str, object] = {}
    for key, value in metadata.items():
        normalized = key.lower()
        if any(term in normalized for term in _CONTRACT_LABEL_BLOCKLIST):
            continue
        if isinstance(value, str) and any(term in value.lower() for term in _CONTRACT_LABEL_BLOCKLIST):
            continue
        output[key] = value
    return output


def _availability_status(value: str | None) -> MatchViewerAvailabilityStatus | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    for status_value in MatchViewerAvailabilityStatus:
        if normalized == status_value.value:
            return status_value
    return None


def _string(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _strip_legacy_viewer_contract(payload: dict[str, object]) -> dict[str, object]:
    sanitized = dict(payload)
    for key in tuple(sanitized):
        normalized = key.lower()
        if any(term in normalized for term in _CONTRACT_LABEL_BLOCKLIST):
            sanitized.pop(key, None)
    return sanitized


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
    infinite_stream = (
        ensure_infinite_league_runtime(request.app).live_stream(match_key)
        if generated_live_match_streams_enabled()
        else None
    )
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
                canonical_view=MatchViewStateView.model_validate(_strip_legacy_viewer_contract(stored)),
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
            return _attach_engagement(
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
    return _attach_engagement(
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
            _attach_engagement(
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
