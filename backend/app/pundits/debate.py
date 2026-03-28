from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Protocol

import requests

from app.core.config import Settings
from app.pundits.personas import PUNDITS


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


class DebateLLMClient(Protocol):
    provider_name: str

    def generate(self, prompt: dict[str, Any]) -> str | None:
        ...


@dataclass(slots=True)
class NullDebateLLMClient:
    provider_name: str = "template"

    def generate(self, prompt: dict[str, Any]) -> str | None:
        return None


@dataclass(slots=True)
class RemoteDebateLLMClient:
    enabled: bool = False
    endpoint_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 8
    provider_name: str = "remote-llm"

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "RemoteDebateLLMClient":
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
                                "Simulate a heated football debate. "
                                "Return 6 short lines only, one speaker per line in the format "
                                "'Speaker: line'."
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
            "max_output_tokens": 220,
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
class DebateLine:
    speaker: str
    style: str
    stance: str
    line: str
    emphasis: str = "medium"


@dataclass(slots=True)
class DebateGenerator:
    llm_client: DebateLLMClient = field(default_factory=NullDebateLLMClient)

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "DebateGenerator":
        return cls(llm_client=RemoteDebateLLMClient.from_settings(settings))

    def generate(self, *, analysis: dict[str, Any], hot_takes: list[str]) -> list[DebateLine]:
        llm_output = self.llm_client.generate({"analysis": analysis, "hot_takes": hot_takes, "personas": list(PUNDITS)})
        if llm_output:
            parsed = self._parse_llm_output(llm_output)
            if parsed:
                return parsed
        return self._template_lines(analysis=analysis, hot_takes=hot_takes)

    def _parse_llm_output(self, value: str) -> list[DebateLine]:
        lines: list[DebateLine] = []
        persona_by_name = {item["name"].lower(): item for item in PUNDITS}
        for raw_line in value.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            speaker, body = [part.strip() for part in line.split(":", 1)]
            persona = persona_by_name.get(speaker.lower())
            if persona is None or not body:
                continue
            lines.append(
                DebateLine(
                    speaker=persona["name"],
                    style=persona["style"],
                    stance=persona["stance"],
                    line=body,
                    emphasis="high" if persona["name"] == "Hype Merchant" else "medium",
                )
            )
        return lines[:6]

    def _template_lines(self, *, analysis: dict[str, Any], hot_takes: list[str]) -> list[DebateLine]:
        winner = analysis.get("winner_team_name") or "Nobody"
        score = analysis.get("score") or "0-0"
        key_player = analysis.get("key_player") or "the main man"
        key_rating = analysis.get("key_player_rating") or 0.0
        xg_diff = abs(float(analysis.get("xg_diff") or 0.0))
        turning_point = analysis.get("turning_point") or "the late swing"
        return [
            DebateLine(
                speaker="Tactical Analyst",
                style=PUNDITS[0]["style"],
                stance=PUNDITS[0]["stance"],
                line=f"The xG gap was {xg_diff:.2f}, and that explains why {winner} controlled the decisive phases.",
            ),
            DebateLine(
                speaker="Ex-Pro",
                style=PUNDITS[1]["style"],
                stance=PUNDITS[1]["stance"],
                line=f"I don’t want theory first, I want accountability. Somebody lost every duel when it mattered in that {score}.",
                emphasis="high",
            ),
            DebateLine(
                speaker="Hype Merchant",
                style=PUNDITS[2]["style"],
                stance=PUNDITS[2]["stance"],
                line=f"{winner} just hijacked the timeline and {key_player} was the main character all night 🔥",
                emphasis="high",
            ),
            DebateLine(
                speaker="Tactical Analyst",
                style=PUNDITS[0]["style"],
                stance=PUNDITS[0]["stance"],
                line=f"The turning point was {turning_point}. After that, the match state completely changed.",
            ),
            DebateLine(
                speaker="Ex-Pro",
                style=PUNDITS[1]["style"],
                stance=PUNDITS[1]["stance"],
                line=hot_takes[0] if hot_takes else "That result will leave a scar in the dressing room.",
                emphasis="high",
            ),
            DebateLine(
                speaker="Hype Merchant",
                style=PUNDITS[2]["style"],
                stance=PUNDITS[2]["stance"],
                line=f"{key_player} dropped a {key_rating:.1f} and the internet is going to talk about nothing else.",
                emphasis="high",
            ),
        ]
