from __future__ import annotations

import subprocess
from pathlib import Path


def build_overlay_command(
    video_path: str,
    text: str,
    *,
    output_path: str = "output.mp4",
    x: int = 10,
    y: int = 10,
    font_size: int = 24,
    font_color: str = "white",
) -> list[str]:
    escaped_text = _escape_drawtext(text)
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(Path(video_path)),
        "-vf",
        f"drawtext=text='{escaped_text}':x={x}:y={y}:fontsize={font_size}:fontcolor={font_color}",
        "-codec:a",
        "copy",
        str(Path(output_path)),
    ]


def inject_overlay(
    video_path: str,
    text: str,
    *,
    output_path: str = "output.mp4",
    execute: bool = False,
    check: bool = False,
) -> list[str]:
    command = build_overlay_command(
        video_path,
        text,
        output_path=output_path,
    )
    if execute:
        subprocess.run(command, check=check)
    return command


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
    )


__all__ = ["build_overlay_command", "inject_overlay"]
