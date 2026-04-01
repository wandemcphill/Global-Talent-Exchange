from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
from threading import RLock
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.agent_brain import AgentBrain, AgentDecisionContext, AgentIdentity, AgentMomentCandidate, AgentProfile, AgentStrategy
from app.agents.agent_wallet import AgentWallet, AgentWalletService
from app.backbone.scale_events import enqueue_viral_dispatch
from app.agents.content_generator import AgentContentGenerator, AgentGeneratedClip
from app.agents.learning_engine import AgentLearningEngine, AgentLearningState, AgentPerformanceSignal
from app.agents.state_store import AgentPerformanceLogEntry, AgentStateStore, build_agent_state_store
from app.agents.variant_planner import VariantPlanner
from app.copilot.agent_copilot_service import AgentCopilotService
from app.core.config import Settings, get_settings
from app.core.events import DomainEvent, EventPublisher
from app.orchestrator.orchestrator_service import AttentionOrchestratorService, build_attention_orchestrator_service
from app.viral.ranking_service import LeaderboardEnvelope, ViralLeaderboardStore, ensure_viral_leaderboard_store
from app.viral.schemas import ViralClipDistributionView


logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _coerce_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(float(value), maximum))


def _coerce_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfig:
    initial_population: int = 100
    max_agent_ratio: float = 0.40
    max_posts_per_cycle: int = 6
    max_posts_per_agent_window: int = 3
    per_agent_window_minutes: int = 60
    dispatch_window_minutes: int = 90
    ratio_warm_start_denominator: int = 5
    candidate_pool_limit: int = 250
    max_agents_per_candidate: int = 2
    auto_run_on_moment: bool = True
    moment_trigger_limit: int = 2
    leaderboard_seed_enabled: bool = True

    def as_payload(self) -> dict[str, Any]:
        return {
            "initial_population": max(int(self.initial_population), 1),
            "max_agent_ratio": round(_clamp(self.max_agent_ratio, 0.0, 1.0), 4),
            "max_posts_per_cycle": max(int(self.max_posts_per_cycle), 1),
            "max_posts_per_agent_window": max(int(self.max_posts_per_agent_window), 1),
            "per_agent_window_minutes": max(int(self.per_agent_window_minutes), 1),
            "dispatch_window_minutes": max(int(self.dispatch_window_minutes), 1),
            "ratio_warm_start_denominator": max(int(self.ratio_warm_start_denominator), 1),
            "candidate_pool_limit": max(int(self.candidate_pool_limit), 1),
            "max_agents_per_candidate": max(int(self.max_agents_per_candidate), 1),
            "auto_run_on_moment": bool(self.auto_run_on_moment),
            "moment_trigger_limit": max(int(self.moment_trigger_limit), 1),
            "leaderboard_seed_enabled": bool(self.leaderboard_seed_enabled),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AgentRuntimeConfig":
        return cls(
            initial_population=max(int(payload.get("initial_population", 100) or 100), 1),
            max_agent_ratio=_clamp(float(payload.get("max_agent_ratio", 0.40) or 0.40), 0.0, 1.0),
            max_posts_per_cycle=max(int(payload.get("max_posts_per_cycle", 6) or 6), 1),
            max_posts_per_agent_window=max(int(payload.get("max_posts_per_agent_window", 3) or 3), 1),
            per_agent_window_minutes=max(int(payload.get("per_agent_window_minutes", 60) or 60), 1),
            dispatch_window_minutes=max(int(payload.get("dispatch_window_minutes", 90) or 90), 1),
            ratio_warm_start_denominator=max(int(payload.get("ratio_warm_start_denominator", 5) or 5), 1),
            candidate_pool_limit=max(int(payload.get("candidate_pool_limit", 250) or 250), 1),
            max_agents_per_candidate=max(int(payload.get("max_agents_per_candidate", 2) or 2), 1),
            auto_run_on_moment=bool(payload.get("auto_run_on_moment", True)),
            moment_trigger_limit=max(int(payload.get("moment_trigger_limit", 2) or 2), 1),
            leaderboard_seed_enabled=bool(payload.get("leaderboard_seed_enabled", True)),
        )


@dataclass(slots=True)
class CreatorAgent:
    profile: AgentProfile
    learning_state: AgentLearningState = field(default_factory=AgentLearningState)
    wallet: AgentWallet = field(default_factory=AgentWallet)
    last_generated_clip_id: str | None = None
    last_generated_at: datetime | None = None
    post_history: deque[datetime] = field(default_factory=deque, repr=False)
    state_store: AgentStateStore | None = field(default=None, repr=False, compare=False)

    def save_state(self) -> None:
        if self.state_store is not None:
            self.state_store.save_agent(self)

    def load_state(self) -> bool:
        if self.state_store is None:
            return False
        snapshot = self.state_store.load_agent(self.profile.identity.agent_id)
        if snapshot is None:
            return False
        self.profile = snapshot.profile
        self.learning_state = snapshot.learning_state
        self.wallet = snapshot.wallet
        self.last_generated_clip_id = snapshot.last_generated_clip_id
        self.last_generated_at = snapshot.last_generated_at
        return True


@dataclass(frozen=True, slots=True)
class GeneratedClipRecord:
    clip_id: str
    agent_id: str
    candidate_id: str
    primary_format: str
    variant_formats: tuple[str, ...]
    boost_amount: float
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DispatchWindowEntry:
    occurred_at: datetime
    origin: str


class AgentManagerSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentRuntimeConfigView(AgentManagerSchema):
    initial_population: int = Field(ge=1)
    max_agent_ratio: float = Field(ge=0.0, le=1.0)
    max_posts_per_cycle: int = Field(ge=1)
    max_posts_per_agent_window: int = Field(ge=1)
    per_agent_window_minutes: int = Field(ge=1)
    dispatch_window_minutes: int = Field(ge=1)
    ratio_warm_start_denominator: int = Field(ge=1)
    candidate_pool_limit: int = Field(ge=1)
    max_agents_per_candidate: int = Field(ge=1)
    auto_run_on_moment: bool = True
    moment_trigger_limit: int = Field(ge=1)
    leaderboard_seed_enabled: bool = True


class AgentRuntimeConfigUpdateRequest(AgentManagerSchema):
    initial_population: int | None = Field(default=None, ge=1)
    max_agent_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    max_posts_per_cycle: int | None = Field(default=None, ge=1)
    max_posts_per_agent_window: int | None = Field(default=None, ge=1)
    per_agent_window_minutes: int | None = Field(default=None, ge=1)
    dispatch_window_minutes: int | None = Field(default=None, ge=1)
    ratio_warm_start_denominator: int | None = Field(default=None, ge=1)
    candidate_pool_limit: int | None = Field(default=None, ge=1)
    max_agents_per_candidate: int | None = Field(default=None, ge=1)
    auto_run_on_moment: bool | None = None
    moment_trigger_limit: int | None = Field(default=None, ge=1)
    leaderboard_seed_enabled: bool | None = None


class CreatorAgentView(AgentManagerSchema):
    agent_id: str
    handle: str
    display_name: str
    style: str
    target: str
    risk_level: float = Field(ge=0.0, le=1.0)
    avg_duration: int = Field(ge=1)
    tempo: str
    audience_bias: str
    exploration_rate: float = Field(ge=0.0, le=1.0)
    last_reward: float = Field(ge=0.0)
    average_reward: float = Field(ge=0.0)
    total_posts: int = Field(ge=0)
    balance: float
    roi: float
    last_generated_clip_id: str | None = None
    last_generated_at: datetime | None = None


class AgentRunRequest(AgentManagerSchema):
    max_agents: int | None = Field(default=None, ge=1)
    trigger: str = "manual"


class AgentRunResultView(AgentManagerSchema):
    agent_id: str
    clip_id: str
    candidate_id: str
    primary_format: str
    variant_formats: list[str] = Field(default_factory=list)
    predicted_reward: float = Field(ge=0.0)
    boost_amount: float = Field(ge=0.0)
    generated_at: datetime


class AgentRunResponse(AgentManagerSchema):
    trigger: str
    generated_at: datetime
    published_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    candidate_pool_size: int = Field(ge=0)
    recent_agent_ratio: float = Field(ge=0.0)
    results: list[AgentRunResultView] = Field(default_factory=list)


class AgentManagerSummaryView(AgentManagerSchema):
    population: int = Field(ge=0)
    active_agent_count: int = Field(ge=0)
    candidate_pool_size: int = Field(ge=0)
    total_generated_clips: int = Field(ge=0)
    recent_dispatch_total: int = Field(ge=0)
    recent_agent_dispatches: int = Field(ge=0)
    recent_agent_ratio: float = Field(ge=0.0)
    latest_clip_ids: list[str] = Field(default_factory=list)
    config: AgentRuntimeConfigView


class AgentPerformanceRequest(AgentManagerSchema):
    agent_id: str | None = None
    clip_id: str | None = None
    view_count: int = Field(default=0, ge=0)
    watch_time: float = Field(default=0.0, ge=0.0)
    shares: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    share_rate: float = Field(default=0.0, ge=0.0)
    comment_rate: float = Field(default=0.0, ge=0.0)
    velocity: float = Field(default=0.0, ge=0.0)
    impressions: int = Field(default=0, ge=0)
    penalties: float = Field(default=0.0, ge=0.0)
    earnings: float = Field(default=0.0, ge=0.0)
    skip_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_identifier(self) -> "AgentPerformanceRequest":
        if not self.agent_id and not self.clip_id:
            raise ValueError("Either agent_id or clip_id is required.")
        return self


class AgentPerformanceReceiptView(AgentManagerSchema):
    agent_id: str
    clip_id: str
    reward: float = Field(ge=0.0)
    risk_level: float = Field(ge=0.0, le=1.0)
    avg_duration: int = Field(ge=1)
    exploration_rate: float = Field(ge=0.0, le=1.0)
    average_reward: float = Field(ge=0.0)
    balance: float
    roi: float
    quality_score: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    payout_eligible: bool = True
    payout_block_reason: str | None = None


class CreatorAgentManager:
    def __init__(
        self,
        *,
        app: FastAPI,
        event_publisher: EventPublisher | None = None,
        leaderboard_store: ViralLeaderboardStore | None = None,
        orchestrator_service: AttentionOrchestratorService | None = None,
        settings: Settings | None = None,
        config: AgentRuntimeConfig | None = None,
        brain: AgentBrain | None = None,
        copilot_service: AgentCopilotService | None = None,
        variant_planner: VariantPlanner | None = None,
        content_generator: AgentContentGenerator | None = None,
        wallet_service: AgentWalletService | None = None,
        learning_engine: AgentLearningEngine | None = None,
        state_store: AgentStateStore | None = None,
    ) -> None:
        self.app = app
        self.settings = settings or getattr(app.state, "settings", None) or get_settings()
        self.event_publisher = event_publisher or getattr(app.state, "event_publisher", None)
        self.leaderboard_store = leaderboard_store
        self.orchestrator_service = orchestrator_service
        self.config = config or AgentRuntimeConfig()
        self.copilot_service = copilot_service or AgentCopilotService()
        self.brain = brain or AgentBrain(copilot_service=self.copilot_service)
        self.variant_planner = variant_planner or VariantPlanner()
        self.content_generator = content_generator or AgentContentGenerator()
        self.wallet_service = wallet_service or AgentWalletService()
        self.learning_engine = learning_engine or AgentLearningEngine()
        self.state_store = state_store or build_agent_state_store(session_factory=getattr(app.state, "session_factory", None))
        self._agents: dict[str, CreatorAgent] = {}
        self._candidate_pool: deque[AgentMomentCandidate] = deque()
        self._dispatch_window: deque[DispatchWindowEntry] = deque()
        self._generated_records: deque[GeneratedClipRecord] = deque()
        self._generated_by_clip: dict[str, GeneratedClipRecord] = {}
        self._candidate_usage: Counter[str] = Counter()
        self._subscribed = False
        self._closed = False
        self._lock = RLock()

    def bootstrap_population(self, *, count: int | None = None) -> None:
        desired = count or self.config.initial_population
        with self._lock:
            self._hydrate_persisted_agents()
            if len(self._agents) >= desired:
                return
            next_index = self._next_agent_index()
            while len(self._agents) < desired:
                agent = self._build_agent(next_index)
                agent.state_store = self.state_store
                self._agents[agent.profile.identity.agent_id] = agent
                agent.save_state()
                next_index += 1

    def subscribe(self) -> None:
        if self._subscribed or self.event_publisher is None:
            return
        self.event_publisher.subscribe(self.handle_event)
        self._subscribed = True

    def handle_event(self, event: DomainEvent) -> None:
        with self._lock:
            if self._closed:
                return
            if event.name == "moments.live.created":
                self._ingest_moment_event(event)
                if self.config.auto_run_on_moment:
                    self.run_cycle(max_agents=self.config.moment_trigger_limit, trigger="moment")
                return
            if event.name == "viral.clip.dispatch.requested":
                self._record_dispatch(event)
                return
            if event.name == "viral.clip.performance.reported":
                payload = dict(event.payload or {})
                try:
                    request = AgentPerformanceRequest(**payload)
                except Exception:
                    return
                self.record_performance(request)

    def get_config_view(self) -> AgentRuntimeConfigView:
        return AgentRuntimeConfigView(**self.config.as_payload())

    def update_config(self, payload: AgentRuntimeConfigUpdateRequest) -> AgentRuntimeConfigView:
        current = self.config.as_payload()
        current.update(payload.model_dump(exclude_none=True))
        self.config = AgentRuntimeConfig.from_payload(current)
        self.bootstrap_population(count=self.config.initial_population)
        return self.get_config_view()

    def list_agents(self, *, limit: int = 25) -> list[CreatorAgentView]:
        with self._lock:
            agents = sorted(
                self._agents.values(),
                key=lambda item: (
                    -(item.learning_state.average_reward),
                    item.profile.identity.agent_id,
                ),
            )[: max(int(limit), 1)]
            return [self._agent_view(agent) for agent in agents]

    def summary(self) -> AgentManagerSummaryView:
        with self._lock:
            self._prune_windows(now=_utcnow())
            return AgentManagerSummaryView(
                population=len(self._agents),
                active_agent_count=len(self._agents),
                candidate_pool_size=len(self._candidate_pool),
                total_generated_clips=len(self._generated_records),
                recent_dispatch_total=len(self._dispatch_window),
                recent_agent_dispatches=sum(1 for item in self._dispatch_window if item.origin == "agent"),
                recent_agent_ratio=self._recent_agent_ratio(),
                latest_clip_ids=[item.clip_id for item in list(self._generated_records)[-5:]][::-1],
                config=self.get_config_view(),
            )

    def run_cycle(self, *, max_agents: int | None = None, trigger: str = "manual") -> AgentRunResponse:
        with self._lock:
            now = _utcnow()
            self._prune_windows(now=now)
            candidates = list(self._candidate_pool)
            if not candidates:
                return AgentRunResponse(
                    trigger=trigger,
                    generated_at=now,
                    published_count=0,
                    skipped_count=0,
                    candidate_pool_size=0,
                    recent_agent_ratio=self._recent_agent_ratio(),
                    results=[],
                )
            results: list[AgentRunResultView] = []
            skipped_count = 0
            publish_limit = min(max_agents or self.config.max_posts_per_cycle, self.config.max_posts_per_cycle)
            for agent in self._ordered_agents(now=now):
                if len(results) >= publish_limit:
                    break
                if not self._agent_can_post(agent, now=now):
                    skipped_count += 1
                    continue
                if not self._can_publish_agent_clip():
                    break
                decision = self.brain.decide(
                    profile=agent.profile,
                    learning_state=agent.learning_state,
                    context=self._decision_context(),
                    now=now,
                )
                if not decision.should_post or decision.candidate is None:
                    skipped_count += 1
                    continue
                boost_decision = self.wallet_service.recommend_boost(
                    wallet=agent.wallet,
                    predicted_reward=decision.predicted_reward,
                    risk_level=decision.risk_level,
                    feed_pressure=self._feed_pressure(),
                )
                agent.profile.strategy.global_exposure_feedback = decision.global_exposure_feedback
                agent.profile.strategy.shared_brain = decision.shared_brain
                variants = self.variant_planner.plan(profile=agent.profile, decision=decision)
                generated = self.content_generator.generate(
                    profile=agent.profile,
                    decision=decision,
                    variants=variants,
                    boost_amount=boost_decision.boost_amount,
                )
                agent.wallet = self.wallet_service.apply_spend(agent.wallet, boost_decision.boost_amount)
                self._publish_generated_clip(generated)
                agent.last_generated_clip_id = generated.clip_id
                agent.last_generated_at = generated.created_at
                agent.post_history.append(generated.created_at)
                if self.state_store is not None:
                    self.state_store.update_strategy_feedback(
                        agent_id=agent.profile.identity.agent_id,
                        global_exposure_feedback=decision.global_exposure_feedback,
                    )
                self._candidate_usage[generated.candidate_id] += 1
                record = GeneratedClipRecord(
                    clip_id=generated.clip_id,
                    agent_id=generated.agent_id,
                    candidate_id=generated.candidate_id,
                    primary_format=generated.primary_format,
                    variant_formats=generated.variant_formats,
                    boost_amount=generated.boost_amount,
                    created_at=generated.created_at,
                )
                self._generated_records.append(record)
                self._generated_by_clip[generated.clip_id] = record
                agent.save_state()
                results.append(
                    AgentRunResultView(
                        agent_id=generated.agent_id,
                        clip_id=generated.clip_id,
                        candidate_id=generated.candidate_id,
                        primary_format=generated.primary_format,
                        variant_formats=list(generated.variant_formats),
                        predicted_reward=decision.predicted_reward,
                        boost_amount=generated.boost_amount,
                        generated_at=generated.created_at,
                    )
                )
            return AgentRunResponse(
                trigger=trigger,
                generated_at=_utcnow(),
                published_count=len(results),
                skipped_count=skipped_count,
                candidate_pool_size=len(self._candidate_pool),
                recent_agent_ratio=self._recent_agent_ratio(),
                results=results,
            )

    def record_performance(self, payload: AgentPerformanceRequest) -> AgentPerformanceReceiptView:
        with self._lock:
            record = self._resolve_record(payload)
            agent = self._agents.get(record.agent_id)
            if agent is None:
                raise KeyError("Unknown agent.")
            signal = AgentPerformanceSignal(
                view_count=payload.view_count,
                watch_time=payload.watch_time,
                shares=payload.shares,
                comments=payload.comments,
                completion_rate=payload.completion_rate,
                share_rate=payload.share_rate,
                comment_rate=payload.comment_rate,
                velocity=payload.velocity,
                impressions=payload.impressions,
                penalties=payload.penalties,
                earnings=payload.earnings,
                skip_rate=payload.skip_rate,
            )
            reward = self.learning_engine.apply(
                strategy=agent.profile.strategy,
                state=agent.learning_state,
                performance=signal,
                chosen_formats=record.variant_formats or (record.primary_format,),
            )
            quality_score = self._quality_score(agent=agent, signal=signal)
            trust_score = self._trust_score(agent=agent, signal=signal, quality_score=quality_score)
            repetition_ratio = self._repetition_ratio(agent_id=record.agent_id, primary_format=record.primary_format)
            agent.wallet, settlement = self.wallet_service.settle(
                agent.wallet,
                earnings=payload.earnings,
                quality_score=quality_score,
                trust_score=trust_score,
                repetition_ratio=repetition_ratio,
            )
            agent.save_state()
            if self.state_store is not None:
                self.state_store.record_performance_log(
                    AgentPerformanceLogEntry(
                        agent_id=record.agent_id,
                        clip_id=record.clip_id,
                        primary_format=record.primary_format,
                        variant_formats=record.variant_formats,
                        reward_total=reward.total,
                        quality_score=quality_score,
                        trust_score=trust_score,
                        payout_eligible=settlement.approved,
                        payout_block_reason=None if settlement.approved else settlement.reason,
                        performance=signal,
                        orchestrator_weight=self._orchestrator_weight_for(record.clip_id),
                        global_exposure_feedback=self._exposure_feedback_for(record.primary_format),
                        winner_variant_score=self._winner_variant_scores().get(record.primary_format, 0.0),
                        metadata={"agent_handle": agent.profile.identity.handle},
                    )
                )
            return AgentPerformanceReceiptView(
                agent_id=record.agent_id,
                clip_id=record.clip_id,
                reward=reward.total,
                risk_level=agent.profile.strategy.risk_level,
                avg_duration=agent.profile.strategy.avg_duration,
                exploration_rate=agent.learning_state.exploration_rate,
                average_reward=agent.learning_state.average_reward,
                balance=agent.wallet.balance,
                roi=agent.wallet.roi,
                quality_score=quality_score,
                trust_score=trust_score,
                payout_eligible=settlement.approved,
                payout_block_reason=None if settlement.approved else settlement.reason,
            )

    def close(self) -> None:
        self._closed = True

    def _hydrate_persisted_agents(self) -> None:
        if self.state_store is None or self._agents:
            return
        for snapshot in self.state_store.list_agents():
            agent = CreatorAgent(
                profile=snapshot.profile,
                learning_state=snapshot.learning_state,
                wallet=snapshot.wallet,
                last_generated_clip_id=snapshot.last_generated_clip_id,
                last_generated_at=snapshot.last_generated_at,
                state_store=self.state_store,
            )
            self._agents[agent.profile.identity.agent_id] = agent

    def _next_agent_index(self) -> int:
        indices = [self._agent_index(agent_id) for agent_id in self._agents]
        return (max(indices) + 1) if indices else 1

    @staticmethod
    def _agent_index(agent_id: str) -> int:
        suffix = agent_id.rsplit("_", 1)[-1]
        try:
            return max(int(suffix), 0)
        except ValueError:
            return 0

    def _ordered_agents(self, *, now: datetime) -> list[CreatorAgent]:
        return sorted(
            self._agents.values(),
            key=lambda item: (
                len([stamp for stamp in item.post_history if stamp >= now - timedelta(minutes=self.config.per_agent_window_minutes)]),
                item.last_generated_at or datetime.min.replace(tzinfo=UTC),
                item.profile.identity.agent_id,
            ),
        )

    def _decision_context(self) -> AgentDecisionContext:
        recent_format_counts = Counter(item.primary_format for item in self._generated_records)
        recent_style_counts = Counter(
            self._agents[item.agent_id].profile.identity.style
            for item in self._generated_records
            if item.agent_id in self._agents
        )
        return AgentDecisionContext(
            candidate_pool=list(self._candidate_pool),
            recent_agent_ratio=self._recent_agent_ratio(),
            recent_dispatch_total=len(self._dispatch_window),
            recent_format_counts=dict(recent_format_counts),
            recent_style_counts=dict(recent_style_counts),
            candidate_usage=dict(self._candidate_usage),
            max_agent_ratio=self.config.max_agent_ratio,
            max_agents_per_candidate=self.config.max_agents_per_candidate,
            global_exposure_feedback=self._global_exposure_feedback(),
            winner_variant_scores=self._winner_variant_scores(),
        )

    def _agent_can_post(self, agent: CreatorAgent, *, now: datetime) -> bool:
        self._prune_agent_history(agent, now=now)
        return len(agent.post_history) < self.config.max_posts_per_agent_window

    def _can_publish_agent_clip(self) -> bool:
        projected_agent_dispatches = sum(1 for item in self._dispatch_window if item.origin == "agent") + 1
        projected_total_dispatches = len(self._dispatch_window) + 1
        denominator = max(projected_total_dispatches, self.config.ratio_warm_start_denominator)
        projected_ratio = projected_agent_dispatches / max(denominator, 1)
        return projected_ratio <= self.config.max_agent_ratio

    def _feed_pressure(self) -> float:
        return self._recent_agent_ratio() / max(self.config.max_agent_ratio, 0.01)

    def _recent_agent_ratio(self) -> float:
        if not self._dispatch_window:
            return 0.0
        agent_dispatches = sum(1 for item in self._dispatch_window if item.origin == "agent")
        denominator = max(len(self._dispatch_window), self.config.ratio_warm_start_denominator)
        return round(agent_dispatches / max(denominator, 1), 4)

    def _global_exposure_feedback(self) -> dict[str, float]:
        feedback: dict[str, float] = {}
        recent_records = list(self._generated_records)[-10:]
        if not recent_records:
            return feedback
        format_counts = Counter(item.primary_format for item in recent_records)
        total = max(len(recent_records), 1)
        for format_key, count in format_counts.items():
            scarcity = 1.0 - (count / total)
            feedback[format_key] = round(_clamp(scarcity * (1.0 - min(self._feed_pressure(), 1.2) * 0.25), 0.0, 0.6), 4)
        return feedback

    def _winner_variant_scores(self) -> dict[str, float]:
        scores: dict[str, float] = {}
        if self.orchestrator_service is None:
            return scores
        for record in list(self._generated_records)[-10:]:
            try:
                state = self.orchestrator_service.state_store.load_clip(record.clip_id)
            except Exception:
                state = None
            if state is None:
                continue
            metadata = dict(state.metadata or {})
            winner_score = _coerce_float(metadata.get("variant_winner_score"), 0.0)
            if winner_score > 0.0:
                scores[record.primary_format] = max(scores.get(record.primary_format, 0.0), round(winner_score, 4))
        return scores

    def _orchestrator_weight_for(self, clip_id: str) -> float:
        if self.orchestrator_service is None:
            return 0.0
        try:
            state = self.orchestrator_service.state_store.load_clip(clip_id)
        except Exception:
            state = None
        if state is None:
            return 0.0
        return round(self.orchestrator_service.weight_for_state(state), 6)

    def _exposure_feedback_for(self, format_key: str) -> float:
        return round(self._global_exposure_feedback().get(format_key, 0.0), 4)

    def _quality_score(self, *, agent: CreatorAgent, signal: AgentPerformanceSignal) -> float:
        avg_duration = max(int(agent.profile.strategy.avg_duration), 1)
        watch_ratio = _clamp(signal.watch_time / avg_duration, 0.0, 1.0)
        share_signal = _clamp(signal.share_rate / 0.15, 0.0, 1.0)
        comment_signal = _clamp(signal.comment_rate / 0.08, 0.0, 1.0)
        velocity_signal = _clamp(signal.velocity / 1.5, 0.0, 1.0)
        penalty_signal = _clamp(signal.penalties + signal.skip_rate, 0.0, 1.0)
        return round(
            _clamp(
                (signal.completion_rate * 0.40)
                + (watch_ratio * 0.25)
                + (share_signal * 0.15)
                + (comment_signal * 0.05)
                + (velocity_signal * 0.15)
                - (penalty_signal * 0.20),
                0.0,
                1.0,
            ),
            4,
        )

    def _trust_score(self, *, agent: CreatorAgent, signal: AgentPerformanceSignal, quality_score: float) -> float:
        behavior_signal = _clamp(
            1.0 - signal.skip_rate - min(signal.penalties, 1.0),
            0.0,
            1.0,
        )
        return round(
            _clamp(
                (agent.wallet.trust_score * 0.60)
                + (quality_score * 0.25)
                + (behavior_signal * 0.10)
                + (_clamp(signal.share_rate / 0.12, 0.0, 1.0) * 0.05),
                0.0,
                1.0,
            ),
            4,
        )

    def _repetition_ratio(self, *, agent_id: str, primary_format: str) -> float:
        if self.state_store is not None:
            return self.state_store.repetition_ratio(agent_id=agent_id, primary_format=primary_format)
        records = [item for item in list(self._generated_records)[-5:] if item.agent_id == agent_id]
        if not records:
            return 0.0
        repeated = sum(1 for item in records if item.primary_format == primary_format)
        return round(repeated / max(len(records), 1), 4)

    def _prune_windows(self, *, now: datetime) -> None:
        dispatch_threshold = now - timedelta(minutes=self.config.dispatch_window_minutes)
        while self._dispatch_window and self._dispatch_window[0].occurred_at < dispatch_threshold:
            self._dispatch_window.popleft()
        while self._generated_records and self._generated_records[0].created_at < dispatch_threshold:
            removed = self._generated_records.popleft()
            if self._generated_by_clip.get(removed.clip_id) == removed:
                self._generated_by_clip.pop(removed.clip_id, None)
        while len(self._candidate_pool) > self.config.candidate_pool_limit:
            removed_candidate = self._candidate_pool.popleft()
            self._candidate_usage.pop(removed_candidate.candidate_id, None)
        for agent in self._agents.values():
            self._prune_agent_history(agent, now=now)

    def _prune_agent_history(self, agent: CreatorAgent, *, now: datetime) -> None:
        threshold = now - timedelta(minutes=self.config.per_agent_window_minutes)
        while agent.post_history and agent.post_history[0] < threshold:
            agent.post_history.popleft()

    def _ingest_moment_event(self, event: DomainEvent) -> None:
        payload = dict(event.payload or {})
        clip_payload = dict(payload.get("clip") or {})
        boost_payload = dict(payload.get("boost") or {})
        moment = AgentMomentCandidate(
            candidate_id=_coerce_text(payload.get("moment_id")) or event.event_id,
            match_id=_coerce_text(payload.get("match_id")) or event.aggregate_id or "unknown-match",
            source_event_id=_coerce_text(payload.get("source_event_id")) or event.event_id,
            event_type=_coerce_text(payload.get("event_type")) or "generic",
            minute=max(int(payload.get("minute") or 0), 0),
            team_name=_coerce_text(payload.get("team")),
            player_name=_coerce_text(payload.get("player")),
            scoreline_label=_coerce_text(payload.get("scoreline")),
            priority_score=max(float(boost_payload.get("final_score") or 0.0), 0.1),
            detected_events=tuple(str(item) for item in (payload.get("detected_events") or ()) if str(item).strip()),
            storage_key=_coerce_text(clip_payload.get("storage_key")),
            video_url=_coerce_text(clip_payload.get("cdn_path")),
            render_status=_coerce_text(clip_payload.get("render_status")) or "queued",
            created_at=_coerce_datetime(payload.get("created_at")) or event.occurred_at,
            metadata=dict(payload.get("metadata") or {}),
        )
        existing = {item.candidate_id: item for item in self._candidate_pool}
        existing[moment.candidate_id] = moment
        ordered = sorted(existing.values(), key=lambda item: (-item.priority_score, -item.minute, item.candidate_id))
        self._candidate_pool = deque(ordered[: self.config.candidate_pool_limit])

    def _record_dispatch(self, event: DomainEvent) -> None:
        payload = dict(event.payload or {})
        metadata = dict(payload.get("metadata") or {})
        origin = "agent" if metadata.get("origin") == "creator_agent" or payload.get("agent_id") else "external"
        self._dispatch_window.append(DispatchWindowEntry(occurred_at=event.occurred_at, origin=origin))
        self._prune_windows(now=event.occurred_at)

    def _publish_generated_clip(self, generated: AgentGeneratedClip) -> None:
        if self.orchestrator_service is not None:
            orchestrator_state = self.orchestrator_service.inspect_clip(generated.trending_clip)
            if generated.trending_clip.distribution is not None:
                generated.trending_clip.distribution = ViralClipDistributionView(
                    impressions_served=orchestrator_state.consumed_impressions,
                    impressions_cap=orchestrator_state.allocated_impressions,
                    expansion_stage=orchestrator_state.stage,
                    frozen=orchestrator_state.stage == "decay",
                    eligible=orchestrator_state.remaining_impressions > 0,
                    remaining_impressions=orchestrator_state.remaining_impressions,
                    freeze_reason="decay" if orchestrator_state.stage == "decay" else None,
                )
        event = DomainEvent(
            name="viral.clip.dispatch.requested",
            aggregate_id=generated.agent_id,
            aggregate_type="creator_agent",
            partition_key=generated.agent_id,
            producer="creator-agent-manager",
            payload=generated.payload,
        )
        session_factory = getattr(self.app.state, "session_factory", None)
        if session_factory is not None:
            try:
                with session_factory() as session:
                    enqueue_viral_dispatch(
                        session=session,
                        aggregate_id=generated.agent_id,
                        aggregate_type="creator_agent",
                        partition_key=generated.agent_id,
                        producer="creator-agent-manager",
                        payload=generated.payload,
                    )
                    session.commit()
            except Exception:
                logger.exception("agents.dispatch.enqueue_failed agent_id=%s clip_id=%s", generated.agent_id, generated.clip_id)
        if self.event_publisher is not None:
            self.event_publisher.publish(event)
        else:
            self._record_dispatch(event)
        if self.leaderboard_store is not None and self.config.leaderboard_seed_enabled:
            self.leaderboard_store.upsert(
                [
                    LeaderboardEnvelope(
                        clip_id=generated.clip_id,
                        score=float(generated.trending_clip.ranking_score),
                        payload=generated.trending_clip.model_dump(mode="json"),
                    )
                ]
            )

    def _resolve_record(self, payload: AgentPerformanceRequest) -> GeneratedClipRecord:
        if payload.clip_id:
            record = self._generated_by_clip.get(payload.clip_id)
            if record is not None:
                return record
        if payload.agent_id:
            agent_records = [item for item in self._generated_records if item.agent_id == payload.agent_id]
            if agent_records:
                return agent_records[-1]
        raise KeyError("Unknown agent clip.")

    @staticmethod
    def _agent_view(agent: CreatorAgent) -> CreatorAgentView:
        return CreatorAgentView(
            agent_id=agent.profile.identity.agent_id,
            handle=agent.profile.identity.handle,
            display_name=agent.profile.identity.display_name,
            style=agent.profile.identity.style,
            target=agent.profile.identity.target,
            risk_level=agent.profile.strategy.risk_level,
            avg_duration=agent.profile.strategy.avg_duration,
            tempo=agent.profile.strategy.tempo,
            audience_bias=agent.profile.strategy.audience_bias,
            exploration_rate=agent.learning_state.exploration_rate,
            last_reward=agent.learning_state.last_reward,
            average_reward=agent.learning_state.average_reward,
            total_posts=agent.learning_state.total_posts,
            balance=agent.wallet.balance,
            roi=agent.wallet.roi,
            last_generated_clip_id=agent.last_generated_clip_id,
            last_generated_at=agent.last_generated_at,
        )

    @staticmethod
    def _build_agent(index: int) -> CreatorAgent:
        archetypes = (
            {
                "style": "chaotic_meme",
                "target": "young_high_scroll_users",
                "tempo": "fast",
                "audience_bias": "humor",
                "risk_level": 0.78,
                "avg_duration": 10,
                "event_focus": ("goal", "winner", "red_card", "late_drama"),
                "preferred_formats": ("meme_version", "instant_clip", "debate_clip"),
            },
            {
                "style": "tactical_breakdown",
                "target": "match_nerds",
                "tempo": "measured",
                "audience_bias": "league",
                "risk_level": 0.38,
                "avg_duration": 18,
                "event_focus": ("goal", "penalty", "red_card"),
                "preferred_formats": ("tactical_breakdown", "cinematic_replay", "debate_clip"),
            },
            {
                "style": "cinematic_story",
                "target": "story_watchers",
                "tempo": "medium",
                "audience_bias": "drama",
                "risk_level": 0.46,
                "avg_duration": 16,
                "event_focus": ("winner", "equalizer", "late_drama"),
                "preferred_formats": ("cinematic_replay", "instant_clip", "meme_version"),
            },
            {
                "style": "debate_hunter",
                "target": "opinion_clusters",
                "tempo": "fast",
                "audience_bias": "drama",
                "risk_level": 0.62,
                "avg_duration": 12,
                "event_focus": ("goal", "red_card", "penalty"),
                "preferred_formats": ("debate_clip", "instant_clip", "meme_version"),
            },
            {
                "style": "instant_reaction",
                "target": "club_loyalists",
                "tempo": "fast",
                "audience_bias": "club",
                "risk_level": 0.58,
                "avg_duration": 11,
                "event_focus": ("goal", "winner", "equalizer"),
                "preferred_formats": ("instant_clip", "meme_version", "cinematic_replay"),
            },
        )
        archetype = archetypes[(index - 1) % len(archetypes)]
        agent_id = f"agent_{index:04d}"
        display_name = f"Creator Agent {index:04d}"
        return CreatorAgent(
            profile=AgentProfile(
                identity=AgentIdentity(
                    agent_id=agent_id,
                    handle=f"@GTEX{str(archetype['style']).replace('_', '').title()}{index:02d}",
                    display_name=display_name,
                    style=str(archetype["style"]),
                    target=str(archetype["target"]),
                ),
                strategy=AgentStrategy(
                    risk_level=float(archetype["risk_level"]),
                    avg_duration=int(archetype["avg_duration"]),
                    tempo=str(archetype["tempo"]),
                    audience_bias=str(archetype["audience_bias"]),
                    preferred_formats=tuple(str(item) for item in archetype["preferred_formats"]),
                    event_focus=tuple(str(item) for item in archetype["event_focus"]),
                    cadence_minutes=6 + ((index - 1) % 5),
                    experimental_share=0.25 + (((index - 1) % 3) * 0.10),
                ),
            ),
        )


def ensure_creator_agent_manager(app: FastAPI) -> CreatorAgentManager:
    manager = getattr(app.state, "creator_agent_manager", None)
    if isinstance(manager, CreatorAgentManager):
        return manager
    settings = getattr(app.state, "settings", None) or get_settings()
    try:
        orchestrator_service = build_attention_orchestrator_service(app=app)
    except Exception:
        orchestrator_service = None
    manager = CreatorAgentManager(
        app=app,
        event_publisher=getattr(app.state, "event_publisher", None),
        leaderboard_store=ensure_viral_leaderboard_store(app, settings=settings),
        orchestrator_service=orchestrator_service,
        settings=settings,
    )
    manager.bootstrap_population()
    manager.subscribe()
    app.state.creator_agent_manager = manager
    return manager


def bind_creator_agent_manager(app: FastAPI, _context) -> None:
    ensure_creator_agent_manager(app)


def shutdown_creator_agent_manager(app: FastAPI, _context) -> None:
    manager = getattr(app.state, "creator_agent_manager", None)
    if isinstance(manager, CreatorAgentManager):
        manager.close()
    app.state.creator_agent_manager = None


__all__ = [
    "AgentManagerSummaryView",
    "AgentPerformanceReceiptView",
    "AgentPerformanceRequest",
    "AgentRunRequest",
    "AgentRunResponse",
    "AgentRuntimeConfigUpdateRequest",
    "AgentRuntimeConfigView",
    "CreatorAgentManager",
    "CreatorAgentView",
    "GeneratedClipRecord",
    "bind_creator_agent_manager",
    "ensure_creator_agent_manager",
    "shutdown_creator_agent_manager",
]
