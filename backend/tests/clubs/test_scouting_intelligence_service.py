from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from backend.app.ingestion.models import Player
from backend.app.models.regen import AcademyCandidate, AcademyIntakeBatch, RegenProfile
from backend.app.models.scouting_intelligence import HiddenPotentialEstimate, ScoutMission, ScoutingNetwork, TalentDiscoveryBadge
from backend.app.schemas.club_requests import ClubCreateRequest
from backend.app.services.club_branding_service import ClubBrandingService
from backend.app.services.scouting_intelligence_service import (
    ManagerProfileUpsert,
    ScoutMissionCreate,
    ScoutingIntelligenceService,
    ScoutingNetworkAssignmentCreate,
    ScoutingNetworkCreate,
)


def _create_club(session, *, slug: str) -> object:
    return ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Harbor FC",
                "short_name": "HFC",
                "slug": slug,
                "primary_color": "#114477",
                "secondary_color": "#ffffff",
                "accent_color": "#ff9900",
                "country_code": "NG",
                "region_name": "Lagos",
                "city_name": "Lagos",
                "visibility": "public",
            }
        ),
    )


def _starter_regens(session, club_id: str) -> list[RegenProfile]:
    return session.scalars(
        select(RegenProfile).where(RegenProfile.generated_for_club_id == club_id).order_by(RegenProfile.regen_id)
    ).all()


def _player_for_regen(session, regen: RegenProfile) -> Player:
    player = session.get(Player, regen.player_id)
    assert player is not None
    return player


def _set_profile_window(
    session,
    regen: RegenProfile,
    *,
    age: int,
    current_min: int,
    current_max: int,
    potential_min: int,
    potential_max: int,
    position: str | None = None,
    generation_source: str | None = None,
) -> None:
    player = _player_for_regen(session, regen)
    player.date_of_birth = date.today() - timedelta(days=age * 365)
    regen.current_ability_range_json = {"minimum": current_min, "maximum": current_max}
    regen.potential_range_json = {"minimum": potential_min, "maximum": potential_max}
    regen.current_gsi = current_max
    if position is not None:
        regen.primary_position = position
        player.position = position
        player.normalized_position = "forward"
    if generation_source is not None:
        regen.generation_source = generation_source
    session.flush()


def _add_academy_candidate(session, club_id: str, regen: RegenProfile, *, season_label: str = "2025/26") -> AcademyCandidate:
    batch = AcademyIntakeBatch(
        club_id=club_id,
        season_label=season_label,
        intake_size=1,
        academy_quality_score=82.0,
        status="generated",
        metadata_json={"source": "test"},
    )
    session.add(batch)
    session.flush()
    candidate = AcademyCandidate(
        batch_id=batch.id,
        club_id=club_id,
        regen_profile_id=regen.id,
        display_name=_player_for_regen(session, regen).full_name,
        age=17,
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


def test_scouting_network_creation_persists_region_and_cost(session) -> None:
    club = _create_club(session, slug="thread-a-network")
    service = ScoutingIntelligenceService(session)
    manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club.id,
            manager_code="mgr-youth",
            manager_name="Youth Coach",
            persona_code="Youth Developer",
        )
    )

    network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=manager.id,
            network_name="West Africa Watch",
            region_code="west_africa",
            region_name="West Africa",
            specialty_code="youth",
            quality_tier="elite",
            weekly_cost_coin=1400,
        )
    )
    assignment = service.assign_network(
        ScoutingNetworkAssignmentCreate(
            network_id=network.id,
            club_id=club.id,
            assignment_name="U20 Lagos scan",
            territory_code="lagos",
            focus_position="ST",
            age_band_min=16,
            age_band_max=20,
            budget_profile="value",
        )
    )

    assert network.region_code == "west_africa"
    assert network.weekly_cost_coin == 1400
    assert assignment.territory_code == "lagos"
    assert session.scalar(select(ScoutingNetwork).where(ScoutingNetwork.id == network.id)) is not None


