from __future__ import annotations

from services.livestream import (
    FFmpegStreamConfig,
    LivestreamScheduler,
    build_concat_playlist,
    build_ffmpeg_command,
    build_playlist,
    compose_highlight_segment,
    compose_match_segment,
    compose_studio_segment,
)


def test_playlist_builder_and_ffmpeg_command_shape() -> None:
    match = compose_match_segment(
        {
            "match_id": "match_1",
            "home_club_name": "Lagos Titans",
            "away_club_name": "Abuja Storm",
            "home_goals": 3,
            "away_goals": 2,
            "video_path": "generated/match_1/full.mp4",
            "duration_seconds": 900,
        }
    )
    highlight = compose_highlight_segment({"clip_id": "clip_1", "title": "Chaos reel", "video_path": "generated/clip_1.mp4"})
    debate = compose_studio_segment(kind="debate", title="Pundit Desk", path="studio/debate.mp4", duration_seconds=240)
    ad = compose_studio_segment(kind="ad", title="Brand Spot", path="ads/spot.mp4", duration_seconds=30)

    playlist = build_playlist([match], [highlight], [debate], [ad], sponsor_interval=2)
    manifest = build_concat_playlist(playlist)
    command = build_ffmpeg_command(
        FFmpegStreamConfig(rtmp_url="rtmp://live.youtube.com/app/demo-key"),
        playlist_path="playlist.txt",
    )

    assert [segment.kind for segment in playlist] == ["match", "highlight", "ad", "debate"]
    assert "generated/match_1/full.mp4" in manifest
    assert command[:8] == ["ffmpeg", "-re", "-stream_loop", "-1", "-f", "concat", "-safe", "0"]
    assert command[-1] == "rtmp://live.youtube.com/app/demo-key"


def test_livestream_scheduler_builds_continuous_window() -> None:
    segments = [
        compose_studio_segment(kind="match", title="Match A", path="a.mp4", duration_seconds=90),
        compose_studio_segment(kind="highlight", title="Highlights", path="b.mp4", duration_seconds=45),
    ]
    scheduler = LivestreamScheduler(segments)

    window = scheduler.build_window(minimum_duration_seconds=220)

    assert window.total_duration_seconds >= 220
    assert len(window.segments) >= 3
