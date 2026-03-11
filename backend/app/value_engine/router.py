from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_session
from backend.app.value_engine.schemas import (
    ValueSnapshotBatchResponse,
    ValueSnapshotRebuildRequest,
    ValueSnapshotView,
)
from backend.app.value_engine.service import ValueSnapshotQueryService

router = APIRouter(prefix="/value-engine", tags=["value-engine"])


def _build_breakdown_payload(snapshot) -> dict:
    breakdown_json = snapshot.breakdown_json or {}
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
    }


def _build_global_scouting_index_payload(snapshot) -> dict:
    breakdown_json = snapshot.breakdown_json or {}
    gsi_breakdown_json = breakdown_json.get("global_scouting_index_breakdown") or {}
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
    )
    return ValueSnapshotBatchResponse(
        snapshots=[ValueSnapshotView.model_validate(snapshot) for snapshot in snapshots]
    )


@router.get("/snapshots/{player_id}/latest", response_model=ValueSnapshotView)
def get_latest_value_snapshot(
    player_id: str,
    session: Session = Depends(get_session),
) -> ValueSnapshotView:
    snapshot = ValueSnapshotQueryService(session).get_latest(player_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No precomputed value snapshot exists for player {player_id}.",
        )
    scouting_payload = _build_global_scouting_index_payload(snapshot)
    return ValueSnapshotView(
        player_id=snapshot.player_id,
        player_name=snapshot.player_name,
        as_of=snapshot.as_of,
        previous_credits=snapshot.previous_credits,
        target_credits=snapshot.target_credits,
        movement_pct=snapshot.movement_pct,
        football_truth_value_credits=snapshot.football_truth_value_credits,
        market_signal_value_credits=snapshot.market_signal_value_credits,
        previous_global_scouting_index=scouting_payload["previous_global_scouting_index"],
        global_scouting_index=scouting_payload["global_scouting_index"],
        global_scouting_index_movement_pct=scouting_payload["global_scouting_index_movement_pct"],
        published_card_value_credits=snapshot.target_credits,
        breakdown=_build_breakdown_payload(snapshot),
        global_scouting_index_breakdown=scouting_payload["global_scouting_index_breakdown"],
        drivers=tuple(snapshot.drivers_json),
    )
