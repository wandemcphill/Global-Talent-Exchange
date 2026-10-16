from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from app.common.enums.player_pathway_stage import PlayerPathwayStage
from app.schemas.scouting_core import YouthPipelineSnapshotView
from app.services.club_finance_service import ClubOpsStore, get_club_ops_store


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class YouthPipelineService:
    def __init__(self, *, store: ClubOpsStore | None = None) -> None:
        self.store = store or get_club_ops_store()

    def capture(self, club_id: str) -> YouthPipelineSnapshotView:
        with self.store.lock:
            prospects = tuple(self.store.prospects_by_club.get(club_id, {}).values())
        funnel = {
            stage.value: sum(1 for prospect in prospects if prospect.pathway_stage == stage)
            for stage in PlayerPathwayStage
        }
        discovered = max(1, funnel[PlayerPathwayStage.DISCOVERED.value])
        academy_signed = funnel[PlayerPathwayStage.ACADEMY_SIGNED.value]
        promoted = funnel[PlayerPathwayStage.PROMOTED.value]
        snapshot = YouthPipelineSnapshotView(
            club_id=club_id,
            captured_at=_utcnow(),
            funnel=funnel,
            academy_conversion_rate_bps=round((academy_signed / discovered) * 10_000),
            promotion_rate_bps=round((promoted / discovered) * 10_000),
        )
        with self.store.lock:
            self.store.youth_pipeline_by_club[club_id] = snapshot
        return snapshot

    def get_snapshot(self, club_id: str) -> YouthPipelineSnapshotView:
        with self.store.lock:
            existing = self.store.youth_pipeline_by_club.get(club_id)
        if existing is not None:
            return existing
        return self.capture(club_id)


@lru_cache
def get_youth_pipeline_service() -> YouthPipelineService:
    return YouthPipelineService(store=get_club_ops_store())


__all__ = ["YouthPipelineService", "get_youth_pipeline_service"]
