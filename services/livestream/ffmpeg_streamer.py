from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from services.livestream.composer import StreamSegment


@dataclass(frozen=True, slots=True)
class FFmpegStreamConfig:
    rtmp_url: str
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    preset: str = "veryfast"
    audio_bitrate: str = "128k"
    output_format: str = "flv"


def build_concat_playlist(entries: Sequence[StreamSegment]) -> str:
    lines: list[str] = []
    for entry in entries:
        safe_path = Path(entry.path).as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
    return "\n".join(lines) + ("\n" if lines else "")


def build_ffmpeg_command(config: FFmpegStreamConfig, *, playlist_path: str) -> list[str]:
    return [
        "ffmpeg",
        "-re",
        "-stream_loop",
        "-1",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        playlist_path,
        "-c:v",
        config.video_codec,
        "-preset",
        config.preset,
        "-c:a",
        config.audio_codec,
        "-b:a",
        config.audio_bitrate,
        "-f",
        config.output_format,
        config.rtmp_url,
    ]
