from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ingestion.models import Player
from backend.app.models.regen import AcademyCandidate, AcademyIntakeBatch, RegenProfile
from backend.app.services.scouting_intelligence_service import (
    ManagerProfileUpsert,
    ScoutMissionCreate,
    ScoutingIntelligenceService,
    ScoutingNetworkAssignmentCreate,
    ScoutingNetworkCreate,
)


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


def _add_academy_candidate(session: Session, club_id: str, regen: RegenProfile) -> AcademyCandidate:
    batch = AcademyIntakeBatch(
        club_id=club_id,
        season_label="2026/27",
        intake_size=1,
        academy_quality_score=85.0,
        status="generated",
        metadata_json={"source": "api-test"},
    )
    session.add(batch)
    session.flush()

    candidate = AcademyCandidate(
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
    session.add(candidate)
    session.flush()
    return candidate


def _seed_scouting_intelligence(session: Session, club_id: str) -> tuple[str, str, str]:
    regens = _starter_regens(session, club_id)
    assert regens
    regen = regens[0]
    regen.birth_region = "lagos"
    regen.birth_city = "lagos"
    _set_profile_window(
        session,
        regen,
        age=18,
        current_min=68,
        current_max=72,
        potential_min=90,
        potential_max=93,
        position="ST",
    )
    _add_academy_candidate(session, club_id, regen)

    service = ScoutingIntelligenceService(session)
    manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club_id,
            manager_code="mgr-youth",
            manager_name="Youth Scout",
            persona_code="youth_developer",
            preferred_system="4-3-3",
        )
    )
    network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club_id,
            manager_profile_id=manager.id,
            network_name="Wonderkid Radar",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="wonderkid",
            quality_tier="elite",
            weekly_cost_coin=1400,
            scout_identity="Chief Scout",
        )
    )
    assignment = service.assign_network(
        ScoutingNetworkAssignmentCreate(
            network_id=network.id,
            club_id=club_id,
            assignment_name="Lagos U20 sweep",
            territory_code="lagos",
            focus_position="ST",
            age_band_min=16,
            age_band_max=20,
            budget_profile="value",
        )
    )
    mission = service.create_mission(
        ScoutMissionCreate(
            club_id=club_id,
            network_id=network.id,
            manager_profile_id=manager.id,
            mission_name="Find elite upside",
            mission_type="deep_talent_search",
            target_position="ST",
            target_region="lagos",
            target_age_max=20,
            talent_type="wonderkid",
        )
    )
    completed = service.complete_mission(mission.id, limit=1)
    assert completed.awarded_badges
    return network.id, assignment.id, mission.id


def test_scouting_intelligence_read_endpoints_expose_networks_and_missions(
    client: TestClient,
    session: Session,
    create_club,
) -> None:
    club = create_club(slug="scouting-intelligence-read")
    network_id, assignment_id, mission_id = _seed_scouting_intelligence(session, club["id"])

    networks_response = client.get(f"/api/clubs/{club['id']}/scouting-intelligence/networks")
    assignments_response = client.get(
        f"/api/clubs/{club['id']}/scouting-intelligence/assignments",
        params={"network_id": network_id},
    )
    missions_response = client.get(
        f"/api/clubs/{club['id']}/scouting-intelligence/missions",
        params={"status": "completed"},
    )
    mission_detail_response = client.get(
        f"/api/clubs/{club['id']}/scouting-intelligence/missions/{mission_id}"
    )

    assert networks_response.status_code == 200
    assert assignments_response.status_code == 200
    assert missions_response.status_code == 200
    assert mission_detail_response.status_code == 200

    networks_payload = networks_response.json()
    assignments_payload = assignments_response.json()
    missions_payload = missions_response.json()
    mission_detail_payload = mission_detail_response.json()

    assert networks_payload[0]["id"] == network_id
    assert networks_payload[0]["network_name"] == "Wonderkid Radar"
    assert assignments_payload[0]["id"] == assignment_id
    assert assignments_payload[0]["territory_code"] == "lagos"
    assert missions_payload[0]["id"] == mission_id
    assert missions_payload[0]["status"] == "completed"
    assert mission_detail_payload["mission"]["id"] == mission_id
    assert len(mission_detail_payload["reports"]) == 1
    assert len(mission_detail_payload["hidden_potential_estimates"]) == 1
    assert mission_detail_payload["academy_supply_signals"][0]["candidate_count"] == 1
    assert {badge["badge_code"] for badge in mission_detail_payload["awarded_badges"]} >= {
        "academy_visionary",
        "talent_discoverer",
        "wonderkid_finder",
    }


def test_scouting_intelligence_read_endpoints_require_club_owner(
    client: TestClient,
    session: Session,
    create_club,
) -> None:
    club = create_club(slug="scouting-intelligence-ownership")
    _seed_scouting_intelligence(session, club["id"])

    client.app.state.current_user_id = "user-other"
    response = client.get(f"/api/clubs/{club['id']}/scouting-intelligence/networks")

    assert response.status_code == 403
    assert response.json()["detail"] == "club_owner_required"
