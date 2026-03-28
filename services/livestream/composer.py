from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class StreamSegment:
    segment_id: str
    kind: str
    title: str
    path: str
    duration_seconds: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def compose_match_segment(match: Mapping[str, Any]) -> StreamSegment:
    match_id = str(match.get("match_id") or match.get("fixture_id") or "match")
    home = str(match.get("home_club_name") or match.get("team_name") or "Home")
    away = str(match.get("away_club_name") or match.get("opponent_name") or "Away")
    scoreline = f"{int(match.get('home_goals') or 0)}-{int(match.get('away_goals') or 0)}"
    return StreamSegment(
        segment_id=f"seg_{match_id}",
        kind="match",
        title=f"{home} vs {away}",
        path=str(match.get("video_path") or f"generated/{match_id}/full_match.mp4"),
        duration_seconds=max(120, int(match.get("duration_seconds") or 900)),
        metadata={
            "match_id": match_id,
            "scoreline": scoreline,
            "commentary_prompt": match.get("commentary_prompt"),
            "pundit_prompt": match.get("pundit_prompt"),
        },
    )


def compose_highlight_segment(clip: Mapping[str, Any]) -> StreamSegment:
    clip_id = str(clip.get("clip_id") or clip.get("match_id") or "highlight")
    return StreamSegment(
        segment_id=f"seg_{clip_id}",
        kind="highlight",
        title=str(clip.get("title") or "Highlight Reel"),
        path=str(clip.get("video_path") or f"generated/{clip_id}/highlight.mp4"),
        duration_seconds=max(15, int(clip.get("duration") or 30)),
        metadata={"viral_score": int(clip.get("viral_score") or 0)},
    )


def compose_studio_segment(
    *,
    kind: str,
    title: str,
    path: str,
    duration_seconds: int,
    metadata: Mapping[str, Any] | None = None,
) -> StreamSegment:
    return StreamSegment(
        segment_id=f"seg_{kind}_{title.lower().replace(' ', '_')}",
        kind=kind,
        title=title,
        path=path,
        duration_seconds=max(1, duration_seconds),
        metadata=dict(metadata or {}),
    )
