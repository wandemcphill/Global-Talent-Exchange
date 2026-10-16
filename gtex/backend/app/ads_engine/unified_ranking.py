from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

AD_FREQUENCY_WINDOW = 5


@dataclass(frozen=True, slots=True)
class UnifiedFeedCandidate:
    candidate_key: str
    clip_id: str
    item_type: Literal["organic", "sponsored"]
    payload: Any
    raw_score: float
    normalized_score: float = 0.0


def normalize_candidates(candidates: list[UnifiedFeedCandidate]) -> list[UnifiedFeedCandidate]:
    max_by_type: dict[str, float] = {}
    for candidate in candidates:
        max_by_type[candidate.item_type] = max(
            max_by_type.get(candidate.item_type, 0.0),
            max(float(candidate.raw_score), 0.0),
        )
    normalized: list[UnifiedFeedCandidate] = []
    for candidate in candidates:
        max_score = max(max_by_type.get(candidate.item_type, 0.0), 1.0)
        normalized.append(
            replace(
                candidate,
                normalized_score=round(max(float(candidate.raw_score), 0.0) / max_score, 6),
            )
        )
    return normalized


def rank_unified_feed(
    candidates: list[UnifiedFeedCandidate],
    *,
    limit: int,
    ad_frequency_window: int = AD_FREQUENCY_WINDOW,
) -> list[UnifiedFeedCandidate]:
    resolved_limit = max(1, int(limit))
    if not candidates:
        return []
    pending = sorted(
        _dedupe_by_clip(normalize_candidates(candidates)),
        key=_sort_key,
        reverse=True,
    )
    selected: list[UnifiedFeedCandidate] = []
    while pending and len(selected) < resolved_limit:
        placed = False
        for index, candidate in enumerate(pending):
            if candidate.item_type == "sponsored" and not _can_place_sponsored(
                selected,
                ad_frequency_window=ad_frequency_window,
            ):
                continue
            selected.append(candidate)
            pending.pop(index)
            placed = True
            break
        if not placed:
            break
    return selected


def _dedupe_by_clip(candidates: list[UnifiedFeedCandidate]) -> list[UnifiedFeedCandidate]:
    best_by_clip: dict[str, UnifiedFeedCandidate] = {}
    for candidate in candidates:
        existing = best_by_clip.get(candidate.clip_id)
        if existing is None:
            best_by_clip[candidate.clip_id] = candidate
            continue
        if candidate.item_type == "sponsored" and existing.item_type != "sponsored":
            best_by_clip[candidate.clip_id] = candidate
            continue
        if existing.item_type == "sponsored" and candidate.item_type != "sponsored":
            continue
        if _sort_key(candidate) > _sort_key(existing):
            best_by_clip[candidate.clip_id] = candidate
    return list(best_by_clip.values())


def _sort_key(candidate: UnifiedFeedCandidate) -> tuple[float, float, int, str]:
    return (
        round(float(candidate.normalized_score), 6),
        round(float(candidate.raw_score), 6),
        1 if candidate.item_type == "sponsored" else 0,
        candidate.candidate_key,
    )


def _can_place_sponsored(
    selected: list[UnifiedFeedCandidate],
    *,
    ad_frequency_window: int,
) -> bool:
    if ad_frequency_window <= 1:
        return True
    last_sponsored_position = None
    for index in range(len(selected) - 1, -1, -1):
        if selected[index].item_type == "sponsored":
            last_sponsored_position = index
            break
    if last_sponsored_position is None:
        return True
    return (len(selected) - last_sponsored_position) >= int(ad_frequency_window)


__all__ = [
    "AD_FREQUENCY_WINDOW",
    "UnifiedFeedCandidate",
    "normalize_candidates",
    "rank_unified_feed",
]
