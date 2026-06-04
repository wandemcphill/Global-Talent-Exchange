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
        assert "/api/clubs/{club_id}/dashboard" in paths
        assert "/api/clubs/{club_id}/squad" in paths
        assert "/api/clubs/{club_id}/squad/availability" in paths
        assert "/api/clubs/{club_id}/squad/injuries" in paths
        assert "/api/clubs/{club_id}/squad/chemistry" in paths
        assert "/api/clubs/{club_id}/squad/contracts" in paths
        assert "/api/clubs/{club_id}/squad/scouting" in paths
        assert "/api/clubs/{club_id}/squad/readiness" in paths
        assert "/api/clubs/{club_id}/staff" in paths
        assert "/api/clubs/{club_id}/rankings" in paths
        assert "/api/v2/clubs/{club_id}/formation" in paths
        assert "/api/v2/clubs/{club_id}/formation/active" in paths
        assert "/api/v2/clubs/{club_id}/formation/draft" in paths
        assert "/api/v2/clubs/{club_id}/formation/publish" in paths
        assert "/api/v2/clubs/{club_id}/formations" in paths
        assert "/api/v2/clubs/{club_id}/formations/draft" in paths
        assert "/api/v2/clubs/{club_id}/formations/{formation_id}/publish" in paths
        assert "/api/v2/clubs/{club_id}/formations/{source_formation_id}/restore" in paths
        assert "/api/v2/formations/{formation_id}" in paths
        assert "/api/admin/clubs/ops-summary" in paths
    finally:
        engine.dispose()


def test_canonical_club_ops_read_contracts_return_backend_states(club_ops_client) -> None:
    for path in (
        "/api/clubs/club-api/dashboard",
        "/api/clubs/club-api/squad",
        "/api/clubs/club-api/squad/availability",
        "/api/clubs/club-api/squad/injuries",
        "/api/clubs/club-api/squad/chemistry",
        "/api/clubs/club-api/squad/contracts",
        "/api/clubs/club-api/squad/scouting",
        "/api/clubs/club-api/squad/readiness",
        "/api/clubs/club-api/staff",
        "/api/clubs/club-api/rankings",
    ):
        response = club_ops_client.get(path)

        assert response.status_code == 200

    assert club_ops_client.get("/api/clubs/club-api/dashboard").json()["club_id"] == "club-api"
    assert club_ops_client.get("/api/clubs/club-api/squad").json()["players"] == []
    assert club_ops_client.get("/api/clubs/club-api/squad/selection-ready").json()["players"] == []
    readiness = club_ops_client.get("/api/clubs/club-api/squad/readiness").json()
    assert readiness["state"] == "blocked"
    assert readiness["lanes"]["medical"]["status"] == "missing"
    assert readiness["lanes"]["morale"]["status"] == "missing"
    assert readiness["lanes"]["chemistry"]["status"] == "missing"
    assert readiness["lanes"]["contracts"]["status"] == "missing"
    assert readiness["injured_count"] is None
    assert readiness["available_for_next_fixture"] is None


def test_squad_lane_contracts_surface_missing_authoritative_data(club_ops_client) -> None:
    availability = club_ops_client.get("/api/clubs/club-api/squad/availability")
    injuries = club_ops_client.get("/api/clubs/club-api/squad/injuries")
    chemistry = club_ops_client.get("/api/clubs/club-api/squad/chemistry")
    contracts = club_ops_client.get("/api/clubs/club-api/squad/contracts")
    scouting = club_ops_client.get("/api/clubs/club-api/squad/scouting")

    assert availability.status_code == 200
    assert availability.json()["state"] == "blocked"
    assert availability.json()["missing_data"][0]["source"] == "senior_squad_roster"

    assert injuries.status_code == 200
    assert injuries.json()["state"] == "blocked"
    assert injuries.json()["medical"]["status"] == "missing"
    assert injuries.json()["missing_data"][0]["source"] == "player_medical_availability"

    assert chemistry.status_code == 200
    assert chemistry.json()["overall_score"] is None
    assert chemistry.json()["missing_data"][0]["source"] == "team_chemistry_model"

    assert contracts.status_code == 200
    assert contracts.json()["contracts"] == []
    assert contracts.json()["missing_data"][0]["source"] == "player_contracts"

    assert scouting.status_code == 200
    assert scouting.json()["state"] == "empty"
    assert scouting.json()["scouting_notes"] == []


