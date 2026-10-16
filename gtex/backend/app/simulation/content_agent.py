from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(slots=True)
class SimulatedDistributionAccount:
    handle: str


@dataclass(slots=True)
class SimulatedEditor:
    format_key: str


@dataclass(slots=True)
class SimulatedAnalytics:
    clip_id: str
    view_count: int = 1
    completions: int = 1
    watch_time: float = 12.0
    total_watch_time: float = 12.0
    loops: float = 0.0
    loop_rate: float = 0.0
    shares: int = 0
    comments: int = 0
    skips: int = 0
    completion_rate: float = 1.0
    share_rate: float = 0.0
    comment_rate: float = 0.0
    views_last_10min: int = 1
    views_last_60min: int = 1


@dataclass(slots=True)
class SimulatedClip:
    clip_id: str
    match_id: str
    highlight_id: str
    title: str
    event_type: str
    minute: int
    viral_score: int
    engagement: float
    freshness: float
    ranking_score: float
    analytics: SimulatedAnalytics
    editor: SimulatedEditor
    distribution_accounts: list[SimulatedDistributionAccount]
    metadata: dict[str, Any] = field(default_factory=dict)
    team_name: str | None = None
    player_name: str | None = None
    orchestrator: Any | None = None


@dataclass(slots=True)
class ContentAgent:
    clip_id: str
    creator_id: str
    quality: float
    format: str
    trust: float
    velocity: float
    event_type: str = "goal"
    is_ad: bool = False
    is_moment: bool = False
    bid_weight: float = 1.0
    team_name: str | None = None
    player_name: str | None = None
    age_hours: float = 0.0
    match_id: str = "simulation-match"
    highlight_id: str | None = None
    view_count: int = 100
    share_bias: float = 0.0
    comment_bias: float = 0.0
    loop_bias: float = 0.0
    _published_at: datetime = field(default_factory=lambda: datetime.now(UTC), init=False, repr=False)

    def __post_init__(self) -> None:
        self.quality = min(max(float(self.quality), 0.0), 1.0)
        self.trust = min(max(float(self.trust), 0.0), 1.0)
        self.velocity = max(float(self.velocity), 0.0)
        self.bid_weight = max(float(self.bid_weight), 0.0)
        self.share_bias = max(float(self.share_bias), 0.0)
        self.comment_bias = max(float(self.comment_bias), 0.0)
        self.loop_bias = max(float(self.loop_bias), 0.0)
        self.age_hours = max(float(self.age_hours), 0.0)
        self._published_at = datetime.now(UTC) - timedelta(hours=self.age_hours)
        if self.highlight_id is None:
            self.highlight_id = self.clip_id.rsplit("::", 1)[-1]

    def as_clip(self) -> SimulatedClip:
        completion_rate = min(max((self.quality * 0.75) + (self.trust * 0.20), 0.05), 0.99)
        share_rate = min(max((self.quality * 0.08) + (self.velocity * 0.04) + self.share_bias, 0.0), 1.0)
        comment_rate = min(max((self.quality * 0.04) + self.comment_bias, 0.0), 1.0)
        loop_rate = min(max((self.quality * 0.12) + self.loop_bias, 0.0), 1.0)
        total_watch_time = round(max(self.view_count, 1) * max(3.0, 8.0 + (self.quality * 12.0)), 2)
        completions = min(max(int(round(self.view_count * completion_rate)), 0), self.view_count)
        shares = max(int(round(self.view_count * share_rate)), 0)
        comments = max(int(round(self.view_count * comment_rate)), 0)
        loops = round(self.view_count * loop_rate, 2)
        views_last_60min = max(int(round(self.view_count * min(max(self.velocity / 2.0, 0.05), 1.0))), 1)
        views_last_10min = max(int(round(views_last_60min * min(max(self.velocity / 4.0, 0.05), 1.0))), 1)
        analytics = SimulatedAnalytics(
            clip_id=self.clip_id,
            view_count=max(self.view_count, 1),
            completions=completions,
            watch_time=round(total_watch_time / max(self.view_count, 1), 2),
            total_watch_time=total_watch_time,
            loops=loops,
            loop_rate=round(loop_rate, 4),
            shares=shares,
            comments=comments,
            skips=max(self.view_count - completions, 0),
            completion_rate=round(completion_rate, 4),
            share_rate=round(share_rate, 4),
            comment_rate=round(comment_rate, 4),
            views_last_10min=views_last_10min,
            views_last_60min=views_last_60min,
        )
        viral_score = int(round(min(max(((self.quality + self.trust) * 40.0) + (self.velocity * 18.0), 0.0), 100.0)))
        return SimulatedClip(
            clip_id=self.clip_id,
            match_id=self.match_id,
            highlight_id=self.highlight_id or self.clip_id,
            title=self.clip_id,
            event_type=self.event_type,
            minute=90,
            viral_score=viral_score,
            engagement=round((self.quality * 100.0), 2),
            freshness=round(max(0.0, 100.0 - (self.age_hours * 2.5)), 2),
            ranking_score=round((self.quality * self.velocity * self.trust) * 100.0, 2),
            analytics=analytics,
            editor=SimulatedEditor(format_key=self.format),
            distribution_accounts=[SimulatedDistributionAccount(handle=self.creator_id)],
            metadata={
                "creator_id": self.creator_id,
                "creator_user_id": self.creator_id,
                "quality_score": round(self.quality, 6),
                "trust_score": round(self.trust, 6),
                "bid_weight": round(self.bid_weight, 6),
                "is_ad": bool(self.is_ad),
                "is_moment": bool(self.is_moment),
                "published_at": self._published_at.isoformat(),
                "format_key": self.format,
                "base_clip_id": self.clip_id,
            },
            team_name=self.team_name,
            player_name=self.player_name,
        )

    def apply_reaction(self, reaction: dict[str, float | bool]) -> None:
        watch_time = max(float(reaction.get("watch_time", 0.0) or 0.0), 0.0)
        liked = bool(reaction.get("liked", False))
        shared = bool(reaction.get("shared", False))
        skipped = bool(reaction.get("skipped", False))
        if watch_time > 0.0:
            self.quality = min(self.quality + min(watch_time / 300.0, 0.03), 1.0)
        if liked:
            self.velocity = min(self.velocity + 0.05, 3.0)
        if shared:
            self.velocity = min(self.velocity + 0.12, 3.0)
            self.share_bias = min(self.share_bias + 0.01, 0.4)
        if skipped:
            self.velocity = max(self.velocity - 0.06, 0.0)
            self.quality = max(self.quality - 0.01, 0.0)
        self.view_count = max(self.view_count + 1, 1)

