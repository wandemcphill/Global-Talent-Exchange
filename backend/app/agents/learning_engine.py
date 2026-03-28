from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.agent_brain import AgentStrategy


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(slots=True)
class AgentLearningState:
    exploration_rate: float = 0.35
    last_reward: float = 0.0
    average_reward: float = 0.0
    win_streak: int = 0
    loss_streak: int = 0
    total_posts: int = 0
    total_rewards: float = 0.0
    total_penalties: float = 0.0
    preferred_formats: dict[str, float] = field(default_factory=dict)
    last_updated_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True, slots=True)
class AgentPerformanceSignal:
    view_count: int = 0
    watch_time: float = 0.0
    shares: int = 0
    comments: int = 0
    completion_rate: float = 0.0
    share_rate: float = 0.0
    comment_rate: float = 0.0
    velocity: float = 0.0
    impressions: int = 0
    penalties: float = 0.0
    earnings: float = 0.0
    skip_rate: float = 0.0


@dataclass(frozen=True, slots=True)
class AgentRewardBreakdown:
    watch_time_component: float
    share_component: float
    comment_component: float
    completion_component: float
    earnings_component: float
    penalty_component: float
    total: float


class AgentLearningEngine:
    def evaluate(self, performance: AgentPerformanceSignal) -> AgentRewardBreakdown:
        watch_time_component = max(float(performance.watch_time), 0.0) / 24.0
        share_component = max(int(performance.shares), 0) * 0.18
        comment_component = max(int(performance.comments), 0) * 0.08
        completion_component = _clamp(performance.completion_rate, 0.0, 1.0) * 0.75
        earnings_component = max(float(performance.earnings), 0.0)
        penalty_component = max(float(performance.penalties), 0.0) + (_clamp(performance.skip_rate, 0.0, 1.0) * 0.35)
        total = max(
            watch_time_component + share_component + comment_component + completion_component + earnings_component - penalty_component,
            0.0,
        )
        return AgentRewardBreakdown(
            watch_time_component=round(watch_time_component, 4),
            share_component=round(share_component, 4),
            comment_component=round(comment_component, 4),
            completion_component=round(completion_component, 4),
            earnings_component=round(earnings_component, 4),
            penalty_component=round(penalty_component, 4),
            total=round(total, 4),
        )

    def apply(
        self,
        *,
        strategy: AgentStrategy | Any,
        state: AgentLearningState,
        performance: AgentPerformanceSignal,
        chosen_formats: tuple[str, ...],
    ) -> AgentRewardBreakdown:
        reward = self.evaluate(performance)
        next_total_posts = max(int(state.total_posts), 0) + 1
        next_average_reward = (
            ((state.average_reward * max(int(state.total_posts), 0)) + reward.total) / next_total_posts
            if next_total_posts > 0
            else reward.total
        )
        positive_outcome = reward.total >= max(0.65, state.average_reward * 0.85)
        state.exploration_rate = round(
            _clamp(
                state.exploration_rate
                + (0.08 if not positive_outcome else -0.04)
                + (0.03 if performance.velocity < 0.50 else -0.02),
                0.05,
                0.85,
            ),
            4,
        )
        state.last_reward = reward.total
        state.average_reward = round(next_average_reward, 4)
        state.total_posts = next_total_posts
        state.total_rewards = round(state.total_rewards + reward.total, 4)
        state.total_penalties = round(state.total_penalties + reward.penalty_component, 4)
        state.last_updated_at = _utcnow()
        if positive_outcome:
            state.win_streak = min(state.win_streak + 1, 10)
            state.loss_streak = 0
        else:
            state.loss_streak = min(state.loss_streak + 1, 10)
            state.win_streak = 0

        preferred_formats = dict(state.preferred_formats)
        for format_key in chosen_formats:
            baseline = preferred_formats.get(format_key, 0.0)
            delta = (reward.total * 0.18) if positive_outcome else -0.10
            preferred_formats[format_key] = round(max(baseline + delta, 0.0), 4)
        state.preferred_formats = preferred_formats

        current_risk = _clamp(getattr(strategy, "risk_level", 0.5), 0.0, 1.0)
        current_duration = max(int(getattr(strategy, "avg_duration", 12) or 12), 6)
        if reward.total < 0.65:
            current_risk = _clamp(current_risk + 0.06, 0.10, 1.00)
        elif reward.total > state.average_reward:
            current_risk = _clamp(current_risk - 0.03, 0.10, 1.00)
        if performance.velocity >= 1.0 or performance.share_rate >= 0.05:
            current_duration = max(current_duration - 1, 6)
        elif performance.completion_rate >= 0.80 and performance.watch_time >= current_duration:
            current_duration = min(current_duration + 1, 45)
        setattr(strategy, "risk_level", round(current_risk, 4))
        setattr(strategy, "avg_duration", current_duration)
        return reward


__all__ = [
    "AgentLearningEngine",
    "AgentLearningState",
    "AgentPerformanceSignal",
    "AgentRewardBreakdown",
]
