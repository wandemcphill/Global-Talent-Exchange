from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Protocol

import requests

from app.core.config import Settings


def _extract_llm_text(payload: dict[str, Any]) -> str | None:
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                text = chunk.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    text = payload.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _as_float(value: object, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: object, *, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bounded_ratio(value: object, *, denominator: float | None = None) -> float:
    numeric = _as_float(value, default=0.0)
    if denominator and denominator > 0 and numeric > 1.0:
        numeric = numeric / denominator
    elif 1.0 < numeric <= 100.0:
        numeric = numeric / 100.0
    return round(max(0.0, min(numeric, 1.0)), 4)


def _completion_rate(metrics: Mapping[str, Any], *, views: int) -> float:
    if "completion" in metrics:
        return _bounded_ratio(metrics["completion"])
    if "completion_rate" in metrics:
        return _bounded_ratio(metrics["completion_rate"])
    return _bounded_ratio(metrics.get("completions", 0.0), denominator=float(views))


def _loop_rate(metrics: Mapping[str, Any], *, views: int) -> float:
    if "loop_rate" in metrics:
        return _bounded_ratio(metrics["loop_rate"])
    return _bounded_ratio(metrics.get("loops", metrics.get("rewatches", 0.0)), denominator=float(views))


def track_clip(clip_id: str, metrics: Mapping[str, Any]) -> dict[str, Any]:
    views = max(
        1,
        _as_int(
            metrics.get("views", metrics.get("view_count", metrics.get("impressions", 1))),
            default=1,
        ),
    )
    total_watch_time = round(
        max(
            0.0,
            _as_float(
                metrics.get("total_watch_time", metrics.get("watch_time_total", 0.0)),
                default=0.0,
            ),
        ),
        2,
    )
    watch_time = round(
        max(0.0, _as_float(metrics.get("watch_time", metrics.get("avg_watch_time", 0.0)), default=0.0)),
        2,
    )
    if watch_time <= 0.0 and total_watch_time > 0.0:
        watch_time = round(total_watch_time / views, 2)
    if total_watch_time <= 0.0 and watch_time > 0.0:
        total_watch_time = round(watch_time * views, 2)

    completion_rate = _completion_rate(metrics, views=views)
    completions = max(
        0,
        _as_int(
            metrics.get("completions"),
            default=int(round(completion_rate * views)),
        ),
    )
    completions = min(completions, views)
    if "completion" not in metrics and "completion_rate" not in metrics:
        completion_rate = round(max(0.0, min(completions / views, 1.0)), 4)

    loop_rate = _loop_rate(metrics, views=views)
    loops = round(
        max(
            0.0,
            _as_float(
                metrics.get("loops", metrics.get("rewatches", loop_rate * views)),
                default=loop_rate * views,
            ),
        ),
        2,
    )
    if "loop_rate" not in metrics and "loops" not in metrics and "rewatches" not in metrics:
        loop_rate = round(max(0.0, loops / views), 4)

    shares = max(0, _as_int(metrics.get("shares"), default=0))
    comments = max(0, _as_int(metrics.get("comments"), default=0))
    skips = max(0, _as_int(metrics.get("skips"), default=max(views - completions, 0)))
    views_last_10min = max(0, _as_int(metrics.get("views_last_10min"), default=0))
    views_last_60min = max(0, _as_int(metrics.get("views_last_60min"), default=0))
    share_rate = round(max(0.0, shares / views), 4)
    comment_rate = round(max(0.0, comments / views), 4)

    drop_off_value = metrics.get("drop_off_point", metrics.get("drop_off_point_seconds"))
    drop_off_point = round(max(0.0, _as_float(drop_off_value, default=0.0)), 2) if drop_off_value is not None else None

    return {
        "clip_id": clip_id,
        "view_count": views,
        "completions": completions,
        "watch_time": watch_time,
        "total_watch_time": total_watch_time,
        "loops": loops,
        "loop_rate": loop_rate,
        "shares": shares,
        "comments": comments,
        "skips": skips,
        "completion_rate": completion_rate,
        "drop_off_point_seconds": drop_off_point,
        "share_rate": share_rate,
        "comment_rate": comment_rate,
        "views_last_10min": views_last_10min,
        "views_last_60min": views_last_60min,
    }


@dataclass(slots=True)
class ClipOptimizationFeedback:
    performance_tier: str
    recommendation: str
    increase_similar_clips: bool
    adjust_captions: bool
    shorten_clips: bool
    actions: list[str]
    viral_analysis: str
    analysis_source: str


class ViralityInsightLLMClient(Protocol):
    provider_name: str

    def generate(self, prompt: dict[str, Any]) -> str | None:
        ...


@dataclass(slots=True)
class NullViralityInsightLLMClient:
    provider_name: str = "heuristic"

    def generate(self, prompt: dict[str, Any]) -> str | None:
        return None


@dataclass(slots=True)
class RemoteViralityInsightLLMClient:
    enabled: bool = False
    endpoint_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 8
    provider_name: str = "remote-llm"

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "RemoteViralityInsightLLMClient":
        if settings is None:
            return cls()
        return cls(
            enabled=bool(settings.social_content_llm_enabled),
            endpoint_url=settings.social_content_llm_endpoint_url,
            model=settings.social_content_llm_model,
            api_key=settings.social_content_llm_api_key,
            timeout_seconds=settings.social_content_llm_timeout_seconds,
        )

    def generate(self, prompt: dict[str, Any]) -> str | None:
        if not self.enabled or not self.endpoint_url or not self.model:
            return None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You analyze short-form football clip performance. "
                                "Answer the question 'Why did this clip go viral?' in 2 concise sentences."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(prompt, ensure_ascii=True),
                        }
                    ],
                },
            ],
            "temperature": 0.4,
            "max_output_tokens": 120,
        }
        try:
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                json=body,
                timeout=max(self.timeout_seconds, 1),
            )
            response.raise_for_status()
        except Exception:
            return None
        return _extract_llm_text(response.json())


