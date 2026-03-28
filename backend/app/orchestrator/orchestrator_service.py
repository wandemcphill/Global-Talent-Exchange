from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import ceil
from typing import Any, Protocol

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.infrastructure.outbox import OutboxEvent
from app.orchestrator.exposure_allocator import ExposureAllocator
from app.orchestrator.global_state import (
    AttentionOrchestratorConfig,
    ClipGlobalState,
    DECAY_STAGE,
    EXPAND_STAGE,
    GlobalFeedStateStore,
    TEST_STAGE,
    VIRAL_STAGE,
    build_global_feed_state_store,
)
from app.orchestrator.schemas import (
    AttentionOrchestratorConfigUpdateRequest,
    AttentionOrchestratorConfigView,
    AttentionOrchestratorMetricsView,
    BaseCommand,
    ClipAttentionStateView,
    CompleteMatchCommand,
    StartMatchCommand,
)
from app.orchestrator.variant_budget_manager import VariantBudgetManager


class CommandDispatcher(Protocol):
    def dispatch(self, command: BaseCommand) -> OutboxEvent:
        ...


class OrchestratorService:
    def __init__(
        self,
        command_bus: CommandDispatcher,
    ) -> None:
        self._command_bus = command_bus

    def start_match(self, payload: Mapping[str, Any] | None) -> OutboxEvent:
        normalized_payload = dict(payload or {})
        command = StartMatchCommand(payload=normalized_payload)
        return self._command_bus.dispatch(command)

    def complete_match(self, result: Mapping[str, Any] | None) -> OutboxEvent:
        normalized_result = dict(result or {})
        command = CompleteMatchCommand(result=normalized_result)
        return self._command_bus.dispatch(command)


