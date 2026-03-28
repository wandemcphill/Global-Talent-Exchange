from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
from typing import Any, Protocol

from app.highlights.queue import HighlightRenderJob


def _resolve_storage_path(storage_root: Path, storage_key: str) -> Path:
    normalized = PurePosixPath(storage_key.strip().lstrip("/"))
    if not normalized.parts or any(part in {"", ".", ".."} for part in normalized.parts):
        raise ValueError(f"Invalid storage key: {storage_key}")
    path = (storage_root / normalized).resolve()
    root = storage_root.resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("Storage key resolved outside storage root.")
    return path


class HighlightRenderer(Protocol):
    def render(self, job: HighlightRenderJob, *, output_path: Path, storage_root: Path) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class FFmpegHighlightRenderer:
    binary: str = "ffmpeg"

    def render(self, job: HighlightRenderJob, *, output_path: Path, storage_root: Path) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if job.kind == "reel":
            clip_paths: list[Path] = []
            for storage_key in job.source_clip_storage_keys:
                path = _resolve_storage_path(storage_root, storage_key)
                if path.exists():
                    clip_paths.append(path)
            if clip_paths and len(clip_paths) == len(job.source_clip_storage_keys):
                self._run(self._concat_command(clip_paths=clip_paths, output_path=output_path))
                return {"renderer": "ffmpeg", "mode": "concat_reel", "clip_count": len(clip_paths)}

        source_path = self._resolve_source_path(job=job, storage_root=storage_root)
        if source_path is not None and source_path.exists():
            self._run(self._clip_command(job=job, source_path=source_path, output_path=output_path))
            return {"renderer": "ffmpeg", "mode": "source_clip", "source_path": str(source_path)}

        self._run(self._placeholder_command(job=job, output_path=output_path))
        return {"renderer": "ffmpeg", "mode": "placeholder"}

    def _resolve_source_path(self, *, job: HighlightRenderJob, storage_root: Path) -> Path | None:
        if job.source_path:
            return Path(job.source_path)
        if job.source_storage_key:
            return _resolve_storage_path(storage_root, job.source_storage_key)
        return None

    def _clip_command(self, *, job: HighlightRenderJob, source_path: Path, output_path: Path) -> list[str]:
        duration_seconds = max(1, int(job.duration_seconds))
        command = [self.binary, "-y"]
        if job.start_second is not None:
            command.extend(["-ss", self._seconds(job.start_second)])
        command.extend(["-i", str(source_path), "-t", self._seconds(duration_seconds)])
        if job.playback_speed is not None and job.playback_speed > 0 and abs(job.playback_speed - 1.0) > 0.01:
            command.extend(["-vf", f"setpts={1.0 / job.playback_speed:.3f}*PTS"])
        command.extend(["-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)])
        return command

    def _placeholder_command(self, *, job: HighlightRenderJob, output_path: Path) -> list[str]:
        return [
            self.binary,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=1280x720:d={self._seconds(job.duration_seconds)}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    def _concat_command(self, *, clip_paths: list[Path], output_path: Path) -> list[str]:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".txt") as handle:
            for clip_path in clip_paths:
                handle.write(f"file '{clip_path.as_posix()}'\n")
            list_path = Path(handle.name)
        return [
            self.binary,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    def _run(self, command: list[str]) -> None:
        subprocess.run(command, check=True, capture_output=True)

    @staticmethod
    def _seconds(value: int | float) -> str:
        return f"{float(value):.3f}"


__all__ = ["FFmpegHighlightRenderer", "HighlightRenderer"]
