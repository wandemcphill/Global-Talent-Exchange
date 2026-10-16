from __future__ import annotations

from app.viral.analytics import ViralFeedbackLoopService, track_clip


def test_track_clip_normalizes_core_metrics() -> None:
    tracked = track_clip(
        "clip-101",
        {
            "views": 200,
            "watch_time": 9.5,
            "loops": 48,
            "shares": 14,
            "comments": 9,
            "completion": 82,
            "drop_off_point_seconds": 11.0,
        },
    )

    assert tracked["clip_id"] == "clip-101"
    assert tracked["view_count"] == 200
    assert tracked["completions"] == 164
    assert tracked["watch_time"] == 9.5
    assert tracked["total_watch_time"] == 1900.0
    assert tracked["loops"] == 48.0
    assert tracked["loop_rate"] == 0.24
    assert tracked["skips"] == 36
    assert tracked["completion_rate"] == 0.82
    assert tracked["share_rate"] == 0.07
    assert tracked["comment_rate"] == 0.045


def test_feedback_service_promotes_high_retention_clips() -> None:
    feedback = ViralFeedbackLoopService().analyze_clip(
        clip_id="clip-viral",
        metrics={
            "views": 1000,
            "watch_time": 13.2,
            "loops": 240,
            "shares": 52,
            "comments": 19,
            "completion": 0.88,
            "drop_off_point_seconds": 12.0,
        },
        clip_context={
            "title": "Late winner",
            "duration_seconds": 13,
            "crowd_spike": True,
            "late_drama": True,
            "upset": True,
            "is_final": False,
        },
    )

    assert feedback.performance_tier == "high_retention"
    assert feedback.increase_similar_clips is True
    assert feedback.shorten_clips is False
    assert feedback.viral_analysis