def test_scout_mission_execution_persists_reports_and_hidden_potential(session) -> None:
    club = _create_club(session, slug="thread-a-mission")
    regen = _starter_regens(session, club.id)[0]
    _set_profile_window(
        session,
        regen,
        age=18,
        current_min=68,
        current_max=72,
        potential_min=88,
        potential_max=93,
        position="ST",
    )
    service = ScoutingIntelligenceService(session)
    manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club.id,
            manager_code="mgr-balance",
            manager_name="Chief Scout",
            persona_code="balanced",
        )
    )
    network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=manager.id,
            network_name="Wonderkid Radar",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="wonderkid",
            quality_tier="advanced",
            weekly_cost_coin=900,
        )
    )
    mission = service.create_mission(
        ScoutMissionCreate(
            club_id=club.id,
            network_id=network.id,
            manager_profile_id=manager.id,
            mission_name="Find immediate upside",
            mission_type="deep_talent_search",
            target_position="ST",
            target_region="lagos",
            target_age_max=20,
            talent_type="wonderkid",
        )
    )

    completed = service.complete_mission(mission.id, limit=1)

    assert completed.mission.status == "completed"
    assert len(completed.reports) == 1
    assert len(completed.hidden_potential_estimates) == 1
    assert completed.reports[0].confidence_bps >= 7000
    assert completed.hidden_potential_estimates[0].future_potential_high >= completed.reports[0].future_potential_estimate
    assert session.scalar(select(ScoutMission).where(ScoutMission.id == mission.id)).status == "completed"


def test_hidden_potential_uncertainty_and_accuracy_improve_with_better_scouts(session) -> None:
    club = _create_club(session, slug="thread-a-uncertainty")
    regen = _starter_regens(session, club.id)[0]
    _set_profile_window(
        session,
        regen,
        age=18,
        current_min=67,
        current_max=71,
        potential_min=89,
        potential_max=94,
        position="ST",
    )
    service = ScoutingIntelligenceService(session)
    manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club.id,
            manager_code="mgr-youth",
            manager_name="Youth Analyst",
            persona_code="youth_developer",
        )
    )
    low_network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=manager.id,
            network_name="Budget Scout",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="value",
            quality_tier="standard",
            weekly_cost_coin=400,
        )
    )
    high_network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=manager.id,
            network_name="Elite Scout",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="value",
            quality_tier="elite",
            weekly_cost_coin=1800,
        )
    )
    low_mission = service.create_mission(
        ScoutMissionCreate(
            club_id=club.id,
            network_id=low_network.id,
            manager_profile_id=manager.id,
            mission_name="Budget look",
            target_position="ST",
            target_region="lagos",
            target_age_max=20,
        )
    )
    high_mission = service.create_mission(
        ScoutMissionCreate(
            club_id=club.id,
            network_id=high_network.id,
            manager_profile_id=manager.id,
            mission_name="Elite look",
            mission_type="deep_talent_search",
            target_position="ST",
            target_region="lagos",
            target_age_max=20,
        )
    )

    low_result = service.complete_mission(low_mission.id, limit=1)
    high_result = service.complete_mission(high_mission.id, limit=1)
    actual_current = 69
    actual_potential = 92
    low_report = low_result.reports[0]
    high_report = high_result.reports[0]
    low_estimate = low_result.hidden_potential_estimates[0]
    high_estimate = high_result.hidden_potential_estimates[0]
    low_error = abs(low_report.current_ability_estimate - actual_current) + abs(low_report.future_potential_estimate - actual_potential)
    high_error = abs(high_report.current_ability_estimate - actual_current) + abs(high_report.future_potential_estimate - actual_potential)

    assert high_estimate.uncertainty_band < low_estimate.uncertainty_band
    assert high_error <= low_error


