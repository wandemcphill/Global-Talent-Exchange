from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.value_engine.schemas import (
    ValueDailyCloseResponse,
    ValueDailyCloseView,
    ValueHistoryResponse,
    ValueSnapshotBatchResponse,
    ValueSnapshotRebuildRequest,
    ValueSnapshotView,
    ValueTrendSummaryView,
)
from backend.app.value_engine.service import ValueSnapshotQueryService

router = APIRouter(prefix="/value-engine", tags=["value-engine"])

_INTERNAL_REASON_MARKERS = ("wash", "circular", "shadow", "suppression", "same_cluster", "suspicious")


def _safe_movement_tags(reason_codes: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not reason_codes:
        return ()
    return tuple(
        code for code in reason_codes if code and not any(marker in code for marker in _INTERNAL_REASON_MARKERS)
    )


def _build_breakdown_payload(snapshot: Any) -> dict:
    breakdown_json = getattr(snapshot, "breakdown_json", None) or {}
    if not breakdown_json and getattr(snapshot, "breakdown", None) is not None:
        breakdown_json = asdict(snapshot.breakdown)
    football_truth_value_credits = breakdown_json.get(
        "football_truth_value_credits",
        snapshot.football_truth_value_credits or snapshot.target_credits,
    )
    market_signal_value_credits = breakdown_json.get(
        "market_signal_value_credits",
        snapshot.market_signal_value_credits or snapshot.target_credits,
    )
    return {
        "baseline_credits": breakdown_json.get("baseline_credits", football_truth_value_credits),
        "football_truth_value_credits": football_truth_value_credits,
        "market_signal_value_credits": market_signal_value_credits,
        "published_card_value_credits": breakdown_json.get("published_card_value_credits", snapshot.target_credits),
        "blended_target_credits": breakdown_json.get("blended_target_credits", snapshot.target_credits),
        "band_limited_target_credits": breakdown_json.get("band_limited_target_credits", snapshot.target_credits),
        "liquidity_weight": breakdown_json.get("liquidity_weight", 0.0),
        "snapshot_market_price_credits": breakdown_json.get("snapshot_market_price_credits"),
        "quoted_market_price_credits": breakdown_json.get("quoted_market_price_credits"),
        "trusted_trade_price_credits": breakdown_json.get("trusted_trade_price_credits"),
        "price_band_floor_credits": breakdown_json.get("price_band_floor_credits", football_truth_value_credits),
        "price_band_ceiling_credits": breakdown_json.get("price_band_ceiling_credits", football_truth_value_credits),
        "anti_manipulation_guard_multiplier": breakdown_json.get("anti_manipulation_guard_multiplier", 1.0),
        "anchor_adjustment_pct": breakdown_json.get("anchor_adjustment_pct", 0.0),
        "performance_adjustment_pct": breakdown_json.get("performance_adjustment_pct", 0.0),
        "transfer_adjustment_pct": breakdown_json.get("transfer_adjustment_pct", 0.0),
        "award_adjustment_pct": breakdown_json.get("award_adjustment_pct", 0.0),
        "demand_adjustment_pct": breakdown_json.get("demand_adjustment_pct", 0.0),
        "market_price_adjustment_pct": breakdown_json.get("market_price_adjustment_pct", 0.0),
        "market_signal_adjustment_pct": breakdown_json.get("market_signal_adjustment_pct", 0.0),
        "truth_uncapped_adjustment_pct": breakdown_json.get("truth_uncapped_adjustment_pct", 0.0),
        "truth_capped_adjustment_pct": breakdown_json.get("truth_capped_adjustment_pct", 0.0),
        "uncapped_adjustment_pct": breakdown_json.get("uncapped_adjustment_pct", 0.0),
        "capped_adjustment_pct": breakdown_json.get("capped_adjustment_pct", 0.0),
        "trade_trust_score": breakdown_json.get("trade_trust_score", 0.0),
        "trusted_trade_count": breakdown_json.get("trusted_trade_count", 0),
        "suspicious_trade_count": breakdown_json.get("suspicious_trade_count", 0),
        "wash_trade_count": breakdown_json.get("wash_trade_count", 0),
        "circular_trade_count": breakdown_json.get("circular_trade_count", 0),
        "shadow_ignored_trade_count": breakdown_json.get("shadow_ignored_trade_count", 0),
        "unique_trade_participants": breakdown_json.get("unique_trade_participants", 0),
        "holder_count": breakdown_json.get("holder_count"),
        "top_holder_share_pct": breakdown_json.get("top_holder_share_pct"),
        "top_3_holder_share_pct": breakdown_json.get("top_3_holder_share_pct"),
        "holder_concentration_penalty_pct": breakdown_json.get("holder_concentration_penalty_pct", 0.0),
        "thin_market": breakdown_json.get("thin_market", False),
        "scouting_signal_value_credits": breakdown_json.get("scouting_signal_value_credits"),
        "egame_signal_value_credits": breakdown_json.get("egame_signal_value_credits"),
        "reference_market_value_eur": breakdown_json.get("reference_market_value_eur"),
        "seeded_reference_market_value_eur": breakdown_json.get("seeded_reference_market_value_eur"),
        "reference_value_source": breakdown_json.get("reference_value_source"),
        "reference_confidence_tier": breakdown_json.get("reference_confidence_tier"),
        "reference_confidence_score": breakdown_json.get("reference_confidence_score"),
        "reference_staleness_days": breakdown_json.get("reference_staleness_days"),
        "position_family": breakdown_json.get("position_family"),
        "position_subrole": breakdown_json.get("position_subrole"),
        "player_class": breakdown_json.get("player_class"),
        "age_curve_multiplier": breakdown_json.get("age_curve_multiplier"),
        "competition_quality_multiplier": breakdown_json.get("competition_quality_multiplier"),
        "club_quality_multiplier": breakdown_json.get("club_quality_multiplier"),
        "visibility_multiplier": breakdown_json.get("visibility_multiplier"),
        "injury_adjustment_pct": breakdown_json.get("injury_adjustment_pct"),
        "scouting_adjustment_pct": breakdown_json.get("scouting_adjustment_pct"),
        "egame_adjustment_pct": breakdown_json.get("egame_adjustment_pct"),
        "momentum_7d_pct": breakdown_json.get("momentum_7d_pct", snapshot.trend_7d_pct),
        "momentum_30d_pct": breakdown_json.get("momentum_30d_pct", snapshot.trend_30d_pct),
        "momentum_adjustment_pct": breakdown_json.get("momentum_adjustment_pct"),
        "trend_confidence": breakdown_json.get("trend_confidence", snapshot.trend_confidence),
        "confidence_score": breakdown_json.get("confidence_score", snapshot.confidence_score),
        "market_integrity_score": breakdown_json.get("market_integrity_score", snapshot.market_integrity_score),
        "signal_trust_score": breakdown_json.get("signal_trust_score", snapshot.signal_trust_score),
        "participant_diversity_score": breakdown_json.get("participant_diversity_score"),
        "price_discovery_confidence": breakdown_json.get("price_discovery_confidence"),
        "low_liquidity_penalty_pct": breakdown_json.get("low_liquidity_penalty_pct"),
        "suspicious_signal_suppression_multiplier": breakdown_json.get("suspicious_signal_suppression_multiplier"),
        "weight_profile_code": breakdown_json.get("weight_profile_code"),
    }


def _build_global_scouting_index_payload(snapshot: Any) -> dict:
    breakdown_json = getattr(snapshot, "breakdown_json", None) or {}
    if not breakdown_json and getattr(snapshot, "breakdown", None) is not None:
        breakdown_json = asdict(snapshot.breakdown)
    gsi_breakdown_json = breakdown_json.get("global_scouting_index_breakdown") or {}
    if not gsi_breakdown_json and getattr(snapshot, "global_scouting_index_breakdown", None) is not None:
        gsi_breakdown_json = asdict(snapshot.global_scouting_index_breakdown)
    previous_score = breakdown_json.get(
        "previous_global_scouting_index",
        gsi_breakdown_json.get("previous_score", 50.0),
    )
    target_score = breakdown_json.get(
        "global_scouting_index",
        gsi_breakdown_json.get("target_score", previous_score),
    )
    return {
        "previous_global_scouting_index": previous_score,
        "global_scouting_index": target_score,
        "global_scouting_index_movement_pct": breakdown_json.get(
            "global_scouting_index_movement_pct",
            gsi_breakdown_json.get("capped_adjustment_pct", 0.0),
        ),
        "global_scouting_index_breakdown": {
            "neutral_score": gsi_breakdown_json.get("neutral_score", 50.0),
            "previous_score": previous_score,
            "target_score": target_score,
            "weighted_signal_volume": gsi_breakdown_json.get("weighted_signal_volume", 0.0),
            "eligible_watchlist_adds": gsi_breakdown_json.get("eligible_watchlist_adds", 0),
            "eligible_shortlist_adds": gsi_breakdown_json.get("eligible_shortlist_adds", 0),
            "eligible_transfer_room_adds": gsi_breakdown_json.get("eligible_transfer_room_adds", 0),
            "eligible_scouting_activity": gsi_breakdown_json.get("eligible_scouting_activity", 0),
            "anchor_adjustment_pct": gsi_breakdown_json.get("anchor_adjustment_pct", 0.0),
            "scouting_signal_adjustment_pct": gsi_breakdown_json.get("scouting_signal_adjustment_pct", 0.0),
            "uncapped_adjustment_pct": gsi_breakdown_json.get("uncapped_adjustment_pct", 0.0),
            "capped_adjustment_pct": gsi_breakdown_json.get("capped_adjustment_pct", 0.0),
        },
    }


def _build_snapshot_view(snapshot: Any) -> ValueSnapshotView:
    scouting_payload = _build_global_scouting_index_payload(snapshot)
    reason_codes = tuple(getattr(snapshot, "reason_codes_json", None) or getattr(snapshot, "reason_codes", ()))
    return ValueSnapshotView(
        player_id=snapshot.player_id,
        player_name=snapshot.player_name,
        as_of=snapshot.as_of,
        previous_credits=snapshot.previous_credits,
        target_credits=snapshot.target_credits,
        movement_pct=snapshot.movement_pct,
        football_truth_value_credits=snapshot.football_truth_value_credits,
        market_signal_value_credits=snapshot.market_signal_value_credits,
        scouting_signal_value_credits=getattr(snapshot, "scouting_signal_value_credits", None),
        egame_signal_value_credits=getattr(snapshot, "egame_signal_value_credits", None),
        previous_global_scouting_index=scouting_payload["previous_global_scouting_index"],
        global_scouting_index=scouting_payload["global_scouting_index"],
        global_scouting_index_movement_pct=scouting_payload["global_scouting_index_movement_pct"],
        published_card_value_credits=snapshot.target_credits,
        confidence_score=getattr(snapshot, "confidence_score", None),
        confidence_tier=getattr(snapshot, "confidence_tier", None),
        liquidity_tier=getattr(snapshot, "liquidity_tier", None),
        market_integrity_score=getattr(snapshot, "market_integrity_score", None),
        signal_trust_score=getattr(snapshot, "signal_trust_score", None),
        trend_7d_pct=getattr(snapshot, "trend_7d_pct", None),
        trend_30d_pct=getattr(snapshot, "trend_30d_pct", None),
        trend_direction=getattr(snapshot, "trend_direction", None),
        trend_confidence=getattr(snapshot, "trend_confidence", None),
        snapshot_type=getattr(snapshot, "snapshot_type", "intraday"),
        config_version=getattr(snapshot, "config_version", None),
        movement_tags=_safe_movement_tags(reason_codes),
        breakdown=_build_breakdown_payload(snapshot),
        global_scouting_index_breakdown=scouting_payload["global_scouting_index_breakdown"],
        drivers=tuple(getattr(snapshot, "drivers_json", None) or getattr(snapshot, "drivers", ())),
    )


def _build_daily_close_view(record: Any) -> ValueDailyCloseView:
    return ValueDailyCloseView(
        player_id=record.player_id,
        player_name=record.player_name,
        close_date=record.close_date,
        close_credits=record.close_credits,
        football_truth_value_credits=record.football_truth_value_credits,
        market_signal_value_credits=record.market_signal_value_credits,
        scouting_signal_value_credits=getattr(record, "scouting_signal_value_credits", None),
        egame_signal_value_credits=getattr(record, "egame_signal_value_credits", None),
        confidence_score=getattr(record, "confidence_score", None),
        confidence_tier=getattr(record, "confidence_tier", None),
        liquidity_tier=getattr(record, "liquidity_tier", None),
        trend_7d_pct=getattr(record, "trend_7d_pct", None),
        trend_30d_pct=getattr(record, "trend_30d_pct", None),
        trend_direction=getattr(record, "trend_direction", None),
        trend_confidence=getattr(record, "trend_confidence", None),
        movement_tags=_safe_movement_tags(getattr(record, "reason_codes_json", ())),
    )


@router.post("/snapshots/rebuild", response_model=ValueSnapshotBatchResponse, status_code=status.HTTP_202_ACCEPTED)
def rebuild_value_snapshots(
    payload: ValueSnapshotRebuildRequest,
    request: Request,
) -> ValueSnapshotBatchResponse:
    bridge = request.app.state.value_engine_bridge
    snapshots = bridge.run(
        as_of=payload.as_of,
        lookback_days=payload.lookback_days,
        player_ids=payload.player_ids,
        snapshot_type=payload.snapshot_type,
    )
    return ValueSnapshotBatchResponse(snapshots=[_build_snapshot_view(snapshot) for snapshot in snapshots])


@router.get("/snapshots/{player_id}/latest", response_model=ValueSnapshotView)
def get_latest_value_snapshot(
    player_id: str,
    snapshot_type: str | None = None,
    session: Session = Depends(get_session),
) -> ValueSnapshotView:
    snapshot = ValueSnapshotQueryService(session).get_latest(player_id, snapshot_type=snapshot_type)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No precomputed value snapshot exists for player {player_id}.",
        )
    return _build_snapshot_view(snapshot)


