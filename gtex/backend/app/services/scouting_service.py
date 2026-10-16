from __future__ import annotations

from functools import lru_cache

from app.common.enums.player_pathway_stage import PlayerPathwayStage
from app.schemas.club_ops_requests import CreateScoutAssignmentRequest, UpdateYouthProspectRequest
from app.schemas.club_ops_responses import (
    ScoutingOverviewResponse,
    ScoutingProspectDetailResponse,
    ScoutingProspectsResponse,
)
from app.services.academy_service import AcademyService, get_academy_service
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_finance_service, get_club_ops_store
from app.services.scout_assignment_service import ScoutAssignmentService, get_scout_assignment_service
from app.services.youth_pipeline_service import YouthPipelineService, get_youth_pipeline_service
from app.services.youth_prospect_service import YouthProspectService, get_youth_prospect_service


class ScoutingService:
    def __init__(
        self,
        *,
        store: ClubOpsStore | None = None,
        finance_service: ClubFinanceService | None = None,
        assignment_service: ScoutAssignmentService | None = None,
        prospect_service: YouthProspectService | None = None,
        pipeline_service: YouthPipelineService | None = None,
        academy_service: AcademyService | None = None,
    ) -> None:
        self.store = store or get_club_ops_store()
        self.finance_service = finance_service or get_club_finance_service()
        self.assignment_service = assignment_service or get_scout_assignment_service()
        self.prospect_service = prospect_service or get_youth_prospect_service()
        self.pipeline_service = pipeline_service or get_youth_pipeline_service()
        self.academy_service = academy_service or get_academy_service()

    def get_overview(self, club_id: str) -> ScoutingOverviewResponse:
        self._ensure_club_setup(club_id)
        with self.store.lock:
            assignments = tuple(self.store.scouting_assignments_by_club.get(club_id, {}).values())
        prospects = self.prospect_service.list_prospects(club_id)
        return ScoutingOverviewResponse(
            club_id=club_id,
            regions=self.assignment_service.list_regions(),
            assignments=assignments,
            prospects=prospects,
            pipeline_snapshot=self.pipeline_service.get_snapshot(club_id),
        )

    def create_assignment(self, club_id: str, payload: CreateScoutAssignmentRequest):
        self._ensure_club_setup(club_id)
        assignment, blueprints = self.assignment_service.create_assignment(club_id=club_id, payload=payload)
        prospects = tuple(
            self.prospect_service.create_from_blueprint(
                club_id=club_id,
                assignment_id=assignment.id,
                blueprint=blueprint,
            )
            for blueprint in blueprints
        )
        assignment.generated_prospect_ids = tuple(prospect.id for prospect in prospects)
        with self.store.lock:
            self.store.scouting_assignments_by_club.setdefault(club_id, {})[assignment.id] = assignment
        self.finance_service.record_scouting_assignment_debit(
            club_id,
            amount_minor=payload.budget_minor,
            reference_id=assignment.id,
            description=f"Scouting assignment budget reserved for {assignment.region_name}.",
        )
        self.pipeline_service.capture(club_id)
        return assignment

    def list_prospects(self, club_id: str) -> ScoutingProspectsResponse:
        self._ensure_club_setup(club_id)
        return ScoutingProspectsResponse(club_id=club_id, prospects=self.prospect_service.list_prospects(club_id))

    def get_prospect(self, club_id: str, prospect_id: str) -> ScoutingProspectDetailResponse:
        self._ensure_club_setup(club_id)
        prospect = self.prospect_service.get_prospect(club_id, prospect_id)
        if prospect is None:
            raise ValueError("prospect_not_found")
        return ScoutingProspectDetailResponse(
            prospect=prospect,
            pipeline_snapshot=self.pipeline_service.get_snapshot(club_id),
        )

    def update_prospect(self, club_id: str, prospect_id: str, payload: UpdateYouthProspectRequest):
        self._ensure_club_setup(club_id)
        prospect = self.prospect_service.update_prospect(club_id, prospect_id, payload)
        if payload.convert_to_academy and prospect.pathway_stage == PlayerPathwayStage.ACADEMY_SIGNED and prospect.academy_player_id is None:
            academy_player = self.academy_service.enroll_prospect(
                club_id=club_id,
                display_name=prospect.display_name,
                age=prospect.age,
                primary_position=prospect.primary_position,
                secondary_position=prospect.secondary_position,
                program_id=payload.academy_program_id,
                pathway_note="Converted from the youth scouting pipeline into the academy pathway.",
            )
            prospect.academy_player_id = academy_player.id
        self.pipeline_service.capture(club_id)
        return prospect

    def _ensure_club_setup(self, club_id: str) -> None:
        self.finance_service.ensure_club_setup(club_id)
        with self.store.lock:
            self.store.scouting_assignments_by_club.setdefault(club_id, {})
            self.store.prospects_by_club.setdefault(club_id, {})


@lru_cache
def get_scouting_service() -> ScoutingService:
    return ScoutingService(
        store=get_club_ops_store(),
        finance_service=get_club_finance_service(),
        assignment_service=get_scout_assignment_service(),
        prospect_service=get_youth_prospect_service(),
        pipeline_service=get_youth_pipeline_service(),
        academy_service=get_academy_service(),
    )


__all__ = ["ScoutingService", "get_scouting_service"]
