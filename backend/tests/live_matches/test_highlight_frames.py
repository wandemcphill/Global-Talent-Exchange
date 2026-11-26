from types import SimpleNamespace

from app.live_matches.router import _frames_for_open_chance


def _frame(stamp: float, rate: float = 1.0) -> SimpleNamespace:
    return SimpleNamespace(time_seconds=stamp, playback_rate=rate)


def test_open_play_has_no_picture_and_a_chance_includes_the_move() -> None:
    frames = [_frame(stamp) for stamp in (30, 34, 38, 41.5, 44, 50, 60)]
    frames[3].playback_rate = 0.45
    shot = SimpleNamespace(event_id="shot-1", event_type="shot", time_seconds=44.0)

    assert _frames_for_open_chance(frames, frames[2], None) == []

    buildup = _frames_for_open_chance(frames, frames[3], shot)
    assert [item.time_seconds for item in buildup] == [38, 41.5, 44]

    finish = _frames_for_open_chance(frames, frames[4], shot)
    assert [item.time_seconds for item in finish] == [38, 41.5, 44]

    # The clock has moved on, but the next poll can still fetch the same move.
    late = _frames_for_open_chance(frames, frames[5], None, [shot])
    assert [item.time_seconds for item in late] == [38, 41.5, 44]

    assert _frames_for_open_chance(frames, frames[6], None, [shot]) == []