@router.get("/snapshots/{player_id}/history", response_model=ValueHistoryResponse)
def get_value_history(
    player_id: str,
    limit: int = 30,
    snapshot_type: str | None = None,
    session: Session = Depends(get_session),
) -> ValueHistoryResponse:
    snapshots = ValueSnapshotQueryService(session).list_history(
        player_id=player_id,
        limit=limit,
        snapshot_type=snapshot_type,
    )
    return ValueHistoryResponse(snapshots=[_build_snapshot_view(snapshot) for snapshot in snapshots])


@router.get("/snapshots/{player_id}/daily-closes", response_model=ValueDailyCloseResponse)
def get_daily_closes(
    player_id: str,
    limit: int = 30,
    session: Session = Depends(get_session),
) -> ValueDailyCloseResponse:
    closes = ValueSnapshotQueryService(session).list_daily_closes(player_id=player_id, limit=limit)
    return ValueDailyCloseResponse(closes=[_build_daily_close_view(close) for close in closes])


@router.get("/snapshots/{player_id}/trend-summary", response_model=ValueTrendSummaryView)
def get_trend_summary(
    player_id: str,
    session: Session = Depends(get_session),
) -> ValueTrendSummaryView:
    snapshot = ValueSnapshotQueryService(session).get_latest(player_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No precomputed value snapshot exists for player {player_id}.",
        )
    return ValueTrendSummaryView(
        player_id=snapshot.player_id,
        current_value_credits=snapshot.target_credits,
        trend_7d_pct=getattr(snapshot, "trend_7d_pct", 0.0),
        trend_30d_pct=getattr(snapshot, "trend_30d_pct", 0.0),
        trend_direction=getattr(snapshot, "trend_direction", "flat"),
        trend_confidence=getattr(snapshot, "trend_confidence", 0.0),
        confidence_tier=getattr(snapshot, "confidence_tier", "low"),
        movement_tags=_safe_movement_tags(getattr(snapshot, "reason_codes_json", ())),
    )
