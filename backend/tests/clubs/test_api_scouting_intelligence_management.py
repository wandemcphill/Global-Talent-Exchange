from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ingestion.models import Player
from backend.app.models.regen import AcademyCandidate, AcademyIntakeBatch, RegenProfile
from backend.app.models.scouting_intelligence import ManagerScoutingProfile, ScoutMission, ScoutingNetwork, ScoutingNetworkAssignment


def _starter_regens(session: Session, club_id: str) -> list[RegenProfile]:
    return session.scalars(
        select(RegenProfile).where(RegenProfile.generated_for_club_id == club_id).order_by(RegenProfile.regen_id)
    ).all()


def _player_for_regen(session: Session, regen: RegenProfile) -> Player:
    player = session.get(Player, regen.player_id)
    assert player is not None
    return player


def _set_profile_window(
    session: Session,
    regen: RegenProfile,
    *,
    age: int,
    current_min: int,
    current_max: int,
    potential_min: int,
    potential_max: int,
    position: str,
) -> None:
    player = _player_for_regen(session, regen)
    player.date_of_birth = date.today() - timedelta(days=age * 365)
    player.position = position
    player.normalized_position = "forward"
    regen.primary_position = position
    regen.current_gsi = current_max
    regen.current_ability_range_json = {"minimum": current_min, "maximum": current_max}
    regen.potential_range_json = {"minimum": potential_min, "maximum": potential_max}
    session.flush()


def _add_academy_candidate(session: Session, club_id: str, regen: RegenProfile) -> None:
    batch = AcademyIntakeBatch(
        club_id=club_id,
        season_label="2026/27",
        intake_size=1,
        academy_quality_score=86.0,
        status="generated",
        metadata_json={"source": "management-api-test"},
    )
    session.add(batch)
    session.flush()
    session.add(
        AcademyCandidate(
            batch_id=batch.id,
            club_id=club_id,
            regen_profile_id=regen.id,
            display_name=_player_for_regen(session, regen).full_name,
            age=18,
            nationality_code=regen.birth_country_code,
            birth_region=regen.birth_region,
            birth_city=regen.birth_city,
            primary_position=regen.primary_position,
            secondary_position=(regen.secondary_positions_json[0] if regen.secondary_positions_json else None),
            current_ability_range_json=regen.current_ability_range_json,
            potential_range_json=regen.potential_range_json,
            scout_confidence="medium",
            status="academy_candidate",
            metadata_json={"origin": "academy"},
        )
    )
    session.flush()


def _prepare_thread_a_surface(session: Session, club_id: str) -> RegenProfile:
    regen = _starter_regens(session, club_id)[0]
    regen.birth_region = "lagos"
    regen.birth_city = "lagos"
    _set_profile_window(
        session,
        regen,
        age=18,
        current_min=68,
        current_max=72,
        potential_min=89,
        potential_max=94,
        position="ST",
    )
    _add_academy_candidate(session, club_id, regen)
    return regen