@dataclass(slots=True)
class ViralFeedbackLoopService:
    llm_client: ViralityInsightLLMClient = field(default_factory=NullViralityInsightLLMClient)

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "ViralFeedbackLoopService":
        return cls(llm_client=RemoteViralityInsightLLMClient.from_settings(settings))

    def analyze_clip(
        self,
        *,
        clip_id: str,
        metrics: Mapping[str, Any],
        clip_context: Mapping[str, Any],
    ) -> ClipOptimizationFeedback:
        tracked = track_clip(clip_id, metrics)
        duration_seconds = max(1.0, _as_float(clip_context.get("duration_seconds"), default=1.0))
        completion_rate = _as_float(tracked["completion_rate"])
        loop_rate = _as_float(tracked["loop_rate"])
        share_rate = _as_float(tracked["share_rate"])
        comment_rate = _as_float(tracked["comment_rate"])
        drop_off_ratio = (
            _as_float(tracked["drop_off_point_seconds"]) / duration_seconds
            if tracked["drop_off_point_seconds"] is not None
            else completion_rate
        )

        increase_similar = completion_rate >= 0.78 or loop_rate >= 0.18 or share_rate >= 0.035
        shorten_clips = completion_rate < 0.58 or drop_off_ratio < 0.45
        adjust_captions = share_rate < 0.02 or comment_rate < 0.01

        if increase_similar and not shorten_clips:
            performance_tier = "high_retention"
            recommendation = "Increase similar clips."
        elif shorten_clips:
            performance_tier = "retention_risk"
            recommendation = "Shorten the clip and tighten the opening."
        else:
            performance_tier = "iterating"
            recommendation = "Keep testing hooks and captions."

        actions: list[str] = []
        if increase_similar:
            actions.append("Increase similar clips across the same event pattern and camera language.")
        if shorten_clips:
            actions.append("Cut the setup earlier and move the payoff into the first half of the clip.")
        if adjust_captions:
            actions.append("Adjust captions, hooks, and CTA wording before the next distribution pass.")
        if not actions:
            actions.append("Keep the current cut and gather more data before changing the format.")

        prompt = {
            "clip_id": clip_id,
            "metrics": tracked,
            "context": dict(clip_context),
        }
        llm_analysis = self.llm_client.generate(prompt)
        analysis_source = getattr(self.llm_client, "provider_name", "heuristic") if llm_analysis else "heuristic"
        viral_analysis = llm_analysis or self._heuristic_analysis(
            tracked=tracked,
            clip_context=clip_context,
            duration_seconds=duration_seconds,
        )

        return ClipOptimizationFeedback(
            performance_tier=performance_tier,
            recommendation=recommendation,
            increase_similar_clips=increase_similar,
            adjust_captions=adjust_captions,
            shorten_clips=shorten_clips,
            actions=actions,
            viral_analysis=viral_analysis,
            analysis_source=analysis_source,
        )

    def _heuristic_analysis(
        self,
        *,
        tracked: Mapping[str, Any],
        clip_context: Mapping[str, Any],
        duration_seconds: float,
    ) -> str:
        reasons: list[str] = []
        completion_rate = _as_float(tracked["completion_rate"])
        loop_rate = _as_float(tracked["loop_rate"])
        share_rate = _as_float(tracked["share_rate"])

        if completion_rate >= 0.8:
            reasons.append("viewers stayed through most of the clip")
        if loop_rate >= 0.18:
            reasons.append("the moment was replayed often")
        if share_rate >= 0.03:
            reasons.append("share velocity was strong")
        if clip_context.get("crowd_spike"):
            reasons.append("crowd energy amplified the payoff")
        if clip_context.get("late_drama"):
            reasons.append("late-match timing added urgency")
        if clip_context.get("upset"):
            reasons.append("the result carried upset value")
        if clip_context.get("is_final"):
            reasons.append("the stage raised the emotional stakes")

        if not reasons:
            reasons.append("the hook and payoff still landed well enough to trigger repeat views")

        joined = ", ".join(reasons[:3])
        title = str(clip_context.get("title") or "This clip")
        return f"{title} performed because {joined}. The current signal suggests leaning into the same moment profile on the next cut."


__all__ = [
    "ClipOptimizationFeedback",
    "RemoteViralityInsightLLMClient",
    "ViralFeedbackLoopService",
    "track_clip",
]
