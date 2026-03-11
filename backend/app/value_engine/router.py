from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.value_engine.jobs import InMemoryValueSnapshotRepository, ValueSnapshotJob
from backend.app.value_engine.schemas import (
    ValueSnapshotBatchRequest,
    ValueSnapshotBatchResponse,
    ValueSnapshotView,
)

router = APIRouter(prefix="/value-engine", tags=["value-engine"])


@router.post("/snapshots", response_model=ValueSnapshotBatchResponse)
def build_value_snapshots(payload: ValueSnapshotBatchRequest) -> ValueSnapshotBatchResponse:
    player_ids = [item.player_id for item in payload.inputs]
    if len(set(player_ids)) != len(player_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player inputs must contain unique player_id values.",
        )

    repository = InMemoryValueSnapshotRepository(
        inputs={item.player_id: item.to_domain(payload.as_of) for item in payload.inputs}
    )
    snapshots = ValueSnapshotJob(lookback_days=payload.lookback_days).run(repository, payload.as_of)
    return ValueSnapshotBatchResponse(
        snapshots=[ValueSnapshotView.model_validate(snapshot) for snapshot in snapshots]
    )
