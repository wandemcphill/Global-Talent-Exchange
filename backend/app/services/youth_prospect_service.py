from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from backend.app.common.enums.player_pathway_stage import PlayerPathwayStage
from backend.app.schemas.club_ops_requests import UpdateYouthProspectRequest
from backend.app.schemas.scouting_core import YouthProspectReportView, YouthProspectView
from backend.app.services.club_finance_service import ClubOpsStore, get_club_ops_store
from backend.app.services.scout_assignment_service import ProspectBlueprint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class YouthProspectService:
    def __init__(self, *, store: ClubOpsStore | None = None) -> None:
        self.store = store or get_club_ops_store()

    def create_from_blueprint(
        self,
        *,
        club_id: str,
        assignment_id: str,
        blueprint: ProspectBlueprint,
    ) -> YouthProspectView:
        prospect_id = f"prospect-{uuid4().hex[:12]}"
        report = YouthProspectReportView(
            id=f"yrp-{uuid4().hex[:12]}",
            prospect_id=prospect_id,
            assignment_id=assignment_id,
            confidence_bps=blueprint.confidence_bps,
            summary_text="Deterministic scouting report generated from assignment coverage and defined evaluation rules.",
            strengths=blueprint.strengths,
            development_flags=blueprint.development_flags,
            created_at=_utcnow(),
        )
        prospect = YouthProspectView(
            id=prospect_id,
            club_id=club_id,
            assignment_id=assignment_id,
            display_name=blueprint.display_name,
            age=blueprint.age,
            nationality_code=blueprint.nationality_code,
            region_label=blueprint.region_label,
            primary_position=blueprint.primary_position,
            secondary_position=blueprint.secondary_position,
            rating_band=blueprint.rating_band,
            development_traits=blueprint.development_traits,
            pathway_stage=PlayerPathwayStage.DISCOVERED,
            discovered_at=_utcnow(),
            scouting_source=blueprint.scouting_source,
            follow_priority=5,
            academy_player_id=None,
            reports=(report,),
        )
        with self.store.lock:
            self.store.prospects_by_club.setdefault(club_id, {})[prospect.id] = prospect
            self.store.prospect_reports_by_prospect.setdefault(prospect.id, []).append(report)
        return prospect

    def list_prospects(self, club_id: str) -> tuple[YouthProspectView, ...]:
        with self.store.lock:
            return tuple(self.store.prospects_by_club.get(club_id, {}).values())

    def get_prospect(self, club_id: str, prospect_id: str) -> YouthProspectView | None:
        with self.store.lock:
            return self.store.prospects_by_club.get(club_id, {}).get(prospect_id)

    def update_prospect(self, club_id: str, prospect_id: str, payload: UpdateYouthProspectRequest) -> YouthProspectView:
        with self.store.lock:
            prospect = self.store.prospects_by_club.get(club_id, {}).get(prospect_id)
            if prospect is None:
                raise ValueError("prospect_not_found")
            if payload.pathway_stage is not None:
                prospect.pathway_stage = payload.pathway_stage
            if payload.follow_priority is not None:
                prospect.follow_priority = payload.follow_priority
        return prospect


@lru_cache
def get_youth_prospect_service() -> YouthProspectService:
    return YouthProspectService(store=get_club_ops_store())


__all__ = ["YouthProspectService", "get_youth_prospect_service"]
