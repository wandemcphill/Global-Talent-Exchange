from __future__ import annotations

from app.services.squad_assignment_service import SquadAssignmentService


def test_winger_profile_is_formation_ready_with_secondary_options() -> None:
    profile = SquadAssignmentService().build_profile(
        player_id="player-winger",
        primary_position="Winger",
        normalized_position="forward",
        preferred_foot="right",
        age=21,
        current_club_id="club-1",
    )

    assert profile.formation_ready is True
    assert "RW" in profile.formation_slots
    assert "LW" in profile.formation_slots
    assert profile.role_archetype in {"inverted_winger", "touchline_winger", "inside_forward"}
    assert profile.squad_eligibility["first_team"] is True
    assert set(profile.secondary_positions).issubset({"Striker", "Attacking Midfielder"})


def test_free_agent_profile_routes_into_free_agent_pool() -> None:
    profile = SquadAssignmentService().build_profile(
        player_id="player-free-agent",
        primary_position="Full-Back",
        normalized_position="defender",
        preferred_foot="left",
        age=18,
        current_club_id=None,
    )

    assert profile.formation_ready is True
    assert "LB" in profile.formation_slots
    assert profile.squad_eligibility["free_agent_pool"] is True
    assert profile.squad_eligibility["first_team"] is False
