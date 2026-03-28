from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import log
from typing import Any


@dataclass(frozen=True, slots=True)
class SimulationReport:
    generated_at: datetime
    ticks: int
    sessions: int
    avg_session_time: float
    avg_watch_time: float
    retention_curve: dict[str, float]
    fairness_index: float
    creator_distribution: dict[str, int]
    ad_performance: dict[str, float]
    viral_detection_speed: float
    total_impressions: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "ticks": self.ticks,
            "sessions": self.sessions,
            "avg_session_time": round(self.avg_session_time, 4),
            "avg_watch_time": round(self.avg_watch_time, 4),
            "retention_curve": {key: round(value, 4) for key, value in self.retention_curve.items()},
            "fairness_index": round(self.fairness_index, 4),
            "creator_distribution": dict(self.creator_distribution),
            "ad_performance": {key: round(value, 4) for key, value in self.ad_performance.items()},
            "viral_detection_speed": round(self.viral_detection_speed, 4),
            "total_impressions": self.total_impressions,
        }


@dataclass(slots=True)
class SimulationMetricsCollector:
    session_watch_times: list[float] = field(default_factory=list)
    watch_times: list[float] = field(default_factory=list)
    creator_impressions: Counter[str] = field(default_factory=Counter)
    clip_impressions: Counter[str] = field(default_factory=Counter)
    stage_first_seen_tick: dict[str, int] = field(default_factory=dict)
    clip_first_viral_tick: dict[str, int] = field(default_factory=dict)
    ad_impressions: int = 0
    ad_clicks: int = 0
    reactions: Counter[str] = field(default_factory=Counter)
    retention_buckets: defaultdict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def begin_session(self) -> None:
        self.session_watch_times.append(0.0)

    def record_delivery(self, *, tick: int, position: int, clip: Any) -> None:
        metadata = dict(getattr(clip, "metadata", {}) or {})
        creator_id = str(metadata.get("creator_id") or metadata.get("creator_user_id") or "unknown").strip() or "unknown"
        self.creator_impressions[creator_id] += 1
        self.clip_impressions[str(getattr(clip, "clip_id", "unknown"))] += 1
        if bool(metadata.get("is_ad", False)):
            self.ad_impressions += 1
        stage = None
        orchestrator = getattr(clip, "orchestrator", None)
        if orchestrator is not None:
            stage = getattr(orchestrator, "stage", None)
        if isinstance(stage, str):
            self.stage_first_seen_tick.setdefault(f"{getattr(clip, 'clip_id', 'unknown')}::{stage}", tick)
            if stage == "viral":
                self.clip_first_viral_tick.setdefault(str(getattr(clip, "clip_id", "unknown")), tick)
        self.retention_buckets[f"position_{position + 1}"].append(0.0)

    def record_reaction(self, *, clip: Any, position: int, reaction: dict[str, float | bool]) -> None:
        watch_time = max(float(reaction.get("watch_time", 0.0) or 0.0), 0.0)
        self.watch_times.append(watch_time)
        if self.session_watch_times:
            self.session_watch_times[-1] += watch_time
        self.retention_buckets[f"position_{position + 1}"][-1] = watch_time
        if bool(reaction.get("liked", False)):
            self.reactions["likes"] += 1
        if bool(reaction.get("shared", False)):
            self.reactions["shares"] += 1
            metadata = dict(getattr(clip, "metadata", {}) or {})
            if bool(metadata.get("is_ad", False)):
                self.ad_clicks += 1
        if bool(reaction.get("skipped", False)):
            self.reactions["skips"] += 1

    def report(self, *, ticks: int) -> SimulationReport:
        sessions = len(self.session_watch_times)
        total_watch_time = sum(self.watch_times)
        avg_watch_time = total_watch_time / len(self.watch_times) if self.watch_times else 0.0
        avg_session_time = sum(self.session_watch_times) / sessions if sessions else 0.0
        fairness_index = self._fairness_index()
        retention_curve = {
            bucket: (sum(values) / len(values) if values else 0.0)
            for bucket, values in sorted(self.retention_buckets.items())
        }
        if self.clip_first_viral_tick:
            viral_detection_speed = sum(self.clip_first_viral_tick.values()) / len(self.clip_first_viral_tick)
        else:
            viral_detection_speed = float(ticks)
        ad_ctr = (self.ad_clicks / self.ad_impressions) if self.ad_impressions > 0 else 0.0
        return SimulationReport(
            generated_at=datetime.now(UTC),
            ticks=int(ticks),
            sessions=sessions,
            avg_session_time=avg_session_time,
            avg_watch_time=avg_watch_time,
            retention_curve=retention_curve,
            fairness_index=fairness_index,
            creator_distribution=dict(self.creator_impressions),
            ad_performance={
                "impressions": float(self.ad_impressions),
                "clicks": float(self.ad_clicks),
                "ctr": ad_ctr,
            },
            viral_detection_speed=viral_detection_speed,
            total_impressions=sum(self.clip_impressions.values()),
        )

    def _fairness_index(self) -> float:
        counts = [count for count in self.creator_impressions.values() if count > 0]
        if not counts:
            return 1.0
        total = float(sum(counts))
        if len(counts) == 1 or total <= 0:
            return 1.0
        entropy = -sum((count / total) * log(count / total) for count in counts)
        max_entropy = log(len(counts))
        if max_entropy <= 0:
            return 1.0
        return max(min(entropy / max_entropy, 1.0), 0.0)
