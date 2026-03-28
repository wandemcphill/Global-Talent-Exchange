from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.creator_profile import CreatorProfile
from app.models.sponsored_clip import SponsoredClip

RECENT_VIRAL_CLIP_LIMIT = 50
DEFAULT_CREATOR_REPUTATION = 50.0
DEFAULT_DISTRIBUTION_WEIGHT = 1.0


def _clamp(value: float, *, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _default_feedback_state() -> dict[str, Any]:
    return {
        "creator_reputation": DEFAULT_CREATOR_REPUTATION,
        "future_distribution_weight": DEFAULT_DISTRIBUTION_WEIGHT,
        "marketplace_rank_boost": 0.0,
        "recommendation_boost": 0.0,
        "published_campaign_clips": 0,
        "viral_successes": 0,
        "campaign_successes": 0,
        "recent_viral_clip_ids": [],
        "ad_engagement_score": 0.0,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _table_exists(session: Session, table_name: str) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    return bool(inspect(bind).has_table(table_name))


@dataclass(slots=True)
class FeedbackEngine:
    session: Session

    def creator_distribution_weight(self, creator_id: str | None) -> float:
        return _clamp(
            _as_float(self._creator_feedback_state(creator_id).get("future_distribution_weight"), default=1.0),
            minimum=1.0,
            maximum=2.0,
        )

    def creator_marketplace_rank_boost(self, creator_id: str | None) -> float:
        return _clamp(
            _as_float(self._creator_feedback_state(creator_id).get("marketplace_rank_boost"), default=0.0),
            minimum=0.0,
            maximum=20.0,
        )

    def creator_recommendation_boost(self, creator_id: str | None) -> float:
        return _clamp(
            _as_float(self._creator_feedback_state(creator_id).get("recommendation_boost"), default=0.0),
            minimum=0.0,
            maximum=0.5,
        )

    def published_campaign_clips(self, creator_id: str | None) -> int:
        return max(
            0,
            _as_int(self._creator_feedback_state(creator_id).get("published_campaign_clips"), default=0),
        )

    def record_clip_publication(self, *, creator_id: str | None) -> None:
        if creator_id is None:
            return
        profile = self._resolve_creator_profile(creator_id)
        if profile is None:
            return
        state = self._profile_feedback_state(profile)
        state["published_campaign_clips"] = max(0, _as_int(state.get("published_campaign_clips")) + 1)
        self._store_feedback_state(profile, state)

    def record_viral_success(
        self,
        *,
        creator_id: str | None,
        clip_id: str,
        trending_score: float,
        analytics: dict[str, Any] | None = None,
    ) -> None:
        if creator_id is None:
            return
        profile = self._resolve_creator_profile(creator_id)
        if profile is None:
            return
        state = self._profile_feedback_state(profile)
        recent_ids = list(state.get("recent_viral_clip_ids") or [])
        if clip_id in recent_ids:
            return
        recent_ids = ([clip_id] + recent_ids)[:RECENT_VIRAL_CLIP_LIMIT]
        share_rate = _as_float((analytics or {}).get("share_rate"), default=0.0)
        completion_rate = _as_float((analytics or {}).get("completion_rate"), default=0.0)
        reputation_gain = min(12.0, max(trending_score, 0.0) * 12.0)
        state["viral_successes"] = max(0, _as_int(state.get("viral_successes")) + 1)
        state["creator_reputation"] = round(
            _clamp(
                _as_float(state.get("creator_reputation"), default=DEFAULT_CREATOR_REPUTATION) + reputation_gain,
                minimum=0.0,
                maximum=100.0,
            ),
            4,
        )
        state["future_distribution_weight"] = round(
            _clamp(
                1.0
                + (_as_int(state.get("viral_successes")) * 0.05)
                + (share_rate * 0.50)
                + (completion_rate * 0.15),
                minimum=1.0,
                maximum=2.0,
            ),
            4,
        )
        state["recommendation_boost"] = round(
            _clamp(
                _as_float(state.get("recommendation_boost")) + 0.03 + (share_rate * 0.20),
                minimum=0.0,
                maximum=0.50,
            ),
            4,
        )
        state["marketplace_rank_boost"] = round(
            _clamp(
                _as_float(state.get("marketplace_rank_boost")) + 1.25,
                minimum=0.0,
                maximum=20.0,
            ),
            4,
        )
        state["recent_viral_clip_ids"] = recent_ids
        self._store_feedback_state(profile, state)

    def record_campaign_success(
        self,
        *,
        creator_id: str | None,
        campaign_id: str,
        performance_metrics: dict[str, Any] | None,
    ) -> None:
        if creator_id is None:
            return
        profile = self._resolve_creator_profile(creator_id)
        if profile is None:
            return
        metrics = dict(performance_metrics or {})
        views = max(0, _as_int(metrics.get("views")))
        conversions = max(0, _as_int(metrics.get("conversions")))
        engagement_rate = _as_float(metrics.get("engagement_rate"), default=0.0)
        campaign_signal = _clamp(
            min(1.0, views / 2_500.0) + min(1.0, conversions / 30.0) + min(1.0, engagement_rate * 4.0),
            minimum=0.0,
            maximum=1.0,
        )
        state = self._profile_feedback_state(profile)
        state["campaign_successes"] = max(0, _as_int(state.get("campaign_successes")) + 1)
        state["creator_reputation"] = round(
            _clamp(
                _as_float(state.get("creator_reputation"), default=DEFAULT_CREATOR_REPUTATION)
                + (campaign_signal * 8.0),
                minimum=0.0,
                maximum=100.0,
            ),
            4,
        )
        state["marketplace_rank_boost"] = round(
            _clamp(
                _as_float(state.get("marketplace_rank_boost")) + (campaign_signal * 4.5),
                minimum=0.0,
                maximum=20.0,
            ),
            4,
        )
        state["recommendation_boost"] = round(
            _clamp(
                _as_float(state.get("recommendation_boost")) + (campaign_signal * 0.04),
                minimum=0.0,
                maximum=0.50,
            ),
            4,
        )
        state["last_campaign_id"] = campaign_id
        self._store_feedback_state(profile, state)

    def record_interaction_event(self, *, name: str, metadata: dict[str, Any] | None = None) -> None:
        payload = dict(metadata or {})
        creator_id = self._resolve_creator_id(payload)
        if creator_id is None:
            creator_id = self._resolve_creator_id_from_ad(payload)
        if creator_id is None:
            return
        profile = self._resolve_creator_profile(creator_id)
        if profile is None:
            return
        state = self._profile_feedback_state(profile)
        event_name = name.strip().lower()
        if event_name in {"clip.complete", "sponsored_clip.watch"}:
            delta = 0.012 + min(_as_float(payload.get("watch_time_seconds"), default=0.0) / 600.0, 0.02)
            state["recommendation_boost"] = round(
                _clamp(_as_float(state.get("recommendation_boost")) + delta, minimum=0.0, maximum=0.50),
                4,
            )
        elif event_name in {"clip.share", "sponsored_clip.click"}:
            state["recommendation_boost"] = round(
                _clamp(_as_float(state.get("recommendation_boost")) + 0.02, minimum=0.0, maximum=0.50),
                4,
            )
        elif event_name == "clip.scroll":
            state["recommendation_boost"] = round(
                _clamp(_as_float(state.get("recommendation_boost")) - 0.015, minimum=0.0, maximum=0.50),
                4,
            )
        if event_name.startswith("sponsored_clip."):
            ad_delta = 0.02 if event_name in {"sponsored_clip.click", "sponsored_clip.conversion"} else 0.01
            state["ad_engagement_score"] = round(
                _clamp(_as_float(state.get("ad_engagement_score")) + ad_delta, minimum=0.0, maximum=1.0),
                4,
            )
        self._store_feedback_state(profile, state)

    def viral_weight_adjustments(self) -> dict[str, float]:
        if not _table_exists(self.session, SponsoredClip.__tablename__):
            return {
                "completion_rate": 0.0,
                "share_rate": 0.0,
                "comment_rate": 0.0,
                "avg_watch_time": 0.0,
                "skip_penalty": 0.0,
            }
        ads = list(
            self.session.scalars(
                select(SponsoredClip)
                .where(SponsoredClip.impressions_served > 0)
                .order_by(SponsoredClip.updated_at.desc())
                .limit(50)
            ).all()
        )
        if not ads:
            return {
                "completion_rate": 0.0,
                "share_rate": 0.0,
                "comment_rate": 0.0,
                "avg_watch_time": 0.0,
                "skip_penalty": 0.0,
            }

        ctrs = [int(ad.clicks or 0) / max(int(ad.impressions_served or 0), 1) for ad in ads]
        conversion_rates = [int(ad.conversions or 0) / max(int(ad.impressions_served or 0), 1) for ad in ads]
        avg_watch_times = [
            _as_float(ad.total_watch_time_seconds) / max(int(ad.impressions_served or 0), 1)
            for ad in ads
        ]
        ctr = max(fmean(ctrs), 0.0)
        conversion_rate = max(fmean(conversion_rates), 0.0)
        watch_time = max(fmean(avg_watch_times), 0.0)
        return {
            "completion_rate": round(min(0.08, (watch_time / 120.0) + (conversion_rate * 0.25)), 6),
            "share_rate": round(min(0.08, (ctr * 0.20) + (conversion_rate * 0.35)), 6),
            "comment_rate": round(min(0.04, ctr * 0.08), 6),
            "avg_watch_time": round(min(0.05, watch_time / 180.0), 6),
            "skip_penalty": round(min(0.05, (watch_time / 240.0) + (conversion_rate * 0.10)), 6),
        }

    def _creator_feedback_state(self, creator_id: str | None) -> dict[str, Any]:
        profile = self._resolve_creator_profile(creator_id)
        if profile is None:
            return _default_feedback_state()
        return self._profile_feedback_state(profile)

    def _profile_feedback_state(self, profile: CreatorProfile) -> dict[str, Any]:
        payload = dict(profile.payout_config_json or {})
        stored = payload.get("feedback_engine")
        if not isinstance(stored, dict):
            return _default_feedback_state()
        state = _default_feedback_state()
        state.update(stored)
        return state

    def _store_feedback_state(self, profile: CreatorProfile, state: dict[str, Any]) -> None:
        payload = dict(profile.payout_config_json or {})
        state["updated_at"] = datetime.now(UTC).isoformat()
        payload["feedback_engine"] = state
        profile.payout_config_json = payload
        self.session.flush()

    def _resolve_creator_profile(self, creator_id: str | None) -> CreatorProfile | None:
        if creator_id is None:
            return None
        profile = self.session.get(CreatorProfile, creator_id)
        if profile is not None:
            return profile
        return self.session.scalar(
            select(CreatorProfile).where(
                (CreatorProfile.user_id == creator_id) | (CreatorProfile.handle == creator_id)
            )
        )

    def _resolve_creator_id(self, payload: dict[str, Any]) -> str | None:
        value = payload.get("creator_id") or payload.get("creator_key")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _resolve_creator_id_from_ad(self, payload: dict[str, Any]) -> str | None:
        ad_id = payload.get("ad_id")
        if not isinstance(ad_id, str) or not ad_id.strip():
            return None
        ad = self.session.get(SponsoredClip, ad_id)
        if ad is None:
            return None
        metadata = dict(ad.clip_payload_json or {}).get("metadata")
        if not isinstance(metadata, dict):
            return None
        creator_id = metadata.get("creator_id")
        if isinstance(creator_id, str) and creator_id.strip():
            return creator_id.strip()
        return None


__all__ = ["FeedbackEngine"]