def test_manager_personas_rank_different_targets(session) -> None:
    club = _create_club(session, slug="thread-a-manager-personas")
    youth_target, star_target = _starter_regens(session, club.id)
    _set_profile_window(
        session,
        youth_target,
        age=18,
        current_min=66,
        current_max=70,
        potential_min=90,
        potential_max=94,
        position="ST",
    )
    _set_profile_window(
        session,
        star_target,
        age=27,
        current_min=82,
        current_max=86,
        potential_min=86,
        potential_max=89,
        position="ST",
    )
    star_target.is_special_lineage = True
    session.flush()

    service = ScoutingIntelligenceService(session)
    youth_manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club.id,
            manager_code="mgr-youth",
            manager_name="Youth Lead",
            persona_code="youth_developer",
        )
    )
    star_manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club.id,
            manager_code="mgr-star",
            manager_name="Star Lead",
            persona_code="star_recruiter",
        )
    )
    youth_network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=youth_manager.id,
            network_name="Youth Net",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="youth",
            quality_tier="elite",
            weekly_cost_coin=1000,
        )
    )
    star_network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=star_manager.id,
            network_name="Star Net",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="star",
            quality_tier="elite",
            weekly_cost_coin=1000,
        )
    )

    youth_result = service.complete_mission(
        service.create_mission(
            ScoutMissionCreate(
                club_id=club.id,
                network_id=youth_network.id,
                manager_profile_id=youth_manager.id,
                mission_name="Youth shortlist",
                target_position="ST",
            )
        ).id,
        limit=1,
    )
    star_result = service.complete_mission(
        service.create_mission(
            ScoutMissionCreate(
                club_id=club.id,
                network_id=star_network.id,
                manager_profile_id=star_manager.id,
                mission_name="Star shortlist",
                target_position="ST",
            )
        ).id,
        limit=1,
    )

    assert youth_result.reports[0].regen_profile_id == youth_target.id
    assert star_result.reports[0].regen_profile_id == star_target.id


def test_academy_supply_visibility_and_badges(session) -> None:
    club = _create_club(session, slug="thread-a-academy")
    academy_regen = _starter_regens(session, club.id)[0]
    _set_profile_window(
        session,
        academy_regen,
        age=17,
        current_min=61,
        current_max=65,
        potential_min=86,
        potential_max=91,
        position="ST",
        generation_source="academy",
    )
    academy_candidate = _add_academy_candidate(session, club.id, academy_regen)

    service = ScoutingIntelligenceService(session)
    manager = service.upsert_manager_profile(
        ManagerProfileUpsert(
            club_id=club.id,
            manager_code="mgr-academy",
            manager_name="Academy Lead",
            persona_code="youth_developer",
        )
    )
    network = service.create_network(
        ScoutingNetworkCreate(
            club_id=club.id,
            manager_profile_id=manager.id,
            network_name="Academy Net",
            region_code="ng",
            region_name="Nigeria",
            specialty_code="academy",
            quality_tier="elite",
            weekly_cost_coin=1200,
        )
    )
    mission = service.create_mission(
        ScoutMissionCreate(
            club_id=club.id,
            network_id=network.id,
            manager_profile_id=manager.id,
            mission_name="Academy visibility",
            mission_type="deep_talent_search",
            target_position="ST",
            target_region="lagos",
            target_age_max=19,
            include_academy=True,
            talent_type="wonderkid",
        )
    )

    completed = service.complete_mission(mission.id, limit=1)

    assert completed.academy_supply_signals[0].candidate_count == 1
    assert completed.academy_supply_signals[0].visibility_score > 0
    assert any(badge.badge_code in {"academy_visionary", "wonderkid_finder"} for badge in completed.awarded_badges)
    assert session.scalar(select(AcademyCandidate).where(AcademyCandidate.id == academy_candidate.id)) is not None
    assert session.scalar(select(TalentDiscoveryBadge).where(TalentDiscoveryBadge.regen_profile_id == academy_regen.id)) is not None
    assert session.scalar(
        select(HiddenPotentialEstimate).where(HiddenPotentialEstimate.academy_candidate_id == academy_candidate.id)
    ) is not None
