from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from fastapi import FastAPI

from app.core.config import get_settings
from app.viral.distribution import ClipDistributionManager, ClipDistributionState, build_clip_distribution_manager
from app.viral.schemas import (
    PersonalizedFeedClipView,
    PersonalizedFeedResponse,
    ViralClipDistributionView,
    ViralTrendingClipView,
    ViralTrendingResponse,
)

_RankedClip = TypeVar("_RankedClip", PersonalizedFeedClipView, ViralTrendingClipView)


@dataclass(slots=True)
class DistributionFilterMiddleware:
    distribution_manager: ClipDistributionManager

    def deliver_personalized_feed_response(
        self,
        response: PersonalizedFeedResponse,
    ) -> PersonalizedFeedResponse:
        return response.model_copy(update={"items": self.deliver_ranked_clips(response.items)})

    def deliver_trending_response(self, response: ViralTrendingResponse) -> ViralTrendingResponse:
        clips = self.deliver_ranked_clips(response.clips)
        reranked = [clip.model_copy(update={"rank": index}) for index, clip in enumerate(clips, start=1)]
        return response.model_copy(update={"clips": reranked})

    def deliver_ranked_clips(self, clips: list[_RankedClip]) -> list[_RankedClip]:
        delivered: list[_RankedClip] = []
        for clip in clips:
            cap_multiplier = _distribution_cap_multiplier(clip)
            state = self.distribution_manager.refresh_distribution(
                clip_id=clip.clip_id,
                viral_score=float(getattr(clip, "viral_score", 0.0) or 0.0),
                analytics=clip.analytics.model_dump(mode="python"),
                performance_tier=getattr(clip.feedback, "performance_tier", None),
                cap_multiplier=cap_multiplier,
            )
            if not self.distribution_manager.is_eligible(state):
                continue
            allocation = self.distribution_manager.allocate_impressions(clip.clip_id, count=1)
            delivered_clip = self._clip_with_distribution(
                clip,
                state=allocation.state,
                cap_multiplier=cap_multiplier,
            )
            if allocation.allocated:
                delivered.append(delivered_clip)
        return delivered

    def _clip_with_distribution(
        self,
        clip: _RankedClip,
        *,
        state: ClipDistributionState,
        cap_multiplier: int,
    ) -> _RankedClip:
        metadata = dict(clip.metadata or {})
        metadata["distribution_key"] = self.distribution_manager.distribution_key(clip.clip_id)
        metadata["distribution_stage"] = state.expansion_stage
        metadata["distribution_frozen"] = state.frozen
        metadata["distribution_cap_multiplier"] = cap_multiplier
        return clip.model_copy(
            update={
                "distribution": ViralClipDistributionView(
                    impressions_served=int(state.impressions_served),
                    impressions_cap=int(state.impressions_cap),
                    expansion_stage=state.expansion_stage,
                    frozen=bool(state.frozen),
                    eligible=bool(state.eligible),
                    remaining_impressions=int(state.remaining_impressions),
                    freeze_reason=state.freeze_reason,
                ),
                "metadata": metadata,
            }
        )


def ensure_distribution_filter_middleware(app: FastAPI) -> DistributionFilterMiddleware:
    middleware = getattr(app.state, "distribution_filter_middleware", None)
    if middleware is None:
        settings = getattr(app.state, "settings", None)
        if settings is None:
            settings = get_settings()
        middleware = DistributionFilterMiddleware(
            distribution_manager=build_clip_distribution_manager(settings=settings)
        )
        app.state.distribution_filter_middleware = middleware
    return middleware


def _distribution_cap_multiplier(clip: PersonalizedFeedClipView | ViralTrendingClipView) -> int:
    metadata = dict(clip.metadata or {})
    cascade_metadata = metadata.get("cascade")
    if not isinstance(cascade_metadata, dict) or not bool(cascade_metadata.get("cascade")):
        return 1
    actions = cascade_metadata.get("actions")
    if not isinstance(actions, dict):
        return 1
    try:
        return max(int(actions.get("distribution_cap_multiplier", 1) or 1), 1)
    except (TypeError, ValueError):
        return 1


__all__ = ["DistributionFilterMiddleware", "ensure_distribution_filter_middleware"]
