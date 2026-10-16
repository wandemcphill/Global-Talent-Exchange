from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from services.livestream.composer import StreamSegment


@dataclass(frozen=True, slots=True)
class StreamWindow:
    window_id: str
    segments: tuple[StreamSegment, ...]
    total_duration_seconds: int

    def as_dict(self) -> dict[str, object]:
        return {
            "window_id": self.window_id,
            "segments": [asdict(segment) for segment in self.segments],
            "total_duration_seconds": self.total_duration_seconds,
        }


class LivestreamScheduler:
    def __init__(self, playlist: Sequence[StreamSegment]) -> None:
        self._playlist = list(playlist)
        self._cursor = 0

    def build_window(self, *, minimum_duration_seconds: int = 3600) -> StreamWindow:
        if not self._playlist:
            return StreamWindow(window_id="window_empty", segments=(), total_duration_seconds=0)
        selected: list[StreamSegment] = []
        total_duration = 0
        while total_duration < max(minimum_duration_seconds, 1):
            segment = self._playlist[self._cursor]
            selected.append(segment)
            total_duration += max(segment.duration_seconds, 1)
            self._cursor = (self._cursor + 1) % len(self._playlist)
            if len(selected) > len(self._playlist) * 4 and total_duration > 0:
                break
        return StreamWindow(
            window_id=f"window_{self._cursor}_{total_duration}",
            segments=tuple(selected),
            total_duration_seconds=total_duration,
        )
