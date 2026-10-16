from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin, get_session
from app.models.user import User
from app.value_engine.router import _build_daily_close_view, _build_snapshot_view
from app.value_engine.schemas import (
    AdminValueInspectionView,
    ValueAdminAuditResponse,
    ValueAdminAuditView,
    ValueCandidateResponse,
    ValueHistoryResponse,
    ValueRecomputeCandidateView,
    ValueRecomputeRequest,
    ValueRunHistoryResponse,
    ValueRunRecordView,
    ValueSnapshotBatchResponse,
    ValueSnapshotView,
)

from .schemas import (
    LiquidityBandConfigPayload,
    PlayerCardMarketIntegrityPayload,
    SupplyTierConfigPayload,
    SuspicionThresholdsPayload,
    ValueControlsPayload,
)
from .service import ConfigAdminService

router = APIRouter(prefix="/admin/config", tags=["admin"])


def get_config_admin_service() -> ConfigAdminService:
    return ConfigAdminService()


def _candidate_view(candidate) -> ValueRecomputeCandidateView:
    return ValueRecomputeCandidateView(
        player_id=candidate.player_id,
        player_name=candidate.player_name,
        status=candidate.status,
        requested_tempo=candidate.requested_tempo,
        priority=candidate.priority,
        trigger_count=candidate.trigger_count,
        signal_delta_score=candidate.signal_delta_score,
        last_event_at=candidate.last_event_at,
        last_requested_at=candidate.last_requested_at,
        claimed_at=candidate.claimed_at,
        processed_at=candidate.processed_at,
        next_eligible_at=candidate.next_eligible_at,
        last_error=candidate.last_error,
        reason_codes=tuple(candidate.reason_codes_json or ()),
        metadata=candidate.metadata_json or {},
    )


@router.get("/supply-tiers", response_model=SupplyTierConfigPayload)
def get_supply_tiers(
    request: Request,
    _: User = Depends(get_current_admin),
) -> SupplyTierConfigPayload:
    return SupplyTierConfigPayload.model_validate(request.app.state.settings.supply_tiers)


