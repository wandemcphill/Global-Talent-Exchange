from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.main import create_app


def test_real_app_registers_club_ops_routes(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'club_ops_app.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    try:
        with TestClient(app):
            paths = app.openapi()["paths"]
            modules = set(app.state.domain_modules)

        assert "club_ops" in modules
        assert "club_ops_admin" in modules
        assert "/api/clubs/{club_id}/finances" in paths
        assert "/api/admin/clubs/ops-summary" in paths
    finally:
        engine.dispose()


def test_club_ops_api_flow(club_ops_client) -> None:
    finance_response = club_ops_client.get("/api/clubs/club-api/finances")
    assert finance_response.status_code == 200
    assert finance_response.json()["budget"]["available_budget_minor"] == 1_500_000

    contract_response = club_ops_client.post(
        "/api/clubs/club-api/sponsorships/contracts",
        json={
            "package_code": "community-jersey-front",
            "sponsor_name": "Harbor Energy",
            "duration_months": 6,
            "activate_immediately": True,
        },
    )
    assert contract_response.status_code == 201
    contract_id = contract_response.json()["id"]

    program_response = club_ops_client.post(
        "/api/clubs/club-api/academy/programs",
        json={
            "name": "Club Pathway",
            "program_type": "elite_development",
            "budget_minor": 120000,
            "cycle_length_weeks": 6,
            "focus_attributes": ["technical", "tactical"],
        },
    )
    assert program_response.status_code == 201
    program_id = program_response.json()["id"]

    player_response = club_ops_client.post(
        "/api/clubs/club-api/academy/players",
        json={
            "program_id": program_id,
            "display_name": "Mason Aina",
            "age": 17,
            "primary_position": "CM",
        },
    )
    assert player_response.status_code == 201
    player_id = player_response.json()["id"]

    player_update_response = club_ops_client.patch(
        f"/api/clubs/club-api/academy/players/{player_id}",
        json={
            "attendance_score": 90,
            "coach_assessment": 88,
            "completed_cycles_delta": 1,
        },
    )
    assert player_update_response.status_code == 200
    assert player_update_response.json()["status"] in {"developing", "standout", "promoted"}

    assignment_response = club_ops_client.post(
        "/api/clubs/club-api/scouting/assignments",
        json={
            "region_code": "domestic-core",
            "focus_area": "Ball progression",
            "budget_minor": 45000,
            "scout_count": 2,
        },
    )
    assert assignment_response.status_code == 201

    prospects_response = club_ops_client.get("/api/clubs/club-api/scouting/prospects")
    assert prospects_response.status_code == 200
    prospect_id = prospects_response.json()["prospects"][0]["id"]

    prospect_update_response = club_ops_client.patch(
        f"/api/clubs/club-api/scouting/prospects/{prospect_id}",
        json={"pathway_stage": "shortlisted", "follow_priority": 8},
    )
    assert prospect_update_response.status_code == 200
    assert prospect_update_response.json()["pathway_stage"] == "shortlisted"

    sponsorships_response = club_ops_client.get("/api/clubs/club-api/sponsorships")
    assert sponsorships_response.status_code == 200
    assert sponsorships_response.json()["contracts"][0]["id"] == contract_id
