from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from app.ai_gateway.config import AiRuntimeConfig, central_api_key
from app.ai_gateway.errors import AiProviderError

logger = logging.getLogger(__name__)

_RETRYABLE = {"rate_limited", "timeout", "service_outage"}


@dataclass(slots=True)
class ProviderRequest:
    model: str
    instructions: str
    user_input: str
    max_output_tokens: int
    temperature: float = 0.4
    json_schema: dict[str, Any] | None = None
    schema_name: str = "gtex_result"
    tools: list[dict[str, Any]] | None = None


@dataclass(slots=True)
class ProviderCompletion:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    tool_calls: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class ModerationResult:
    flagged: bool
    categories: list[str]


def classify_openai_error(exc: BaseException) -> tuple[str, bool]:
    name = type(exc).__name__
    status = getattr(exc, "status_code", None)
    code = str(getattr(exc, "code", "") or "").lower()
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        body_text = json.dumps(body).lower()
    else:
        body_text = str(body or "").lower()
    if "insufficient_quota" in code or "insufficient_quota" in body_text or "billing" in body_text:
        return "insufficient_credits", False
    if name in {"AuthenticationError", "PermissionDeniedError"} or status in {401, 403}:
        return "authentication_failed", False
    if name == "BadRequestError" or (isinstance(status, int) and 400 <= status < 500 and status != 429):
        return "invalid_request", False
    if name == "RateLimitError" or status == 429:
        return "rate_limited", True
    if name in {"APITimeoutError", "APIConnectionError"} or status in {408, 409}:
        return "timeout", True
    if name in {"InternalServerError", "APIStatusError"} or (isinstance(status, int) and status >= 500):
        return "service_outage", True
    return "service_outage", True


class OpenAiSdkProvider:
    """Official OpenAI SDK adapter. Retries live here so callers share one policy."""

    def __init__(
        self,
        config: AiRuntimeConfig,
        *,
        client: Any | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self._sleep = sleeper or _default_sleep

    def complete(self, request: ProviderRequest) -> ProviderCompletion:
        def _once() -> ProviderCompletion:
            client = self._ensure_client()
            kwargs: dict[str, Any] = {
                "model": request.model,
                "instructions": request.instructions,
                "input": request.user_input,
                "max_output_tokens": request.max_output_tokens,
                "temperature": request.temperature,
                "store": False,
            }
            if request.json_schema is not None:
                kwargs["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": request.schema_name,
                        "strict": True,
                        "schema": request.json_schema,
                    }
                }
            if request.tools:
                kwargs["tools"] = request.tools
                kwargs["tool_choice"] = "required"
            response = client.responses.create(**kwargs)
            return _completion_from_response(response, request.model)

        return self._call(_once)

    def moderate(self, text: str) -> ModerationResult:
        def _once() -> ModerationResult:
            client = self._ensure_client()
            response = client.moderations.create(model="omni-moderation-latest", input=text)
            return _moderation_from_response(response)

        return self._call(_once)

    def stream(self, request: ProviderRequest) -> Iterator[str]:
        attempt = 0
        yielded = False
        while True:
            try:
                client = self._ensure_client()
                events = client.responses.create(
                    model=request.model,
                    instructions=request.instructions,
                    input=request.user_input,
                    max_output_tokens=request.max_output_tokens,
                    temperature=request.temperature,
                    stream=True,
                    store=False,
                )
                for event in events:
                    if getattr(event, "type", "") == "response.output_text.delta":
                        delta = str(getattr(event, "delta", "") or "")
                        if delta:
                            yielded = True
                            yield delta
                return
            except AiProviderError:
                raise
            except Exception as exc:
                code, retryable = classify_openai_error(exc)
                if yielded or not retryable or attempt >= self.config.max_retries:
                    raise AiProviderError(code) from None
                self._sleep(min(8.0, 0.5 * (2**attempt)))
                attempt += 1

    def _call(self, fn: Callable[[], Any]) -> Any:
        attempt = 0
        while True:
            try:
                return fn()
            except AiProviderError:
                raise
            except Exception as exc:
                code, retryable = classify_openai_error(exc)
                if code not in _RETRYABLE:
                    retryable = False
                if not retryable or attempt >= self.config.max_retries:
                    raise AiProviderError(code) from None
                self._sleep(min(8.0, 0.5 * (2**attempt)))
                attempt += 1

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        key = central_api_key()
        if not key:
            raise AiProviderError("missing_api_key")
        try:
            import httpx
            from openai import OpenAI
        except ImportError as exc:
            raise AiProviderError("configuration_invalid") from exc
        timeout_seconds = max(self.config.timeout_ms, 1000) / 1000
        self._client = OpenAI(api_key=key, timeout=httpx.Timeout(timeout_seconds), max_retries=0)
        return self._client


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)


def _completion_from_response(response: Any, model: str) -> ProviderCompletion:
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    text = str(getattr(response, "output_text", "") or "")
    tool_calls: list[dict[str, str]] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) == "function_call":
            tool_calls.append(
                {
                    "name": str(getattr(item, "name", "") or ""),
                    "arguments": str(getattr(item, "arguments", "") or ""),
                }
            )
    return ProviderCompletion(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=str(getattr(response, "model", None) or model),
        tool_calls=tool_calls,
    )


def _moderation_from_response(response: Any) -> ModerationResult:
    results = list(getattr(response, "results", None) or [])
    if not results:
        return ModerationResult(flagged=False, categories=[])
    result = results[0]
    categories = getattr(result, "categories", None)
    if hasattr(categories, "model_dump"):
        raw = categories.model_dump()
    elif isinstance(categories, dict):
        raw = categories
    else:
        raw = {}
    flagged_names = sorted(str(key) for key, value in raw.items() if value)
    return ModerationResult(flagged=bool(getattr(result, "flagged", False)), categories=flagged_names)


def provider_failure(exc: Exception) -> str:
    if isinstance(exc, AiProviderError):
        return exc.code
    logger.warning("ai_gateway.provider_failure code=service_outage")
    return "service_outage"
