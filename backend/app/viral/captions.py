from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Protocol

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


class CaptionLLMClient(Protocol):
    provider_name: str

    def generate(self, prompt: dict[str, Any]) -> str | None:
        ...


@dataclass(slots=True)
class NullCaptionLLMClient:
    provider_name: str = "template"

    def generate(self, prompt: dict[str, Any]) -> str | None:
        return None


@dataclass(slots=True)
class RemoteCaptionLLMClient:
    enabled: bool = False
    endpoint_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 8
    provider_name: str = "remote-llm"

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "RemoteCaptionLLMClient":
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
                                "Write a football short-form caption. "
                                "Return one hook line and one caption line only. "
                                "Keep it dramatic, concise, social-first, and emoji-ready."
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
            "temperature": 0.9,
            "max_output_tokens": 80,
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
class CaptionResult:
    hook: str
    caption: str
    cta: str
    hashtags: list[str]
    source: str


@dataclass(slots=True)
class ViralCaptionService:
    llm_client: CaptionLLMClient = field(default_factory=NullCaptionLLMClient)

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "ViralCaptionService":
        return cls(llm_client=RemoteCaptionLLMClient.from_settings(settings))

    def generate_caption(self, event: dict[str, Any]) -> CaptionResult:
        llm_output = self.llm_client.generate(event)
        if llm_output:
            parts = [part.strip() for part in llm_output.splitlines() if part.strip()]
            hook = parts[0] if parts else "Wait for the finish 😳"
            caption = parts[1] if len(parts) > 1 else parts[0]
            return CaptionResult(
                hook=hook,
                caption=caption,
                cta="Share to WhatsApp",
                hashtags=["#GTEX", "#Football", "#ViralClip"],
                source=getattr(self.llm_client, "provider_name", "remote-llm"),
            )
        return self._template_caption(event)

    def _template_caption(self, event: dict[str, Any]) -> CaptionResult:
        minute = int(event.get("minute") or 0)
        team = str(event.get("team_name") or "This team")
        player = str(event.get("player_name") or "someone")
        event_type = str(event.get("event_type") or "moment").lower()
        comeback = bool(event.get("comeback"))
        go_ahead = bool(event.get("go_ahead"))
        equalizer = bool(event.get("equalizer"))
        if event_type in {"goal", "penalty_goal", "penalty_scored"} and minute >= 85:
            hook = f"{minute}' and the whole match flipped 😳🔥"
        elif comeback:
            hook = "This comeback broke the timeline 😤"
        elif go_ahead:
            hook = "One touch changed everything ⚽"
        elif equalizer:
            hook = "They dragged it back from nowhere 😮"
        elif event_type in {"double_save", "goalkeeper_save", "save"}:
            hook = "How did that NOT go in? 🧤"
        else:
            hook = "Football chaos in one clip 🎥"
        caption = f"{player} sparked it for {team}. This is the kind of moment people replay instantly."
        return CaptionResult(
            hook=hook,
            caption=caption,
            cta="Share to WhatsApp",
            hashtags=["#GTEX", "#Football", "#Clips"],
            source="template",
        )