@dataclass(slots=True)
class AttentionOrchestratorService:
    state_store: GlobalFeedStateStore
    session: Session | None = None
    settings: Settings | None = None
    exposure_allocator: ExposureAllocator | None = None
    variant_budget_manager: VariantBudgetManager | None = None
    _config: AttentionOrchestratorConfig | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        self._refresh_components()

    def config(self) -> AttentionOrchestratorConfig:
        if self._config is None:
            self._refresh_components()
        assert self._config is not None
        return self._config

    def get_config_view(self) -> AttentionOrchestratorConfigView:
        config = self.config()
        return AttentionOrchestratorConfigView(**config.as_payload())

    def update_config(self, payload: AttentionOrchestratorConfigUpdateRequest) -> AttentionOrchestratorConfigView:
        current = self.config()
        merged = current.as_payload()
        merged.update(payload.model_dump(exclude_none=True))
        saved = self.state_store.save_config(AttentionOrchestratorConfig.from_payload(merged))
        self._config = saved
        self._refresh_components()
        return self.get_config_view()

    def filter_available(self, clips: list[Any]) -> list[Any]:
        available: list[Any] = []
        for clip in clips:
            state = self.refresh_clip_state(clip)
            if state.available:
                available.append(clip)
        return available

    def refresh_clip_state(self, clip: Any) -> ClipGlobalState:
        existing = self.state_store.load_clip(self._clip_id(clip))
        next_state = self._build_state_from_clip(clip, existing=existing)
        saved = self.state_store.save_clip(next_state)
        self._sync_variant_budgets(saved)
        self._annotate_clip(clip, saved)
        return saved

    def inspect_clip(self, clip: Any) -> ClipAttentionStateView:
        state = self.refresh_clip_state(clip)
        return self._state_view(state)

    def weight_for_clip(self, clip: Any) -> float:
        state = self.refresh_clip_state(clip)
        return self.weight_for_state(state)

    def weight_for_state(self, state: ClipGlobalState) -> float:
        allocator = self.exposure_allocator or ExposureAllocator(config=self.config())
        return round(max(allocator.allocate(state), 0.0001), 6)

    def session_boost_for(self, user: Any, clip: Any) -> float:
        preferences = self._preferences_payload(user)
        boost = 1.0
        format_key = self._format_key(clip)
        creator_id = self._creator_id(clip)
        event_type = _coerce_text(getattr(clip, "event_type", None))
        if format_key is not None:
            boost += _float_from_mapping(preferences.get("formats"), format_key)
        if creator_id is not None:
            boost += _float_from_mapping(preferences.get("creators"), creator_id)
        if event_type is not None:
            boost += _float_from_mapping(preferences.get("event_types"), event_type)
        return round(max(boost, 0.1), 6)

    def generate_feed(self, *, user: Any, clips: list[Any], limit: int = 10) -> list[Any]:
        available = self.filter_available(clips)
        ranked = sorted(
            available,
            key=lambda clip: (
                -(self.weight_for_clip(clip) * self.session_boost_for(user, clip)),
                str(self._clip_id(clip)),
            ),
        )
        balanced = self._rebalance_origin_mix(ranked, limit=max(int(limit), 1))
        return self.allocate_impressions(balanced, limit=max(int(limit), 1))

    def allocate_impressions(self, clips: list[Any], *, limit: int | None = None, count_per_clip: int = 1) -> list[Any]:
        balanced = self._rebalance_origin_mix(clips, limit=limit)
        allocated: list[Any] = []
        for clip in balanced:
            clip_id = self._clip_id(clip)
            state = self.refresh_clip_state(clip)
            if state.stage == DECAY_STAGE or state.consumed_impressions >= state.allocated_impressions:
                continue
            allocation = self.state_store.allocate_clip(clip_id, count=max(int(count_per_clip), 1))
            if not allocation.allocated:
                continue
            self._sync_variant_budgets(allocation.state)
            self._annotate_clip(clip, allocation.state)
            allocated.append(clip)
            if limit is not None and len(allocated) >= max(int(limit), 0):
                break
        return allocated

    def metrics(self, *, sample_limit: int = 10) -> AttentionOrchestratorMetricsView:
        states = self.state_store.list_clips(limit=max(int(sample_limit) * 5, 50))
        stage_distribution: Counter[str] = Counter()
        total_allocated = 0
        total_consumed = 0
        ad_clip_count = 0
        moment_clip_count = 0
        available_clip_count = 0
        for state in states:
            stage_distribution[state.stage] += 1
            total_allocated += int(state.allocated_impressions)
            total_consumed += int(state.consumed_impressions)
            if state.is_ad:
                ad_clip_count += 1
            if state.is_moment:
                moment_clip_count += 1
            if state.available:
                available_clip_count += 1
        sample = sorted(
            states,
            key=lambda item: (-self.weight_for_state(item), item.clip_id),
        )[: max(int(sample_limit), 0)]
        return AttentionOrchestratorMetricsView(
            clip_count=len(states),
            total_allocated_impressions=total_allocated,
            total_consumed_impressions=total_consumed,
            available_clip_count=available_clip_count,
            stage_distribution=dict(stage_distribution),
            ad_clip_count=ad_clip_count,
            moment_clip_count=moment_clip_count,
            sample_clips=[self._state_view(state) for state in sample],
            updated_at=datetime.now(UTC),
        )

    def _refresh_components(self) -> None:
        self._config = self.state_store.load_config()
        self.exposure_allocator = ExposureAllocator(config=self._config)
        self.variant_budget_manager = VariantBudgetManager(session=self.session, config=self._config)

    def _build_state_from_clip(self, clip: Any, *, existing: ClipGlobalState | None) -> ClipGlobalState:
        config = self.config()
        metadata = self._metadata(clip)
        candidate = ClipGlobalState(
            clip_id=self._clip_id(clip),
            stage=existing.stage if existing is not None else self._stage_hint(clip, metadata),
            allocated_impressions=existing.allocated_impressions if existing is not None else int(config.test_impressions_cap),
            consumed_impressions=existing.consumed_impressions if existing is not None else 0,
            velocity_score=self._velocity_score(clip, metadata, existing=existing),
            quality_score=self._quality_score(clip, metadata, existing=existing),
            trust_score=self._trust_score(clip, metadata, existing=existing),
            is_ad=self._is_ad(clip, metadata, existing=existing),
            is_moment=self._is_moment(clip, metadata, existing=existing),
            bid_weight=self._bid_weight(clip, metadata, existing=existing),
            age_hours=self._age_hours(clip, metadata, existing=existing),
            base_clip_id=self._base_clip_id(clip, existing=existing),
            winner_variant_id=existing.winner_variant_id if existing is not None else None,
            metadata=self._state_metadata(clip, metadata, existing=existing),
            updated_at=datetime.now(UTC),
        )
        candidate.stage = self.exposure_allocator.stage_for(candidate) if self.exposure_allocator is not None else candidate.stage
        candidate.allocated_impressions = (
            self.exposure_allocator.cap_for(
                candidate,
                previous_cap=existing.allocated_impressions if existing is not None else None,
            )
            if self.exposure_allocator is not None
            else candidate.allocated_impressions
        )
        if existing is not None and existing.stage == candidate.stage:
            candidate.allocated_impressions = max(existing.allocated_impressions, existing.consumed_impressions)
        if candidate.stage == DECAY_STAGE:
            candidate.allocated_impressions = max(candidate.consumed_impressions, candidate.allocated_impressions)
        if candidate.age_hours <= float(config.new_clip_age_hours):
            candidate.allocated_impressions = max(
                candidate.allocated_impressions,
                int(config.new_clip_minimum_impressions),
            )
        if self.variant_budget_manager is not None:
            candidate.winner_variant_id = self.variant_budget_manager.resolve_winner_variant_id(candidate.clip_id)
        return candidate

    def _sync_variant_budgets(self, state: ClipGlobalState) -> None:
        if self.variant_budget_manager is None:
            return
        splits = self.variant_budget_manager.sync(state)
        if not splits:
            return
        state.metadata["variant_budget_splits"] = [
            {
                "variant_id": split.variant_id,
                "share": round(split.share, 4),
                "allocated_impressions": int(split.allocated_impressions),
                "locked": bool(split.locked),
                "viral_score": round(split.viral_score, 4),
                "global_exposure_feedback": round(split.global_exposure_feedback, 4),
            }
            for split in splits
        ]
        state.metadata["global_exposure_feedback"] = round(
            max((split.global_exposure_feedback for split in splits), default=0.0),
            4,
        )
        state.metadata["variant_winner_score"] = round(
            max(
                (
                    split.viral_score
                    if split.viral_score <= 1.0
                    else (split.viral_score / 100.0)
                    for split in splits
                ),
                default=0.0,
            ),
            4,
        )
        winner = next((split for split in splits if split.locked and split.share > 0.0), None)
        if winner is not None:
            state.winner_variant_id = winner.variant_id
            state.metadata["winner_variant_id"] = winner.variant_id
        self.state_store.save_clip(state)

    def _state_view(self, state: ClipGlobalState) -> ClipAttentionStateView:
        return ClipAttentionStateView(
            clip_id=state.clip_id,
            stage=state.stage,
            allocated_impressions=int(state.allocated_impressions),
            consumed_impressions=int(state.consumed_impressions),
            remaining_impressions=int(state.remaining_impressions),
            velocity_score=round(state.velocity_score, 6),
            quality_score=round(state.quality_score, 6),
            trust_score=round(state.trust_score, 6),
            orchestrator_weight=self.weight_for_state(state),
            is_ad=bool(state.is_ad),
            is_moment=bool(state.is_moment),
            winner_variant_id=state.winner_variant_id,
            metadata=dict(state.metadata),
            updated_at=state.updated_at,
        )

    def _annotate_clip(self, clip: Any, state: ClipGlobalState) -> None:
        view = self._state_view(state)
        metadata = self._metadata(clip)
        metadata["orchestrator"] = view.model_dump(mode="json")
        metadata["orchestrator_weight"] = view.orchestrator_weight
        if hasattr(clip, "metadata"):
            try:
                clip.metadata = metadata
            except Exception:
                pass
        if hasattr(clip, "orchestrator"):
            try:
                clip.orchestrator = view
            except Exception:
                pass

    @staticmethod
    def _clip_id(clip: Any) -> str:
        value = getattr(clip, "clip_id", None)
        text = _coerce_text(value)
        if text is None:
            raise ValueError("Clip is missing clip_id.")
        return text

    @staticmethod
    def _metadata(clip: Any) -> dict[str, Any]:
        payload = getattr(clip, "metadata", {}) or {}
        if isinstance(payload, Mapping):
            return dict(payload)
        return {}

    @staticmethod
    def _format_key(clip: Any) -> str | None:
        editor = getattr(clip, "editor", None)
        if editor is not None:
            value = getattr(editor, "format_key", None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        metadata = getattr(clip, "metadata", {}) or {}
        if isinstance(metadata, Mapping):
            for key in ("format_key", "format_type"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    def _creator_id(clip: Any) -> str | None:
        metadata = getattr(clip, "metadata", {}) or {}
        if isinstance(metadata, Mapping):
            for key in ("creator_user_id", "creator_id", "author_user_id"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        distribution_accounts = getattr(clip, "distribution_accounts", None) or []
        if distribution_accounts:
            handle = getattr(distribution_accounts[0], "handle", None)
            if isinstance(handle, str) and handle.strip():
                return handle.strip()
        return None

    def _stage_hint(self, clip: Any, metadata: Mapping[str, Any]) -> str:
        candidate = _coerce_text(metadata.get("distribution_stage"))
        if candidate in {TEST_STAGE, EXPAND_STAGE, VIRAL_STAGE, DECAY_STAGE}:
            return candidate
        distribution = getattr(clip, "distribution", None)
        if distribution is not None:
            candidate = _coerce_text(getattr(distribution, "expansion_stage", None))
            if candidate in {TEST_STAGE, EXPAND_STAGE, VIRAL_STAGE, DECAY_STAGE}:
                return candidate
        return TEST_STAGE

    def _velocity_score(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> float:
        orchestrator_payload = metadata.get("orchestrator")
        if isinstance(orchestrator_payload, Mapping) and orchestrator_payload.get("velocity_score") is not None:
            return max(_coerce_float(orchestrator_payload.get("velocity_score"), 1.0), 0.0)
        trending_metrics = getattr(clip, "trending_metrics", None)
        if trending_metrics is not None:
            velocity = getattr(trending_metrics, "velocity", None)
            if velocity is not None:
                return max(float(velocity), 0.0)
        analytics = getattr(clip, "analytics", None)
        if analytics is not None:
            views_last_10min = max(int(getattr(analytics, "views_last_10min", 0) or 0), 0)
            views_last_60min = max(int(getattr(analytics, "views_last_60min", 0) or 0), 0)
            if views_last_60min > 0:
                return round(max(views_last_10min / max(views_last_60min, 1), 0.0) * 6.0, 6)
        if existing is not None:
            return existing.velocity_score
        return 1.0

    def _quality_score(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> float:
        orchestrator_payload = metadata.get("orchestrator")
        if isinstance(orchestrator_payload, Mapping) and orchestrator_payload.get("quality_score") is not None:
            return min(max(_coerce_float(orchestrator_payload.get("quality_score"), 0.5), 0.0), 1.0)
        quality_hint = metadata.get("quality_score")
        if quality_hint is not None:
            return min(max(_coerce_float(quality_hint, 0.5), 0.0), 1.0)
        analytics = getattr(clip, "analytics", None)
        if analytics is not None:
            completion_rate = min(max(_coerce_float(getattr(analytics, "completion_rate", 0.0), 0.0), 0.0), 1.0)
            share_rate = min(max(_coerce_float(getattr(analytics, "share_rate", 0.0), 0.0), 0.0), 1.0)
            comment_rate = min(max(_coerce_float(getattr(analytics, "comment_rate", 0.0), 0.0), 0.0), 1.0)
            loop_rate = min(max(_coerce_float(getattr(analytics, "loop_rate", 0.0), 0.0), 0.0), 1.0)
            return round(min((0.45 * completion_rate) + (1.5 * share_rate) + comment_rate + (0.35 * loop_rate), 1.0), 6)
        if existing is not None:
            return existing.quality_score
        return 0.5

    def _trust_score(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> float:
        for key in ("trust_score", "clip_trust_score", "avg_trust_score"):
            value = metadata.get(key)
            if value is not None:
                return min(max(_coerce_float(value, 1.0), 0.0), 1.0)
        orchestrator_payload = metadata.get("orchestrator")
        if isinstance(orchestrator_payload, Mapping) and orchestrator_payload.get("trust_score") is not None:
            return min(max(_coerce_float(orchestrator_payload.get("trust_score"), 1.0), 0.0), 1.0)
        if existing is not None:
            return existing.trust_score
        return 1.0

    def _is_ad(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> bool:
        if metadata.get("is_ad") is not None:
            return bool(metadata.get("is_ad"))
        if existing is not None:
            return existing.is_ad
        return False

    def _is_moment(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> bool:
        if metadata.get("is_moment") is not None:
            return bool(metadata.get("is_moment"))
        cascade = metadata.get("cascade")
        if isinstance(cascade, Mapping) and bool(cascade.get("cascade")):
            return True
        event_type = _coerce_text(getattr(clip, "event_type", None))
        if event_type in {"goal", "winner", "equalizer", "penalty_goal", "red_card", "late_drama"}:
            return True
        if existing is not None:
            return existing.is_moment
        return False

    def _bid_weight(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> float:
        if metadata.get("bid_weight") is not None:
            return max(_coerce_float(metadata.get("bid_weight"), 1.0), 0.0)
        if existing is not None:
            return existing.bid_weight
        return 1.0

    def _age_hours(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> float:
        published_at = metadata.get("published_at")
        if isinstance(published_at, str):
            try:
                parsed = datetime.fromisoformat(published_at)
            except ValueError:
                parsed = None
            if parsed is not None:
                resolved = parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
                return max((datetime.now(UTC) - resolved.astimezone(UTC)).total_seconds() / 3600.0, 0.0)
        if existing is not None:
            return existing.age_hours
        return 0.0

    def _base_clip_id(self, clip: Any, *, existing: ClipGlobalState | None) -> str | None:
        metadata = self._metadata(clip)
        if isinstance(metadata.get("base_clip_id"), str) and str(metadata.get("base_clip_id")).strip():
            return str(metadata.get("base_clip_id")).strip()
        clip_id = self._clip_id(clip)
        if clip_id.count("::") >= 2:
            parts = clip_id.split("::")
            return f"{parts[0]}::{parts[1]}"
        if existing is not None:
            return existing.base_clip_id
        return clip_id

    def _state_metadata(self, clip: Any, metadata: Mapping[str, Any], *, existing: ClipGlobalState | None) -> dict[str, Any]:
        payload = dict(existing.metadata) if existing is not None else {}
        payload.update(
            {
                "event_type": _coerce_text(getattr(clip, "event_type", None)),
                "creator_id": self._creator_id(clip),
                "format_key": self._format_key(clip),
                "team_name": _coerce_text(getattr(clip, "team_name", None)),
                "base_clip_id": self._base_clip_id(clip, existing=existing),
                "origin": _coerce_text(metadata.get("origin")),
                "agent_id": _coerce_text(metadata.get("agent_id")),
                "is_agent_generated": bool(metadata.get("is_agent_generated", False)),
            }
        )
        return {key: value for key, value in payload.items() if value is not None}

    def _rebalance_origin_mix(self, clips: list[Any], *, limit: int | None = None) -> list[Any]:
        if not clips:
            return []
        max_items = max(int(limit if limit is not None else len(clips)), 0)
        if max_items <= 0:
            return []
        ranked = list(clips)
        if len(ranked) <= 1:
            return ranked[:max_items]

        human_available = sum(1 for clip in ranked if not self._is_agent_clip(clip))
        agent_available = len(ranked) - human_available
        if human_available == 0 or agent_available == 0:
            return ranked[:max_items]

        config = self.config()
        human_target = min(human_available, max_items, ceil(max_items * float(config.min_human_exposure_guarantee)))
        agent_cap = min(agent_available, max_items, int(max_items * float(config.max_agent_feed_ratio)))

        selected: list[Any] = []
        selected_clip_ids: set[str] = set()
        human_count = 0
        agent_count = 0

        def append_clip(candidate: Any) -> None:
            nonlocal human_count, agent_count
            clip_id = self._clip_id(candidate)
            if clip_id in selected_clip_ids or len(selected) >= max_items:
                return
            selected.append(candidate)
            selected_clip_ids.add(clip_id)
            if self._is_agent_clip(candidate):
                agent_count += 1
            else:
                human_count += 1

        for clip in ranked:
            if len(selected) >= max_items:
                break
            if self._is_agent_clip(clip):
                if human_count < human_target or agent_count >= agent_cap:
                    continue
            elif human_count >= human_target:
                continue
            append_clip(clip)

        for clip in ranked:
            if len(selected) >= max_items:
                break
            if self._is_agent_clip(clip):
                continue
            append_clip(clip)

        for clip in ranked:
            if len(selected) >= max_items:
                break
            if not self._is_agent_clip(clip):
                continue
            if agent_count >= agent_cap and human_count >= min(human_available, max_items):
                append_clip(clip)
                continue
            if agent_count >= agent_cap:
                continue
            append_clip(clip)

        if len(selected) < max_items:
            for clip in ranked:
                if len(selected) >= max_items:
                    break
                append_clip(clip)

        return selected[:max_items]

    @staticmethod
    def _is_agent_clip(clip: Any) -> bool:
        metadata = AttentionOrchestratorService._metadata(clip)
        origin = _coerce_text(metadata.get("origin"))
        if origin == "creator_agent":
            return True
        if bool(metadata.get("is_agent_generated", False)):
            return True
        if _coerce_text(metadata.get("agent_id")) is not None:
            return True
        return _coerce_text(getattr(clip, "agent_id", None)) is not None

    @staticmethod
    def _preferences_payload(user: Any) -> dict[str, Any]:
        raw = getattr(user, "preferences", None)
        if isinstance(raw, Mapping):
            return dict(raw)
        return {}


def ensure_attention_orchestrator_store(app: FastAPI, *, settings: Settings | None = None) -> GlobalFeedStateStore:
    store = getattr(app.state, "attention_orchestrator_store", None)
    if store is None:
        store = build_global_feed_state_store(settings=settings or getattr(app.state, "settings", None))
        app.state.attention_orchestrator_store = store
    return store


def build_attention_orchestrator_service(*, app: FastAPI, session: Session | None = None) -> AttentionOrchestratorService:
    settings = getattr(app.state, "settings", None) or get_settings()
    return AttentionOrchestratorService(
        state_store=ensure_attention_orchestrator_store(app, settings=settings),
        session=session,
        settings=settings,
    )


def _coerce_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _coerce_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _float_from_mapping(value: object, key: str) -> float:
    if not isinstance(value, Mapping):
        return 0.0
    return max(_coerce_float(value.get(key), 0.0), 0.0)


__all__ = [
    "AttentionOrchestratorService",
    "CommandDispatcher",
    "OrchestratorService",
    "build_attention_orchestrator_service",
    "ensure_attention_orchestrator_store",
]
