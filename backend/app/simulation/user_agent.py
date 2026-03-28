from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any


@dataclass(slots=True)
class UserAgent:
    user_id: str
    preferences: dict[str, dict[str, float]] = field(default_factory=dict)
    attention_span: float = 0.5
    engagement_bias: float = 0.5
    share_bias: float = 0.2
    ad_tolerance: float = 0.2

    def __post_init__(self) -> None:
        self.attention_span = min(max(float(self.attention_span), 0.0), 1.0)
        self.engagement_bias = min(max(float(self.engagement_bias), 0.0), 1.0)
        self.share_bias = min(max(float(self.share_bias), 0.0), 1.0)
        self.ad_tolerance = min(max(float(self.ad_tolerance), 0.0), 1.0)

    @classmethod
    def randomized(
        cls,
        *,
        user_id: str,
        formats: list[str] | None = None,
        creators: list[str] | None = None,
        rng: random.Random | None = None,
    ) -> "UserAgent":
        resolved_rng = rng or random.Random()
        format_weights = {
            item: round(resolved_rng.uniform(0.0, 0.35), 4)
            for item in (formats or [])
        }
        creator_weights = {
            item: round(resolved_rng.uniform(0.0, 0.45), 4)
            for item in (creators or [])
        }
        return cls(
            user_id=user_id,
            preferences={
                "formats": format_weights,
                "creators": creator_weights,
                "event_types": {"goal": round(resolved_rng.uniform(0.05, 0.25), 4)},
            },
            attention_span=resolved_rng.uniform(0.35, 0.95),
            engagement_bias=resolved_rng.uniform(0.15, 0.95),
            share_bias=resolved_rng.uniform(0.05, 0.45),
            ad_tolerance=resolved_rng.uniform(0.0, 0.4),
        )

    def react(self, clip: Any, *, rng: random.Random | None = None) -> dict[str, float | bool]:
        resolved_rng = rng or random.Random()
        metadata = dict(getattr(clip, "metadata", {}) or {})
        analytics = getattr(clip, "analytics", None)
        quality = min(max(float(metadata.get("quality_score", 0.5) or 0.5), 0.0), 1.0)
        trust = min(max(float(metadata.get("trust_score", 1.0) or 1.0), 0.0), 1.0)
        creator_id = str(metadata.get("creator_id") or metadata.get("creator_user_id") or "").strip()
        format_key = str(metadata.get("format_key") or getattr(getattr(clip, "editor", None), "format_key", "") or "").strip()
        event_type = str(getattr(clip, "event_type", "") or "").strip()
        creator_preference = float((self.preferences.get("creators") or {}).get(creator_id, 0.0))
        format_preference = float((self.preferences.get("formats") or {}).get(format_key, 0.0))
        event_preference = float((self.preferences.get("event_types") or {}).get(event_type, 0.0))
        base_interest = min(
            max(
                (0.40 * quality)
                + (0.20 * trust)
                + (0.15 * self.attention_span)
                + creator_preference
                + format_preference
                + event_preference
                + (0.10 * self.engagement_bias),
                0.0,
            ),
            1.0,
        )
        if bool(metadata.get("is_ad", False)):
            base_interest = max(base_interest - max(0.25 - self.ad_tolerance, 0.0), 0.0)
        completion_rate = float(getattr(analytics, "completion_rate", 0.6) or 0.6) if analytics is not None else 0.6
        watch_ratio = min(max((base_interest * 0.65) + (completion_rate * 0.35), 0.0), 1.0)
        watch_time = round(watch_ratio * (8.0 + (quality * 18.0)), 2)
        like_probability = min(max(base_interest * self.engagement_bias, 0.0), 1.0)
        share_probability = min(max((base_interest * 0.45) + (self.share_bias * 0.55), 0.0), 1.0)
        skip_probability = min(max(1.0 - watch_ratio, 0.0), 1.0)
        liked = resolved_rng.random() < like_probability
        shared = resolved_rng.random() < share_probability
        skipped = resolved_rng.random() < skip_probability
        return {
            "watch_time": watch_time,
            "like_probability": round(like_probability, 6),
            "share_probability": round(share_probability, 6),
            "skip_probability": round(skip_probability, 6),
            "liked": liked,
            "shared": shared,
            "skipped": skipped,
        }

