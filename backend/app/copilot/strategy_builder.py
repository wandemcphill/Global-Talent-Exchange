from __future__ import annotations

import json
from typing import Any, Mapping

from app.core.cache import CacheBackend, NullCacheBackend, build_cache_backend

PROFILE_TTL_SECONDS = 24 * 60 * 60


class CopilotStrategyBuilder:
    def __init__(self, *, cache_backend: CacheBackend | None = None) -> None:
        self.cache_backend = cache_backend or build_cache_backend()

    @staticmethod
    def profile_key(creator_id: str) -> str:
        return f"creator:{creator_id}:strategy_profile"

    def build(
        self,
        *,
        creator_id: str,
        features: Mapping[str, Any],
        prediction: Mapping[str, Any],
        variant_strategy: Mapping[str, Any],
    ) -> dict[str, Any]:
        creator_metrics = ((features.get("creator_history") or {}).get("insights") or {}).get("creator_metrics") or {}
        winning_formats = self._winning_formats(
            creator_metrics=creator_metrics,
            prediction=prediction,
            variant_strategy=variant_strategy,
        )
        winning_duration = str(creator_metrics.get("optimal_duration") or self._duration_phrase(features))
        audience_cluster = (
            creator_metrics.get("audience_cluster")
            or ((features.get("audience_affinity") or {}).get("dominant_cluster"))
            or "general"
        )
        archetype = self._archetype(
            best_format=str(prediction.get("best_format") or "instant"),
            features=features,
        )
        confidence = self._clamp(
            (float(prediction.get("viral_probability", 0.0)) * 0.75)
            + (min(len(winning_formats), 2) * 0.08)
        )
        summary = self._summary(
            best_format=str(prediction.get("best_format") or "instant"),
            winning_duration=winning_duration,
            features=features,
        )
        payload = {
            "profile_key": self.profile_key(creator_id),
            "archetype": archetype,
            "summary": summary,
            "confidence": round(confidence, 4),
            "winning_formats": winning_formats,
            "winning_duration": winning_duration,
            "audience_cluster": audience_cluster,
        }
        self._store(payload=payload)
        return payload

    def _store(self, *, payload: Mapping[str, Any]) -> None:
        if isinstance(self.cache_backend, NullCacheBackend):
            return
        key = str(payload.get("profile_key") or "")
        if not key:
            return
        self.cache_backend.set(key, json.dumps(payload, default=str), PROFILE_TTL_SECONDS)

    def _winning_formats(
        self,
        *,
        creator_metrics: Mapping[str, Any],
        prediction: Mapping[str, Any],
        variant_strategy: Mapping[str, Any],
    ) -> list[str]:
        ordered: list[str] = []
        for candidate in (
            creator_metrics.get("best_format"),
            prediction.get("best_format"),
            *[item.get("type") for item in (variant_strategy.get("recommended_variants") or [])],
        ):
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            if candidate not in ordered:
                ordered.append(candidate)
        return ordered[:3]

    def _archetype(self, *, best_format: str, features: Mapping[str, Any]) -> str:
        clip_metadata = features.get("clip_metadata") or {}
        event_density = float(clip_metadata.get("event_density", 0.55))
        tempo = str((features.get("current_trends") or {}).get("tempo") or "steady")
        intensity = "chaotic" if event_density >= 0.62 or tempo == "high" else "precise"
        if best_format == "meme":
            return f"{intensity} meme accelerator"
        if best_format == "instant":
            return f"{intensity} instant closer"
        if best_format == "debate":
            return "conversation spike operator"
        if best_format == "tactical":
            return "tactical explainer"
        return "cinematic storyteller"

    def _summary(self, *, best_format: str, winning_duration: str, features: Mapping[str, Any]) -> str:
        clip_metadata = features.get("clip_metadata") or {}
        event_density = float(clip_metadata.get("event_density", 0.55))
        texture = "chaotic" if event_density >= 0.62 else "clean"
        return f"This creator wins with {texture} {best_format} clips {winning_duration}."

    def _duration_phrase(self, features: Mapping[str, Any]) -> str:
        duration_seconds = float((features.get("clip_metadata") or {}).get("duration_seconds", 18.0))
        if duration_seconds < 15:
            return "under 15s"
        if duration_seconds <= 20:
            return "under 20s"
        if duration_seconds <= 30:
            return "around 20-30s"
        if duration_seconds <= 45:
            return "around 30-45s"
        return "over 45s"

    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(value, maximum))


__all__ = ["CopilotStrategyBuilder", "PROFILE_TTL_SECONDS"]