def test_scouting_intelligence_management_endpoints_create_complete_and_plan(
    client: TestClient,
    session: Session,
    create_club,
) -> None:
    club = create_club(slug="scouting-intelligence-management")
    _prepare_thread_a_surface(session, club["id"])

    manager_response = client.post(
        f"/api/clubs/{club['id']}/scouting-intelligence/manager-profiles",
        json={
            "manager_code": "mgr-youth",
            "manager_name": "Youth Director",
            "persona_code": "Youth Developer",
            "preferred_system": "4-3-3",
            "metadata": {"department": "elite-pathway"},
        },
    )
    assert manager_response.status_code == 201, manager_response.text
    manager_payload = manager_response.json()

    network_response = client.post(
        f"/api/clubs/{club['id']}/scouting-intelligence/networks",
        json={
            "manager_profile_id": manager_payload["id"],
            "network_name": "West Africa Watch",
            "region_code": "west_africa",
            "region_name": "West Africa",
            "specialty_code": "wonderkid",
            "quality_tier": "elite",
            "weekly_cost_coin": 1600,
            "scout_identity": "Chief Scout",
            "report_cadence_days": 7,
            "metadata": {"focus": "academy-to-first-team"},
        },
    )
    assert network_response.status_code == 201, network_response.text
    network_payload = network_response.json()

    assignment_response = client.post(
        f"/api/clubs/{club['id']}/scouting-intelligence/assignments",
        json={
            "network_id": network_payload["id"],
            "assignment_name": "Lagos U20 sweep",
            "assignment_scope": "region",
            "territory_code": "lagos",
            "focus_position": "ST",
            "age_band_min": 16,
            "age_band_max": 20,
            "budget_profile": "value",
            "metadata": {"timeline": "summer-window"},
        },
    )
    assert assignment_response.status_code == 201, assignment_response.text
    assignment_payload = assignment_response.json()

    mission_response = client.post(
        f"/api/clubs/{club['id']}/scouting-intelligence/missions",
        json={
            "network_id": network_payload["id"],
            "manager_profile_id": manager_payload["id"],
            "mission_name": "Find immediate upside",
            "mission_type": "deep_talent_search",
            "target_position": "ST",
            "target_region": "lagos",
            "target_age_max": 20,
            "budget_limit_coin": 500000,
            "talent_type": "wonderkid",
            "include_academy": True,
            "system_profile": "4-3-3",
            "metadata": {"timeline": "preseason"},
        },
    )
    assert mission_response.status_code == 201, mission_response.text
    mission_payload = mission_response.json()

    manager_list_response = client.get(f"/api/clubs/{club['id']}/scouting-intelligence/manager-profiles")
    complete_response = client.post(
        f"/api/clubs/{club['id']}/scouting-intelligence/missions/{mission_payload['id']}/complete",
        params={"limit": 1},
    )
    academy_signals_response = client.get(f"/api/clubs/{club['id']}/scouting-intelligence/academy-supply-signals")
    badges_response = client.get(
        f"/api/clubs/{club['id']}/scouting-intelligence/badges",
        params={"mission_id": mission_payload["id"], "limit": 5},
    )
    lifecycle_response = client.get(
        f"/api/clubs/{club['id']}/scouting-intelligence/lifecycle",
        params={"sync_current_roster": True, "limit": 5},
    )
    planning_response = client.get(
        f"/api/clubs/{club['id']}/scouting-intelligence/planning",
        params={"roster_limit": 5},
    )

    assert manager_list_response.status_code == 200
    assert complete_response.status_code == 200, complete_response.text
    assert academy_signals_response.status_code == 200
    assert badges_response.status_code == 200
    assert lifecycle_response.status_code == 200
    assert planning_response.status_code == 200

    complete_payload = complete_response.json()
    academy_signals_payload = academy_signals_response.json()
    badges_payload = badges_response.json()
    lifecycle_payload = lifecycle_response.json()
    planning_payload = planning_response.json()

    assert manager_list_response.json()[0]["manager_code"] == "mgr-youth"
    assert assignment_payload["territory_code"] == "lagos"
    assert complete_payload["mission"]["status"] == "completed"
    assert len(complete_payload["reports"]) == 1
    assert len(complete_payload["hidden_potential_estimates"]) == 1
    assert academy_signals_payload[0]["candidate_count"] == 1
    assert badges_payload
    assert lifecycle_payload
    assert planning_payload["manager_profiles"][0]["manager_name"] == "Youth Director"
    assert planning_payload["academy_supply_signals"][0]["candidate_count"] == 1
    assert planning_payload["lifecycle_profiles"]
    assert planning_payload["badges"]

    assert session.get(ManagerScoutingProfile, manager_payload["id"]) is not None
    assert session.get(ScoutingNetwork, network_payload["id"]) is not None
    assert session.get(ScoutingNetworkAssignment, assignment_payload["id"]) is not None
    assert session.get(ScoutMission, mission_payload["id"]).status == "completed"
