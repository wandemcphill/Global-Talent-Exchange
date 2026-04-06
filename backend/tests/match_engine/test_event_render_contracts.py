from __future__ import annotations

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType, PlayerRole
from app.schemas.match_viewer import MatchViewerCameraPreset, MatchViewerEventType
from app.services.match_timeline_service import MatchTimelineService
from backend.tests.match_engine.helpers import build_request


def _find_payload(predicate, *, seeds=range(1, 240)):
    service = MatchSimulationService()
    for seed in seeds:
        payload = service.build_replay_payload(build_request(seed=seed))
        if predicate(payload):
            return payload
    raise AssertionError("No payload satisfied the requested predicate within the seed range")


def test_replay_payload_includes_renderer_ready_contracts() -> None:
    payload = _find_payload(
        lambda replay: any(event.event_type is MatchEventType.GOAL for event in replay.timeline.events)
    )

    goal_event = next(event for event in payload.timeline.events if event.event_type is MatchEventType.GOAL)
    render = goal_event.metadata.get("render")

    assert isinstance(render, dict)
    assert render["type"] == "goal"
    assert render["camera"]["mode"] == "goal_camera"
    assert render["camera"]["freeze_frame"] is True
    assert render["replay"]["eligible"] is True
    assert 0 <= render["origin"]["x"] <= 100
    assert 0 <= render["origin"]["y"] <= 100
    assert 0 <= render["target"]["x"] <= 100
    assert 0 <= render["target"]["y"] <= 100
    assert render["ball"]["motion"] in {"shot", "cross", "pass", "lob"}
    assert payload.scene_assembly is not None
    assert payload.scene_assembly.scene_version == "v2"
    assert payload.scene_assembly.event_render_mode == "event_driven"
    assert "goal_camera" in payload.scene_assembly.camera_modes


def test_position_aware_ratings_are_attached_to_summary_and_halftime() -> None:
    payload = _find_payload(
        lambda replay: any(event.event_type is MatchEventType.GOAL for event in replay.timeline.events)
    )

    scorer_id = next(
        event.primary_player.player_id
        for event in payload.timeline.events
        if event.event_type is MatchEventType.GOAL and event.primary_player is not None
    )
    scorer_stats = next(player for player in payload.summary.player_stats if player.player_id == scorer_id)

    assert scorer_stats.rating is not None
    assert scorer_stats.rating >= 6.2
    assert scorer_stats.rating_summary is not None
    assert "goal" in scorer_stats.rating_summary.lower()
    assert payload.halftime_analytics is not None
    assert payload.halftime_analytics.player_ratings
    assert all(player.summary for player in payload.halftime_analytics.player_ratings)

    goalkeepers = [player for player in payload.summary.player_stats if player.role is PlayerRole.GOALKEEPER]
    assert goalkeepers
    assert all(player.rating is not None for player in goalkeepers)


def test_viewer_timeline_consumes_render_contract_for_camera_and_ball_states() -> None:
    payload = _find_payload(
        lambda replay: any(event.event_type is MatchEventType.GOAL for event in replay.timeline.events)
    )
    view_state = MatchTimelineService().build_from_replay_payload(payload)

    goal_event = next(event for event in view_state.events if event.event_type is MatchViewerEventType.GOAL)
    goal_frames = [frame for frame in view_state.frames if frame.active_event_id == goal_event.event_id]

    assert goal_frames
    assert any(frame.camera_preset in {MatchViewerCameraPreset.BOX_ZOOM, MatchViewerCameraPreset.GOAL_CELEBRATION} for frame in goal_frames)
    assert any(frame.ball.state in {"shot", "cross", "lob"} for frame in goal_frames)
    assert any(frame.playback_rate <= 0.5 for frame in goal_frames)
    assert any(frame.pressure_index > 0.0 for frame in goal_frames)
    assert any(
        player.animation_state.value in {"shoot", "celebrate", "run", "sprint"}
        for frame in goal_frames
        for player in frame.players
    )


def test_render_contract_exposes_trajectory_spin_and_viewer_ball_height() -> None:
    payload = _find_payload(
        lambda replay: any(
            event.event_type in {MatchEventType.GOAL, MatchEventType.MISSED_BIG_CHANCE, MatchEventType.GOALKEEPER_SAVE}
            for event in replay.timeline.events
        )
    )
    source_event = next(
        event
        for event in payload.timeline.events
        if event.event_type in {MatchEventType.GOAL, MatchEventType.MISSED_BIG_CHANCE, MatchEventType.GOALKEEPER_SAVE}
    )
    render = source_event.metadata.get("render") or {}
    ball = render.get("ball") or {}

    assert isinstance(ball.get("trajectory"), list)
    assert ball["trajectory"]
    assert all({"x", "y", "z", "t"} <= set(point) for point in ball["trajectory"])
    assert set(ball.get("spin", {})) == {"x", "y", "z"}
    assert set(ball.get("velocity", {})) == {"x", "y", "z"}

    view_state = MatchTimelineService().build_from_replay_payload(payload)
    event_frames = [frame for frame in view_state.frames if frame.active_event_id == source_event.event_id]

    assert event_frames
    assert any(frame.ball.height >= 0.0 for frame in event_frames)
    assert any(frame.ball.spin is not None for frame in event_frames)


def test_render_sync_exposes_motion_commentary_crowd_and_spectator_layers() -> None:
    payload = _find_payload(
        lambda replay: any(
            event.event_type in {MatchEventType.GOAL, MatchEventType.SHOT, MatchEventType.MISSED_BIG_CHANCE}
            for event in replay.timeline.events
        )
    )

    assert payload.scene_assembly is not None
    assert payload.scene_assembly.motion_runtime == "onnx_runtime_blend_inference"
    assert payload.scene_assembly.commentary_runtime == "llm_template_tts_stack"
    assert payload.scene_assembly.crowd_reactivity == "event_weighted_pressure_feedback"
    assert payload.scene_assembly.spectator_sync_mode == "deterministic_playback"

    assert payload.broadcast_presentation is not None
    assert payload.broadcast_presentation.tts_enabled is True
    assert "lead" in payload.broadcast_presentation.commentator_roles
    assert "en" in payload.broadcast_presentation.commentary_languages

    assert payload.spectator_package is not None
    assert payload.spectator_package.sync_strategy == "deterministic_playback"
    assert payload.spectator_package.watch_party_enabled is True
    assert payload.spectator_package.reactions_enabled is True
    assert payload.spectator_package.chat_enabled is True

    assert payload.render_sync is not None
    event = next(item for item in payload.render_sync.events if item.experience is not None)
    experience = event.experience

    assert experience is not None
    assert experience.motion is not None
    assert experience.motion.model_key == "gtex_motion_blend_v1"
    assert round(
        experience.motion.run_weight + experience.motion.sprint_weight + experience.motion.shoot_weight,
        3,
    ) == 1.0
    assert -1.0 <= experience.motion.direction.x <= 1.0
    assert -1.0 <= experience.motion.direction.y <= 1.0

    assert experience.commentary is not None
    assert experience.commentary.line
    assert experience.commentary.tts_ready is True

    assert experience.crowd is not None
    assert 0.0 <= experience.crowd.home_intensity <= 1.0
    assert 0.0 <= experience.crowd.away_intensity <= 1.0

    assert experience.spectator_sync is not None
    assert experience.spectator_sync.room_id == f"match_{payload.match_id}"
    assert experience.spectator_sync.sync_strategy == "deterministic_playback"
