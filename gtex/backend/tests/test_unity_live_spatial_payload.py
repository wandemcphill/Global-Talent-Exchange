from __future__ import annotations

from types import SimpleNamespace

from app.live_matches.router import _unity_ball_payload


def _frame(ball: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        ball=ball,
    )


def _ball(*, velocity: SimpleNamespace | None, spin: SimpleNamespace | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        owner_player_id=None,
        position=SimpleNamespace(x=50.0, y=50.0),
        height=0.05,
        state="rolling",
        velocity=velocity,
        spin=spin,
    )


def test_stationary_ball_payload_is_truly_stationary() -> None:
    ball = _unity_ball_payload(_frame(_ball(velocity=SimpleNamespace(x=0.0, y=0.0, z=0.0))), None, {})

    assert ball["speedRatio"] == 0.0
    assert ball["velocityX"] == 0.0
    assert ball["velocityY"] == 0.0
    assert ball["velocityZ"] == 0.0
    assert ball["facingX"] == 0.0
    assert ball["facingZ"] == 0.0


def test_moving_ball_payload_derives_speed_and_facing_from_velocity() -> None:
    ball = _unity_ball_payload(
        _frame(_ball(velocity=SimpleNamespace(x=6.0, y=0.0, z=8.0))),
        None,
        {},
    )

    assert ball["speedRatio"] > 0.0
    assert ball["velocityX"] == 6.0
    assert ball["velocityZ"] == 8.0
    assert ball["facingX"] == 0.6
    assert ball["facingZ"] == 0.8
