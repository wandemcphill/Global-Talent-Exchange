from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.learning_engine import AgentLearningState
    from app.copilot.agent_copilot_service import AgentCopilotAnalysis, AgentCopilotService


FAST_EVENT_TYPES = frozenset({"goal", "winner", "equalizer", "penalty", "penalty_goal", "red_card", "late_drama"})
CHAOS_EVENT_TYPES = frozenset({"goal", "equalizer", "red_card", "late_drama", "winner"})
STYLE_PRIMARY_FORMATS: dict[str, tuple[str, ...]] = {
    "chaotic_meme": ("meme_version", "instant_clip", "debate_clip"),
    "tactical_breakdown": ("tactical_breakdown", "cinematic_replay", "debate_clip"),
    "cinematic_story": ("cinematic_replay", "instant_clip", "meme_version"),
    "debate_hunter": ("debate_clip", "instant_clip", "meme_version"),
    "instant_reaction": ("instant_clip", "meme_version", "cinematic_replay"),
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


@dataclass(slots=True)
class AgentIdentity:
    agent_id: str
    handle: str
    display_name: str
    style: str
    target: str


@dataclass(slots=True)
class AgentStrategy:
    risk_level: float
    avg_duration: int
    tempo: str
    audience_bias: str
    preferred_formats: tuple[str, ...] = ()
    event_focus: tuple[str, ...] = ()
    cadence_minutes: int = 8
    experimental_share: float = 0.30
    global_exposure_feedback: float = 0.0
    shared_brain: str = "copilot"


@dataclass(slots=True)
class AgentProfile:
    identity: AgentIdentity
    strategy: AgentStrategy


@dataclass(slots=True)
class AgentMomentCandidate:
    candidate_id: str
    match_id: str
    source_event_id: str
    event_type: str
    minute: int
    team_name: str | None = None
    player_name: str | None = None
    scoreline_label: str | None = None
    priority_score: float = 0.0
    detected_events: tuple[str, ...] = ()
    storage_key: str | None = None
    video_url: str | None = None
    render_status: str = "queued"
    created_at: datetime = field(default_factory=_utcnow)
    metadata: dict[str, object] = field(default_factory=dict)

    def age_minutes(self, *, now: datetime | None = None) -> float:
        reference = now or _utcnow()
        created_at = self.created_at if self.created_at.tzinfo is not None else self.created_at.replace(tzinfo=UTC)
        return max((reference - created_at.astimezone(UTC)).total_seconds() / 60.0, 0.0)


@dataclass(slots=True)
class AgentDecisionContext:
    candidate_pool: list[AgentMomentCandidate]
    recent_agent_ratio: float
    recent_dispatch_total: int
    recent_format_counts: dict[str, int]
    recent_style_counts: dict[str, int]
    candidate_usage: dict[str, int]
    max_agent_ratio: float
    max_agents_per_candidate: int
    global_exposure_feedback: dict[str, float] = field(default_factory=dict)
    winner_variant_scores: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class AgentDecision:
    should_post: bool
    reason: str
    candidate: AgentMomentCandidate | None = None
    risk_level: float = 0.0
    duration_seconds: int = 12
    selected_formats: tuple[str, ...] = ()
    caption_seed: str = "live_reaction"
    predicted_reward: float = 0.0
    confidence: float = 0.0
    shared_brain: str = "heuristic"
    best_format_key: str | None = None
    global_exposure_feedback: float = 0.0
    winner_variant_score: float = 0.0


class AgentBrain:
    def __init__(self, *, copilot_service: "AgentCopilotService | None" = None) -> None:
        if copilot_service is None:
            from app.copilot.agent_copilot_service import AgentCopilotService as _AgentCopilotService

            copilot_service = _AgentCopilotService()
        self.copilot_service = copilot_service

    def decide(
        self,
        *,
        profile: AgentProfile,
        learning_state: AgentLearningState,
        context: AgentDecisionContext,
        now: datetime | None = None,
    ) -> AgentDecision:
        if not context.candidate_pool:
            return AgentDecision(should_post=False, reason="no_candidates")

        reference = now or _utcnow()
        ratio_pressure = context.recent_agent_ratio / max(context.max_agent_ratio, 0.01)
        analyses = {
            item.candidate_id: self.copilot_service.analyze(
                profile=profile,
                learning_state=learning_state,
                context=context,
                candidate=item,
            )
            for item in context.candidate_pool
        }
        ranked_candidates = sorted(
            context.candidate_pool,
            key=lambda item: (
                -self._candidate_score(
                    profile=profile,
                    learning_state=learning_state,
                    candidate=item,
                    context=context,
                    analysis=analyses[item.candidate_id],
                    now=reference,
                ),
                item.candidate_id,
            ),
        )
        best_candidate = ranked_candidates[0]
        best_analysis = analyses[best_candidate.candidate_id]
        score = self._candidate_score(
            profile=profile,
            learning_state=learning_state,
            candidate=best_candidate,
            context=context,
            analysis=best_analysis,
            now=reference,
        )
        confidence = _clamp(
            score
            * (1.0 - max(ratio_pressure - 0.85, 0.0) * 0.30)
            * (1.0 + min(learning_state.average_reward, 2.0) * 0.08)
            * (1.0 + best_analysis.viral_probability * 0.20),
            0.0,
            4.0,
        )
        threshold = 0.72 + max(ratio_pressure - 0.50, 0.0) * 0.18
        if confidence < threshold:
            return AgentDecision(
                should_post=False,
                reason="insufficient_confidence",
                candidate=best_candidate,
                confidence=round(confidence, 4),
                shared_brain="copilot",
                best_format_key=best_analysis.best_format_key,
                global_exposure_feedback=best_analysis.global_exposure_feedback,
                winner_variant_score=best_analysis.winner_variant_score,
            )

        selected_formats = self._select_formats(
            profile=profile,
            learning_state=learning_state,
            context=context,
            analysis=best_analysis,
        )
        risk_level = _clamp(
            profile.strategy.risk_level
            + (0.04 * min(learning_state.loss_streak, 3))
            - (0.03 * min(learning_state.win_streak, 3))
            - (0.06 * max(ratio_pressure - 0.90, 0.0)),
            0.10,
            1.00,
        )
        duration_seconds = self._duration_seconds(
            profile=profile,
            learning_state=learning_state,
            candidate=best_candidate,
        )
        return AgentDecision(
            should_post=True,
            reason="ready",
            candidate=best_candidate,
            risk_level=round(risk_level, 4),
            duration_seconds=duration_seconds,
            selected_formats=selected_formats,
            caption_seed=self._caption_seed(profile.identity.style, best_candidate),
            predicted_reward=round(
                confidence
                * (1.0 + (risk_level * 0.30))
                * (1.0 + (best_analysis.global_exposure_feedback * 0.10)),
                4,
            ),
            confidence=round(confidence, 4),
            shared_brain="copilot",
            best_format_key=best_analysis.best_format_key,
            global_exposure_feedback=best_analysis.global_exposure_feedback,
            winner_variant_score=best_analysis.winner_variant_score,
        )

    def _candidate_score(
        self,
        *,
        profile: AgentProfile,
        learning_state: AgentLearningState,
        candidate: AgentMomentCandidate,
        context: AgentDecisionContext,
        analysis: "AgentCopilotAnalysis",
        now: datetime,
    ) -> float:
        freshness = max(0.35, 1.30 - min(candidate.age_minutes(now=now), 75.0) / 75.0)
        focus_bonus = 0.18 if candidate.event_type in set(profile.strategy.event_focus) else 0.0
        chaos_bonus = 0.16 if profile.identity.style == "chaotic_meme" and candidate.event_type in CHAOS_EVENT_TYPES else 0.0
        tempo_bonus = 0.14 if profile.strategy.tempo == "fast" and candidate.event_type in FAST_EVENT_TYPES else 0.0
        audience_bonus = 0.10 if profile.strategy.audience_bias in {"humor", "drama"} and candidate.event_type in CHAOS_EVENT_TYPES else 0.0
        candidate_penalty = 0.18 * min(
            context.candidate_usage.get(candidate.candidate_id, 0) / max(context.max_agents_per_candidate, 1),
            1.0,
        )
        streak_bonus = 0.04 * min(learning_state.win_streak, 4)
        exploration_bonus = 0.08 * learning_state.exploration_rate
        copilot_bonus = (
            (analysis.confidence * 0.22)
            + (analysis.global_exposure_feedback * 0.18)
            + (analysis.winner_variant_score * 0.16)
        )
        return max(
            (
                max(candidate.priority_score, 0.05)
                * freshness
                * (
                    1.0
                    + focus_bonus
                    + chaos_bonus
                    + tempo_bonus
                    + audience_bonus
                    + streak_bonus
                    + exploration_bonus
                    + copilot_bonus
                )
            )
            - candidate_penalty,
            0.0,
        )

    def _select_formats(
        self,
        *,
        profile: AgentProfile,
        learning_state: AgentLearningState,
        context: AgentDecisionContext,
        analysis: "AgentCopilotAnalysis",
    ) -> tuple[str, ...]:
        defaults = STYLE_PRIMARY_FORMATS.get(profile.identity.style, ("instant_clip", "meme_version", "debate_clip"))
        ranked_preferences = sorted(
            learning_state.preferred_formats.items(),
            key=lambda item: (-item[1], item[0]),
        )
        format_candidates: list[str] = [analysis.best_format_key]
        format_candidates.extend(list(profile.strategy.preferred_formats) or list(defaults))
        format_candidates.extend(name for name, score in ranked_preferences if score > 0.0)
        format_candidates.extend(defaults)
        unique_formats: list[str] = []
        for format_key in format_candidates:
            if format_key not in unique_formats:
                unique_formats.append(format_key)
        ordered = sorted(
            unique_formats,
            key=lambda item: (
                context.recent_format_counts.get(item, 0),
                -analysis.format_scores.get(item, 0.0),
                -learning_state.preferred_formats.get(item, 0.0),
                unique_formats.index(item),
            ),
        )
        selected_count = 3 if learning_state.exploration_rate >= 0.25 else 2
        return tuple(ordered[:selected_count])

    def _duration_seconds(
        self,
        *,
        profile: AgentProfile,
        learning_state: AgentLearningState,
        candidate: AgentMomentCandidate,
    ) -> int:
        duration = max(int(profile.strategy.avg_duration), 6)
        if profile.strategy.tempo == "fast" or candidate.event_type in FAST_EVENT_TYPES:
            duration -= 2
        if learning_state.average_reward > 1.20 and candidate.event_type not in FAST_EVENT_TYPES:
            duration += 1
        return max(min(duration, 45), 6)

    @staticmethod
    def _caption_seed(style: str, candidate: AgentMomentCandidate) -> str:
        if style == "chaotic_meme":
            return "shock_reaction"
        if style == "tactical_breakdown":
            return "tactical_frame"
        if style == "cinematic_story":
            return "hero_moment"
        if candidate.event_type in {"goal", "winner", "equalizer"}:
            return "crowd_swing"
        return "live_reaction"


__all__ = [
    "AgentBrain",
    "AgentDecision",
    "AgentDecisionContext",
    "AgentIdentity",
    "AgentMomentCandidate",
    "AgentProfile",
    "AgentStrategy",
    "CHAOS_EVENT_TYPES",
    "FAST_EVENT_TYPES",
    "STYLE_PRIMARY_FORMATS",
]
