from __future__ import annotations

from backend.app.common.enums.player_pathway_stage import PlayerPathwayStage
from backend.app.schemas.club_ops_requests import (
    CreateAcademyProgramRequest,
    CreateScoutAssignmentRequest,
    UpdateYouthProspectRequest,
)


def test_youth_pipeline_tracks_academy_and_promotion_conversions(club_ops_services) -> None:
    academy = club_ops_services["academy"]
    scouting = club_ops_services["scouting"]
    pipeline = club_ops_services["pipeline"]

    academy_program = academy.create_program(
        "club-pipeline",
        CreateAcademyProgramRequest(
            name="Pathway Intake",
            program_type="fundamentals",
            budget_minor=80_000,
            cycle_length_weeks=4,
            focus_attributes=("technical", "physical"),
        ),
    )
    scouting.create_assignment(
        "club-pipeline",
        CreateScoutAssignmentRequest(
            region_code="domestic-core",
            focus_area="Transition play",
            budget_minor=35_000,
            scout_count=2,
        ),
    )
    prospect = scouting.list_prospects("club-pipeline").prospects[0]
    scouting.update_prospect(
        "club-pipeline",
        prospect.id,
        UpdateYouthProspectRequest(
            pathway_stage=PlayerPathwayStage.ACADEMY_SIGNED,
            convert_to_academy=True,
            academy_program_id=academy_program.id,
        ),
    )
    scouting.update_prospect(
        "club-pipeline",
        prospect.id,
        UpdateYouthProspectRequest(pathway_stage=PlayerPathwayStage.PROMOTED),
    )
    snapshot = pipeline.capture("club-pipeline")

    assert snapshot.funnel["academy_signed"] >= 0
    assert snapshot.funnel["promoted"] == 1
    assert snapshot.academy_conversion_rate_bps >= 0
    assert snapshot.promotion_rate_bps > 0
