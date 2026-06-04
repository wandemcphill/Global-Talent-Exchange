from __future__ import annotations

from app.live_matches.router import _sample_viewer_frame
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.services.match_timeline_service import MatchTimelineService
from backend.tests.match_engine.helpers import build_request


def _find_motion_window():
    simulation_service = MatchSimulationService()
    timeline_service = MatchTimelineService()

    for seed in range(1, 80):
        replay_payload = simulation_service.build_replay_payload(build_request(seed=seed))
        view_state = timeline_service.build_from_replay_payload(replay_payload)

        for previous_frame, next_frame in zip(view_state.frames, view_state.frames[1:]):
            if next_frame.time_seconds <= previous_frame.time_seconds:
                continue

            moving_player_id = None
            next_players_by_id = {player.player_id: player for player in next_frame.players}
            for player in previous_frame.players:
                next_player = next_players_by_id.get(player.player_id)
                if next_player is None:
                    continue
                if (
                    abs(player.position.x - next_player.position.x) > 0.01
                    or abs(player.position.y - next_player.position.y) > 0.01
                ):
                    moving_player_id = player.player_id
                    break

            ball_moved = (
                abs(previous_frame.ball.position.x - next_frame.ball.position.x) > 0.01
                or abs(previous_frame.ball.position.y - next_frame.ball.position.y) > 0.01
            )

            if moving_player_id is not None or ball_moved:
                return view_state, previous_frame, next_frame, moving_player_id, ball_moved

    raise AssertionError("No live motion window was found across the replay seeds.")


def test_interpolated_viewer_frame_interpolates_live_motion_between_timeline_frames() -> None:
    view_state, previous_frame, next_frame, moving_player_id, ball_moved = _find_motion_window()
    sample_time_seconds = round((previous_frame.time_seconds + next_frame.time_seconds) / 2.0, 2)

    sampled_frame = _sample_viewer_frame(view_state, sample_time_seconds)

    assert sampled_frame.frame_id.endswith(f":interpolated:{int(round(sample_time_seconds * 100))}")
    assert sampled_frame.time_seconds == sample_time_seconds
    assert previous_frame.clock_minute <= sampled_frame.clock_minute <= next_frame.clock_minute
    assert sampled_frame.frame_id not in {previous_frame.frame_id, next_frame.frame_id}

    if moving_player_id is not None:
        previous_player = next(player for player in previous_frame.players if player.player_id == moving_player_id)
        next_player = next(player for player in next_frame.players if player.player_id == moving_player_id)
        sampled_player = next(player for player in sampled_frame.players if player.player_id == moving_player_id)

        assert (
            min(previous_player.position.x, next_player.position.x)
            <= sampled_player.position.x
            <= max(previous_player.position.x, next_player.position.x)
        )
        assert (
            min(previous_player.position.y, next_player.position.y)
            <= sampled_player.position.y
            <= max(previous_player.position.y, next_player.position.y)
        )
        assert (
            abs(sampled_player.position.x - previous_player.position.x) > 0.001
            or abs(sampled_player.position.y - previous_player.position.y) > 0.001
        )

    if ball_moved:
        assert (
            min(previous_frame.ball.position.x, next_frame.ball.position.x)
            <= sampled_frame.ball.position.x
            <= max(previous_frame.ball.position.x, next_frame.ball.position.x)
        )
        assert (
            min(previous_frame.ball.position.y, next_frame.ball.position.y)
            <= sampled_frame.ball.position.y
            <= max(previous_frame.ball.position.y, next_frame.ball.position.y)
        )
        assert (
            abs(sampled_frame.ball.position.x - previous_frame.ball.position.x) > 0.001
            or abs(sampled_frame.ball.position.y - previous_frame.ball.position.y) > 0.001
        )
