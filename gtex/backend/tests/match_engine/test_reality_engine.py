from __future__ import annotations

from app.match_engine.reality_engine.event_engine import ShotProfile
from app.match_engine.reality_engine.roles import resolve_role_profile
from app.match_engine.reality_engine.xg_model import XGModel
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import InternalPlayer, MatchEventType, PlayerRole
from backend.tests.match_engine.helpers import build_request


def _player(
    *,
    player_id: str,
    role: PlayerRole,
    archetype: str,
    overall: int = 80,
    finishing: int = 80,
    creativity: int = 70,
    defending: int = 50,
    goalkeeping: int = 5,
) -> InternalPlayer:
    return InternalPlayer(
        player_id=player_id,
        player_name=player_id,
        role=role,
        overall=overall,
        finishing=finishing,
        creativity=creativity,
        defending=defending,
        goalkeeping=goalkeeping,
        discipline=70,
        fitness=76,
        position_archetype=archetype,
        composure=78,
        decision_making=76,
        positioning=77,
        off_ball_movement=78,
        aerial_ability=72,
        technique=79,
    )


def test_role_profiles_bias_finisher_and_creator_differently() -> None:
    poacher = _player(
        player_id="poacher",
        role=PlayerRole.FORWARD,
        archetype="poacher",
        finishing=86,
        creativity=58,
    )
    playmaker = _player(
        player_id="playmaker",
        role=PlayerRole.MIDFIELDER,
        archetype="deep_playmaker",
        finishing=68,
        creativity=88,
    )

    poacher_profile = resolve_role_profile(poacher)
    playmaker_profile = resolve_role_profile(playmaker)

    assert poacher_profile.shot_volume > playmaker_profile.shot_volume
    assert poacher_profile.shot_quality > playmaker_profile.shot_quality
    assert playmaker_profile.chance_creation > poacher_profile.chance_creation
    assert playmaker_profile.buildup > poacher_profile.buildup


def test_xg_model_rewards_high_value_chances_over_long_range_pressure() -> None:
    model = XGModel()
    shooter = _player(
        player_id="finisher",
        role=PlayerRole.FORWARD,
        archetype="poacher",
        finishing=90,
        creativity=66,
    )
    keeper = _player(
        player_id="keeper",
        role=PlayerRole.GOALKEEPER,
        archetype="shot_stopper",
        overall=82,
        finishing=10,
        creativity=35,
        defending=55,
        goalkeeping=88,
    )
    cutback = ShotProfile(
        shot_type="cutback",
        route="wide_overlap",
        distance=11.5,
        angle=0.78,
        pressure=0.24,
        defender_proximity=0.22,
        goalkeeper_positioning=0.52,
        transition_speed=0.64,
        body_part="foot",
        is_set_piece=False,
        assisted=True,
    )
    long_range = ShotProfile(
        shot_type="long_range_effort",
        route="central_combine",
        distance=24.0,
        angle=0.21,
        pressure=0.58,
        defender_proximity=0.62,
        goalkeeper_positioning=0.58,
        transition_speed=0.30,
        body_part="foot",
        is_set_piece=False,
        assisted=False,
    )

    assert model.calculate_xg(cutback, shooter=shooter, keeper=keeper) > model.calculate_xg(
        long_range,
        shooter=shooter,
        keeper=keeper,
    )


def test_replay_payload_exposes_reality_engine_shot_metadata() -> None:
    service = MatchSimulationService()

    payload = None
    for seed in range(1, 30):
        candidate = service.build_replay_payload(build_request(seed=seed))
        if any(event.event_type is MatchEventType.SHOT for event in candidate.timeline.events):
            payload = candidate
            break

    assert payload is not None

    shot_event = next(event for event in payload.timeline.events if event.event_type is MatchEventType.SHOT)
    assert 0.0 < float(shot_event.metadata["xg"]) < 1.0
    assert shot_event.metadata["possession_route"] in {
        "transition",
        "central_combine",
        "wide_overlap",
        "set_piece",
        "press_break",
    }
    assert shot_event.metadata["shot_body_part"] in {"foot", "header", "volley", "weak_foot"}
    assert float(shot_event.metadata["shot_distance"]) > 0.0
    assert 0.0 < float(shot_event.metadata["shot_angle"]) <= 1.0
