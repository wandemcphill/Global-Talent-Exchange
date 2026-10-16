from __future__ import annotations

from dataclasses import dataclass

from app.orchestrator.global_state import AttentionOrchestratorConfig, ClipGlobalState


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


@dataclass(slots=True)
class ExposureAllocator:
    config: AttentionOrchestratorConfig = AttentionOrchestratorConfig()

    def allocate(self, clip: ClipGlobalState) -> float:
        score = max(float(clip.quality_score), 0.0) * max(float(clip.velocity_score), 0.0) * max(float(clip.trust_score), 0.0)
        metadata = dict(clip.metadata or {})
        winner_variant_score = max(_as_float(metadata.get("variant_winner_score"), 0.0), 0.0)
        global_exposure_feedback = max(_as_float(metadata.get("global_exposure_feedback"), 0.0), 0.0)
        if winner_variant_score > 0.0:
            score *= 0.85 + min(winner_variant_score, 1.0) * 0.30
        if global_exposure_feedback > 0.0:
            score *= 1.0 + min(global_exposure_feedback, 0.35)
        if clip.is_moment:
            score *= max(float(self.config.moment_boost), 1.0)
        if clip.is_ad:
            score *= max(float(clip.bid_weight), 0.0)
        return round(max(score, 0.0), 6)

    def stage_for(self, clip: ClipGlobalState) -> str:
        if clip.stage == "decay":
            return "decay"
        velocity = max(float(clip.velocity_score), 0.0)
        quality = max(float(clip.quality_score), 0.0)
        trust = max(float(clip.trust_score), 0.0)
        if velocity <= float(self.config.decay_threshold) and clip.consumed_impressions >= clip.allocated_impressions:
            return "decay"
        if velocity >= float(self.config.viral_threshold) or (quality >= 0.75 and trust >= 0.8):
            return "viral"
        if velocity >= float(self.config.expand_threshold) or quality >= 0.55:
            return "expand"
        return "test"

    def cap_for(self, clip: ClipGlobalState, *, previous_cap: int | None = None) -> int:
        prior_cap = max(int(previous_cap or clip.allocated_impressions or self.config.test_impressions_cap), 0)
        stage = self.stage_for(clip)
        if stage == "test":
            cap = max(int(self.config.test_impressions_cap), prior_cap, int(self.config.new_clip_minimum_impressions))
        elif stage == "expand":
            base_cap = max(prior_cap, int(self.config.test_impressions_cap))
            cap = int(round(base_cap * max(float(self.config.expand_multiplier), 1.0)))
        elif stage == "viral":
            dynamic_cap = int(
                round(
                    max(int(self.config.viral_base_cap), prior_cap)
                    + (max(float(clip.velocity_score), 0.0) * float(self.config.viral_velocity_cap_multiplier))
                )
            )
            cap = max(dynamic_cap, int(self.config.viral_base_cap), prior_cap)
        else:
            cap = max(prior_cap, int(clip.consumed_impressions))
        if clip.age_hours <= float(self.config.new_clip_age_hours):
            cap = max(cap, int(self.config.new_clip_minimum_impressions))
        return max(cap, int(clip.consumed_impressions))


__all__ = ["ExposureAllocator"]