@router.put("/supply-tiers", response_model=SupplyTierConfigPayload)
def update_supply_tiers(
    payload: SupplyTierConfigPayload,
    request: Request,
    session: Session = Depends(get_session),
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> SupplyTierConfigPayload:
    try:
        settings = service.update_supply_tiers(request.app, session, payload.to_domain())
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SupplyTierConfigPayload.model_validate(settings.supply_tiers)


@router.get("/liquidity-bands", response_model=LiquidityBandConfigPayload)
def get_liquidity_bands(
    request: Request,
    _: User = Depends(get_current_admin),
) -> LiquidityBandConfigPayload:
    return LiquidityBandConfigPayload.model_validate(request.app.state.settings.liquidity_bands)


@router.put("/liquidity-bands", response_model=LiquidityBandConfigPayload)
def update_liquidity_bands(
    payload: LiquidityBandConfigPayload,
    request: Request,
    session: Session = Depends(get_session),
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> LiquidityBandConfigPayload:
    try:
        settings = service.update_liquidity_bands(request.app, session, payload.to_domain())
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LiquidityBandConfigPayload.model_validate(settings.liquidity_bands)


@router.get("/suspicion-thresholds", response_model=SuspicionThresholdsPayload)
def get_suspicion_thresholds(
    request: Request,
    _: User = Depends(get_current_admin),
) -> SuspicionThresholdsPayload:
    return SuspicionThresholdsPayload.model_validate(request.app.state.settings.suspicion_thresholds)


@router.put("/suspicion-thresholds", response_model=SuspicionThresholdsPayload)
def update_suspicion_thresholds(
    payload: SuspicionThresholdsPayload,
    request: Request,
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> SuspicionThresholdsPayload:
    try:
        settings = service.update_suspicion_thresholds(request.app, payload.to_domain())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SuspicionThresholdsPayload.model_validate(settings.suspicion_thresholds)


@router.get("/player-card-market-integrity", response_model=PlayerCardMarketIntegrityPayload)
def get_player_card_market_integrity(
    request: Request,
    _: User = Depends(get_current_admin),
) -> PlayerCardMarketIntegrityPayload:
    return PlayerCardMarketIntegrityPayload.model_validate(request.app.state.settings.player_card_market_integrity)


@router.put("/player-card-market-integrity", response_model=PlayerCardMarketIntegrityPayload)
def update_player_card_market_integrity(
    payload: PlayerCardMarketIntegrityPayload,
    request: Request,
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> PlayerCardMarketIntegrityPayload:
    try:
        settings = service.update_player_card_market_integrity(request.app, payload.to_domain())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlayerCardMarketIntegrityPayload.model_validate(settings.player_card_market_integrity)


@router.get("/value-controls", response_model=ValueControlsPayload)
def get_value_controls(
    request: Request,
    _: User = Depends(get_current_admin),
) -> ValueControlsPayload:
    return ValueControlsPayload.from_domain(request.app.state.settings.value_engine_weighting)


@router.put("/value-controls", response_model=ValueControlsPayload)
def update_value_controls(
    payload: ValueControlsPayload,
    request: Request,
    session: Session = Depends(get_session),
    service: ConfigAdminService = Depends(get_config_admin_service),
    _: User = Depends(get_current_admin),
) -> ValueControlsPayload:
    audit_session = session if hasattr(session, "add") else None
    try:
        updated_config = payload.merge_into(request.app.state.settings.value_engine_weighting)
        settings = service.update_value_controls(request.app, updated_config)
        if audit_session is None:
            with request.app.state.session_factory() as managed_session:
                request.app.state.value_engine_bridge.record_admin_action(
                    managed_session,
                    action_type="value_controls_updated",
                    actor_user_id=_.id,
                    actor_role=str(_.role.value if hasattr(_.role, "value") else _.role),
                    payload=payload.model_dump(exclude_none=True),
                )
                managed_session.commit()
        else:
            request.app.state.value_engine_bridge.record_admin_action(
                audit_session,
                action_type="value_controls_updated",
                actor_user_id=_.id,
                actor_role=str(_.role.value if hasattr(_.role, "value") else _.role),
                payload=payload.model_dump(exclude_none=True),
            )
            audit_session.commit()
    except ValueError as exc:
        if audit_session is not None:
            audit_session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ValueControlsPayload.from_domain(settings.value_engine_weighting)


@router.get("/value-controls/run-history", response_model=ValueRunHistoryResponse)
def get_value_run_history(
    request: Request,
    session: Session = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> ValueRunHistoryResponse:
    bridge = request.app.state.value_engine_bridge
    runs = [ValueRunRecordView.model_validate(run) for run in bridge.list_run_history(session, limit=limit)]
    return ValueRunHistoryResponse(runs=runs)


@router.get("/value-controls/integrity/candidates", response_model=ValueCandidateResponse)
def get_value_recompute_candidates(
    request: Request,
    session: Session = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_admin),
) -> ValueCandidateResponse:
    bridge = request.app.state.value_engine_bridge
    candidates = [_candidate_view(item) for item in bridge.list_candidates(session, limit=limit)]
    return ValueCandidateResponse(candidates=candidates)


@router.get("/value-controls/audits", response_model=ValueAdminAuditResponse)
def get_value_admin_audits(
    request: Request,
    session: Session = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=500),
    _: User = Depends(get_current_admin),
) -> ValueAdminAuditResponse:
    bridge = request.app.state.value_engine_bridge
    audits = [ValueAdminAuditView.model_validate(record) for record in bridge.list_admin_audits(session, limit=limit)]
    return ValueAdminAuditResponse(audits=audits)


@router.get("/value-controls/players/{player_id}", response_model=AdminValueInspectionView)
def inspect_player_value(
    player_id: str,
    request: Request,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_admin),
) -> AdminValueInspectionView:
    bridge = request.app.state.value_engine_bridge
    inspection = bridge.inspect_player(session, player_id)
    latest_snapshot = inspection["latest_snapshot"]
    candidate = inspection["candidate"]
    history = inspection["history"]
    daily_closes = inspection["daily_closes"]
    return AdminValueInspectionView(
        latest_snapshot=_build_snapshot_view(latest_snapshot) if latest_snapshot is not None else None,
        candidate=_candidate_view(candidate) if candidate is not None else None,
        history=[_build_snapshot_view(snapshot) for snapshot in history],
        daily_closes=[_build_daily_close_view(close) for close in daily_closes],
    )


@router.get("/value-controls/preview/{player_id}", response_model=ValueSnapshotView)
def preview_player_value(
    player_id: str,
    request: Request,
    session: Session = Depends(get_session),
    as_of: datetime | None = None,
    lookback_days: int | None = Query(default=None, ge=1),
    _: User = Depends(get_current_admin),
) -> ValueSnapshotView:
    bridge = request.app.state.value_engine_bridge
    snapshot = bridge.preview_player(
        session,
        player_id=player_id,
        as_of=as_of,
        lookback_days=lookback_days,
    )
    return _build_snapshot_view(snapshot)


@router.post("/value-controls/recompute", response_model=ValueSnapshotBatchResponse)
def trigger_value_recompute(
    payload: ValueRecomputeRequest,
    request: Request,
    session: Session = Depends(get_session),
    admin_user: User = Depends(get_current_admin),
) -> ValueSnapshotBatchResponse:
    bridge = request.app.state.value_engine_bridge
    if payload.player_ids:
        snapshots = bridge.run(
            as_of=payload.as_of,
            lookback_days=payload.lookback_days,
            player_ids=payload.player_ids,
            snapshot_type=payload.snapshot_type,
            run_type=f"admin_{payload.tempo}_recompute",
            triggered_by="admin",
            actor_user_id=admin_user.id,
            notes={"tempo": payload.tempo, "explicit_players": True},
        )
    elif payload.tempo == "fast":
        snapshots = bridge.run_fast_reconciliation(
            as_of=payload.as_of,
            lookback_days=payload.lookback_days,
            limit=payload.limit or 25,
            actor_user_id=admin_user.id,
        )
    elif payload.tempo == "daily":
        snapshots = bridge.run_daily_rebase(
            as_of=payload.as_of,
            lookback_days=payload.lookback_days,
            limit=payload.limit,
            actor_user_id=admin_user.id,
        )
    else:
        snapshots = bridge.run_hourly_reconciliation(
            as_of=payload.as_of,
            lookback_days=payload.lookback_days,
            limit=payload.limit or 100,
            actor_user_id=admin_user.id,
        )
    bridge.record_admin_action(
        session,
        action_type="value_recompute_triggered",
        actor_user_id=admin_user.id,
        actor_role=str(admin_user.role.value if hasattr(admin_user.role, "value") else admin_user.role),
        payload=payload.model_dump(exclude_none=True),
    )
    session.commit()
    return ValueSnapshotBatchResponse(snapshots=[_build_snapshot_view(snapshot) for snapshot in snapshots])
