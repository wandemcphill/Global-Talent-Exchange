from __future__ import annotations

from app.schemas.club_ops_requests import CreateScoutAssignmentRequest


def test_scouting_service_generates_deterministic_prospects_and_spend(club_ops_services) -> None:
    scouting = club_ops_services["scouting"]
    finance = club_ops_services["finance"]

    assignment = scouting.create_assignment(
        "club-scouting",
        CreateScoutAssignmentRequest(
            region_code="domestic-core",
            focus_area="Ball progression",
            budget_minor=45_000,
            scout_count=2,
        ),
    )
    prospects = scouting.list_prospects("club-scouting").prospects
    cashflow = finance.get_cashflow_summary("club-scouting")

    assert assignment.region_code == "domestic-core"
    assert len(assignment.generated_prospect_ids) == 3
    assert len(prospects) == 3
    assert prospects[0].display_name
    assert prospects[0].reports[0].confidence_bps >= 6500
    assert cashflow.scouting_spend_minor == 45_000
