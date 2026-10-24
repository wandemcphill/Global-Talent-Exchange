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

def test_academy_underage_player_held_at_standout_until_sixteen(club_ops_services) -> None:
    academy = club_ops_services["academy"]

    program = academy.create_program(
        "club-academy-youth",
        CreateAcademyProgramRequest(
            name="Junior Pathway",
            program_type="fundamentals",
            budget_minor=60_000,
            cycle_length_weeks=4,
            focus_attributes=("technical", "tactical"),
        ),
    )
    # 15 year old prodigy
    player = academy.create_player(
        "club-academy-youth",
        CreateAcademyPlayerRequest(
            program_id=program.id,
            display_name="Wonderkid Junior",
            age=15,
            primary_position="AM",
        ),
    )
    # High readiness (85+) and 3+ cycles: should be held at STANDOUT, not PROMOTED
    updated = academy.update_player(
        "club-academy-youth",
        player.id,
        UpdateAcademyPlayerRequest(
            attendance_score=98,
            coach_assessment=96,
            completed_cycles_delta=3,
            attribute_deltas={"technical": 30, "tactical": 28, "physical": 25, "mentality": 25},
            status=AcademyPlayerStatus.PROMOTED,
        ),
    )
    assert updated.status == AcademyPlayerStatus.STANDOUT, "Underage player (<16) must be held at STANDOUT"


def test_club_growth_promote_prospect_underage_blocked_and_governance_recorded(monkeypatch) -> None:
    from app.club_growth.service import ClubGrowthService, ClubGrowthError
    from app.models.club_growth import AcademyProspect, AcademyPromotionHistory
    from app.models.user import User, UserRole
    from unittest.mock import MagicMock
    import pytest

    session = MagicMock()
    service = ClubGrowthService(session)
    actor = User(id="user-1", email="owner@gtex.club", role=UserRole.CLUB)

    underage_prospect = AcademyProspect(
        id="pros-underage",
        club_id="club-1",
        display_name="Young Talent",
        position="CM",
        academy_profile_id="acad-1",
        age=15,
        status="youth_signed",
        current_ability=55,
        potential=88,
    )
    eligible_prospect = AcademyProspect(
        id="pros-eligible",
        club_id="club-1",
        display_name="Senior Ready",
        position="ST",
        academy_profile_id="acad-1",
        age=16,
        status="youth_signed",
        current_ability=60,
        potential=85,
        portrait_asset_ref="asset://portrait/1",
    )

    current_target = [underage_prospect]
    monkeypatch.setattr(ClubGrowthService, "_get_prospect", lambda self, club_id, prospect_id: current_target[0])
    monkeypatch.setattr(ClubGrowthService, "_promotion_history", lambda self, prospect_id: None)

    with pytest.raises(ClubGrowthError) as exc_info:
        service.promote_prospect(actor=actor, club_id="club-1", prospect_id="pros-underage")
    assert "academy_player_too_young_to_promote" in str(exc_info.value)

    current_target[0] = eligible_prospect
    fake_player = MagicMock(id="player-senior-1")
    monkeypatch.setattr(ClubGrowthService, "_ensure_senior_player_for_prospect", lambda self, club_id, prospect: fake_player)
    monkeypatch.setattr(ClubGrowthService, "_ensure_contract_and_squad_for_promoted_prospect", lambda self, club_id, prospect, player: None)
    monkeypatch.setattr(ClubGrowthService, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(ClubGrowthService, "_academy_prospect_view", lambda self, p: {"id": p.id, "status": "promoted_to_senior"})

    result = service.promote_prospect(actor=actor, club_id="club-1", prospect_id="pros-eligible")
    assert eligible_prospect.status == "promoted_to_senior"
    added_history = [arg[0][0] for arg in session.add.call_args_list if isinstance(arg[0][0], AcademyPromotionHistory)][0]
    assert added_history.metadata_json["hoyd_pathway_verified"] is True
    assert added_history.metadata_json["manager_sporting_readiness_approved"] is True
    assert added_history.metadata_json["governance_signoff"] == "hoyd_and_football_manager"