def test_canonical_formation_storage_gap_remains_blocked(club_ops_client) -> None:
    response = club_ops_client.get("/api/v2/clubs/club-api/formation")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "blocked"
    assert body["status"] == "blocked"
    assert body["club_id"] == "club-api"
    assert body["slots"] == []
    assert body["health"]["score"] is None
    assert body["can_save_draft"] is False
    assert body["can_publish"] is False
    assert {item["source"] for item in body["missing_data"]} == {
        "club_ops_formation_store",
        "club_ops_formation_validation",
    }


def test_frontend_formation_repository_contracts_are_declared(club_ops_client) -> None:
    active_response = club_ops_client.get("/api/v2/clubs/club-api/formation/active")
    assert active_response.status_code == 404
    active_body = active_response.json()["detail"]
    assert active_body["state"] == "empty"
    assert active_body["code"] == "formation_active_not_found"

    history_response = club_ops_client.get("/api/v2/clubs/club-api/formations")
    assert history_response.status_code == 200
    history_body = history_response.json()
    assert history_body["state"] == "empty"
    assert history_body["formations"] == []
    assert history_body["items"] == []
    assert history_body["missing_data"] == []

    detail_response = club_ops_client.get("/api/v2/formations/formation-1")
    assert detail_response.status_code == 404
    detail_body = detail_response.json()["detail"]
    assert detail_body["state"] == "empty"
    assert detail_body["formation_id"] == "formation-1"
    assert detail_body["code"] == "formation_not_found"

    invalid_requests = (
        (club_ops_client.patch("/api/v2/clubs/club-api/formation/draft", json={}), 422, "formation_name_required"),
        (club_ops_client.post("/api/v2/clubs/club-api/formation/publish", json={}), 422, "formation_id_required"),
        (club_ops_client.post("/api/v2/clubs/club-api/formations/draft", json={}), 422, "formation_name_required"),
        (
            club_ops_client.post("/api/v2/clubs/club-api/formations/formation-1/publish", json={}),
            404,
            "formation_not_found",
        ),
        (
            club_ops_client.post("/api/v2/clubs/club-api/formations/formation-1/restore", json={}),
            404,
            "formation_not_found",
        ),
    )
    for response, expected_status, expected_code in invalid_requests:
        assert response.status_code == expected_status
        detail = response.json()["detail"]
        assert detail["code"] == expected_code
        assert detail["club_id"] == "club-api"


def test_club_ops_api_flow(club_ops_client) -> None:
    finance_response = club_ops_client.get("/api/clubs/club-api/finances")
    assert finance_response.status_code == 200
    finance_payload = finance_response.json()
    assert finance_payload["budget"]["available_budget_minor"] == 1_500_000
    assert finance_payload["balance_summary"]["current_balance"] == 15_000

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

    squad_response = club_ops_client.get("/api/clubs/club-api/squad")
    assert squad_response.status_code == 200
    squad_players = squad_response.json()["players"]
    assert squad_players[0]["id"] == player_id
    assert squad_players[0]["name"] == "Mason Aina"
    assert squad_players[0]["position"] == "CM"

    readiness_response = club_ops_client.get("/api/clubs/club-api/squad/readiness")
    assert readiness_response.status_code == 200
    readiness_payload = readiness_response.json()
    assert readiness_payload["eligible_count"] in {0, 1}
    assert readiness_payload["state"] == "blocked"
    assert readiness_payload["lanes"]["availability"]["source"] == "academy_service"
    assert readiness_payload["lanes"]["medical"]["status"] == "missing"
    assert readiness_payload["lanes"]["contracts"]["status"] == "missing"
    assert readiness_payload["injured_count"] is None
    assert readiness_payload["available_for_next_fixture"] is None

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

    scouting_notes_response = club_ops_client.get("/api/clubs/club-api/squad/scouting")
    assert scouting_notes_response.status_code == 200
    assert scouting_notes_response.json()["scouting_notes"]
