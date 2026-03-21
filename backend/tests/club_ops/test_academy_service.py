from __future__ import annotations

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.schemas.club_ops_requests import (
    CreateAcademyPlayerRequest,
    CreateAcademyProgramRequest,
    UpdateAcademyPlayerRequest,
)


def test_academy_service_creates_programs_players_and_graduation_events(club_ops_services) -> None:
    academy = club_ops_services["academy"]
    finance = club_ops_services["finance"]

    program = academy.create_program(
        "club-academy",
        CreateAcademyProgramRequest(
            name="Elite Pathway",
            program_type="elite_development",
            budget_minor=120_000,
            cycle_length_weeks=6,
            focus_attributes=("technical", "tactical"),
        ),
    )
    player = academy.create_player(
        "club-academy",
        CreateAcademyPlayerRequest(
            program_id=program.id,
            display_name="Kelechi Bright",
            age=17,
            primary_position="CM",
        ),
    )
    updated = academy.update_player(
        "club-academy",
        player.id,
        UpdateAcademyPlayerRequest(
            attendance_score=96,
            coach_assessment=95,
            completed_cycles_delta=3,
            attribute_deltas={"technical": 24, "tactical": 24, "physical": 22, "mentality": 22},
            status=AcademyPlayerStatus.PROMOTED,
        ),
    )
    overview = academy.get_overview("club-academy")
    cashflow = finance.get_cashflow_summary("club-academy")

    assert updated.status == AcademyPlayerStatus.PROMOTED
    assert overview.promoted_count == 1
    assert len(overview.training_cycles) == 1
    assert len(overview.graduation_events) == 1
    assert cashflow.academy_spend_minor == 120_000
