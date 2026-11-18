from __future__ import annotations

import json
import logging
import os
import time
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from app.ai_gateway.config import SAFE_MESSAGES, AiRuntimeConfig, FeatureSetting
from app.ai_gateway.guardrails import (
    INSTRUCTIONS,
    estimate_tokens,
    fence_untrusted,
    redact_secrets,
    request_hash,
    tool_is_allowed,
)
from app.ai_gateway.provider import ProviderRequest, provider_failure
from app.ai_gateway.usage import SqlUsageStore, UsageEntry, estimate_cost_usd

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AiCallResult:
    ok: bool
    feature: str
    text: str | None = None
    data: dict[str, Any] | None = None
    model: str | None = None
    error_code: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cache_hit: bool = False
    authoritative: bool = False

    def as_public(self) -> dict[str, Any]:
        return {
            "available": self.ok,
            "authoritative": False,
            "feature": self.feature,
            "provider": "openai" if self.ok else None,
            "model": self.model,
            "text": self.text,
            "data": self.data,
            "error_code": self.error_code,
            "message": None if self.ok else SAFE_MESSAGES.get(self.error_code or "", SAFE_MESSAGES["service_outage"]),
            "cache_hit": self.cache_hit,
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "estimated_cost_usd": self.estimated_cost_usd,
            },
        }


class ResponseCache:
    def __init__(self, max_items: int = 256) -> None:
        self.max_items = max_items
        self._items: OrderedDict[str, tuple[float, AiCallResult]] = OrderedDict()

    def get(self, key: str) -> AiCallResult | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, result = item
        if expires_at < time.monotonic():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return result

    def set(self, key: str, result: AiCallResult, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        self._items[key] = (time.monotonic() + ttl_seconds, result)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)


class GtexAiService:
    def __init__(
        self,
        *,
        config: AiRuntimeConfig | None = None,
        provider: Any | None = None,
        store: Any | None = None,
        cache: ResponseCache | None = None,
        clock: Any | None = None,
    ) -> None:
        self._config = config
        self._provider = provider
        self.store = store if store is not None else SqlUsageStore()
        self.cache = cache or ResponseCache()
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def config(self) -> AiRuntimeConfig:
        if self._config is not None:
            return self._config
        from app.ai_gateway.repository import load_effective_config

        return load_effective_config()

    @property
    def provider(self) -> Any:
        if self._provider is None:
            from app.ai_gateway.provider import OpenAiSdkProvider

            self._provider = OpenAiSdkProvider(self.config)
        return self._provider

    def status(self) -> dict[str, Any]:
        config = self.config
        summary = self.store.summary()
        summary["recent_errors"] = self.store.recent_errors()
        return {
            "provider": "openai",
            "integration_status": config.integration_status,
            "environment_enabled": config.environment_enabled,
            "admin_enabled": config.admin_enabled,
            "effective_enabled": config.effective_enabled,
            "api_key_configured": config.api_key_configured,
            "model": config.model,
            "complex_model": config.complex_model,
            "max_retries": config.max_retries,
            "timeout_ms": config.timeout_ms,
            "daily_budget_usd": config.daily_budget_usd,
            "monthly_budget_usd": config.monthly_budget_usd,
            "max_input_tokens": config.max_input_tokens,
            "max_output_tokens": config.max_output_tokens,
            "user_requests_per_minute": config.user_requests_per_minute,
            "global_requests_per_minute": config.global_requests_per_minute,
            "legacy_clients_routed": config.route_legacy_clients,
            "config_errors": list(config.config_errors),
            "features": [
                {
                    "feature_key": feature.feature_key,
                    "enabled": feature.enabled,
                    "audience": feature.audience,
                    "complexity": feature.complexity,
                    "model": feature.model,
                    "max_requests_per_day": feature.max_requests_per_day,
                    "max_output_tokens": feature.max_output_tokens,
                    "cache_ttl_seconds": feature.cache_ttl_seconds,
                }
                for feature in config.features.values()
            ],
            "usage": summary,
            "authoritative": False,
        }

    def generate_text(
        self,
        *,
        feature: str,
        user_content: str,
        facts: Any = None,
        extra_instructions: str = "",
        user_id: str | None = None,
        model_override: str | None = None,
        temperature: float = 0.4,
        max_output_tokens: int | None = None,
    ) -> AiCallResult:
        try:
            return self._generate(
                feature=feature,
                user_content=user_content,
                facts=facts,
                extra_instructions=extra_instructions,
                user_id=user_id,
                model_override=model_override,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except Exception:
            logger.warning("ai_gateway.unhandled feature=%s", feature)
            return self._result(feature, ok=False, error_code="service_outage")

    def generate_json(
        self,
        *,
        feature: str,
        user_content: str,
        schema: dict[str, Any],
        schema_name: str,
        validator: type[BaseModel],
        facts: Any = None,
        extra_instructions: str = "",
        user_id: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        allowlist: set[str] | None = None,
    ) -> AiCallResult:
        try:
            result = self._generate(
                feature=feature,
                user_content=user_content,
                facts=facts,
                extra_instructions=extra_instructions + " Return only the requested JSON object.",
                user_id=user_id,
                json_schema=None if tools else schema,
                schema_name=schema_name,
                tools=tools,
            )
        except Exception:
            logger.warning("ai_gateway.unhandled feature=%s", feature)
            return self._result(feature, ok=False, error_code="service_outage")
        if not result.ok:
            return result
        if tools and result.data and result.data.get("tool_calls"):
            return self._validate_tool_payload(result, validator, allowlist or set())
        return self._validate_json_text(result, validator)

    def summarize(self, **kwargs: Any) -> AiCallResult:
        kwargs["extra_instructions"] = (
            (kwargs.get("extra_instructions") or "") + " Summarize only the supplied facts in plain prose."
        ).strip()
        return self.generate_text(**kwargs)

    def classify(
        self,
        *,
        feature: str,
        user_content: str,
        labels: list[str],
        facts: Any = None,
        user_id: str | None = None,
    ) -> AiCallResult:
        from app.ai_gateway.schemas import Classification

        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string", "enum": labels},
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
            },
            "required": ["label", "confidence", "rationale"],
        }
        return self.generate_json(
            feature=feature,
            user_content=user_content,
            facts=facts,
            schema=schema,
            schema_name="gtex_classification",
            validator=Classification,
            user_id=user_id,
            extra_instructions="Choose exactly one label. This classification does not punish or ban anyone.",
        )

    def moderate(self, *, text: str, user_id: str | None = None) -> AiCallResult:
        feature = "community_moderation"
        prepared = self._prepare(
            feature,
            user_id=user_id,
            payload=redact_secrets(text)[:2000],
            model_override="omni-moderation-latest",
        )
        if isinstance(prepared, AiCallResult):
            return prepared
        started = time.perf_counter()
        try:
            outcome = self.provider.moderate(prepared.user_input)
        except Exception as exc:
            code = provider_failure(exc)
            self._record(feature, user_id, "error", code, prepared.model, 0, 0, 0, started, False, prepared.digest)
            return self._result(feature, ok=False, error_code=code, model=prepared.model)
        recommendation = "review" if outcome.flagged else "allow"
        data = {
            "flagged": outcome.flagged,
            "categories": outcome.categories,
            "recommendation": recommendation,
            "executed": False,
        }
        self._record(feature, user_id, "success", None, prepared.model, 0, 0, 0, started, False, prepared.digest)
        return self._result(feature, ok=True, text=recommendation, data=data, model=prepared.model)

    def stream_text(self, **kwargs: Any) -> Iterator[str]:
        feature = str(kwargs.get("feature") or "club_announcement")
        user_id = kwargs.get("user_id")
        prepared = self._prepare(
            feature,
            user_id=user_id,
            payload=fence_untrusted(facts=kwargs.get("facts"), user_content=str(kwargs.get("user_content") or "")),
            model_override=kwargs.get("model_override"),
            max_output_tokens=kwargs.get("max_output_tokens"),
        )
        if isinstance(prepared, AiCallResult):
            message = prepared.as_public()["message"] or SAFE_MESSAGES["service_outage"]
            yield message
            return
        request = ProviderRequest(
            model=prepared.model,
            instructions=INSTRUCTIONS + " " + str(kwargs.get("extra_instructions") or ""),
            user_input=prepared.user_input,
            max_output_tokens=prepared.max_output_tokens,
            temperature=float(kwargs.get("temperature") or 0.4),
        )
        started = time.perf_counter()
        chunks: list[str] = []
        try:
            for chunk in self.provider.stream(request):
                chunks.append(chunk)
                yield chunk
        except Exception as exc:
            code = provider_failure(exc)
            self._record(feature, user_id, "error", code, prepared.model, 0, 0, 0, started, False, prepared.digest)
            if not chunks:
                yield SAFE_MESSAGES.get(code, SAFE_MESSAGES["service_outage"])
            return
        text = "".join(chunks)
        output_tokens = estimate_tokens(text)
        cost = estimate_cost_usd(prepared.model, prepared.input_tokens, output_tokens)
        self._record(
            feature,
            user_id,
            "success",
            None,
            prepared.model,
            prepared.input_tokens,
            output_tokens,
            cost,
            started,
            False,
            prepared.digest,
        )

    def _generate(
        self,
        *,
        feature: str,
        user_content: str,
        facts: Any = None,
        extra_instructions: str = "",
        user_id: str | None = None,
        model_override: str | None = None,
        temperature: float = 0.4,
        max_output_tokens: int | None = None,
        json_schema: dict[str, Any] | None = None,
        schema_name: str = "gtex_result",
        tools: list[dict[str, Any]] | None = None,
    ) -> AiCallResult:
        payload = fence_untrusted(facts=facts, user_content=user_content)
        prepared = self._prepare(
            feature,
            user_id=user_id,
            payload=payload,
            model_override=model_override,
            max_output_tokens=max_output_tokens,
        )
        if isinstance(prepared, AiCallResult):
            return prepared
        cached = self.cache.get(prepared.digest)
        if cached is not None:
            hit = self._result(
                feature,
                ok=True,
                text=cached.text,
                data=cached.data,
                model=cached.model,
                cache_hit=True,
            )
            self._record(
                feature, user_id, "success", None, cached.model, 0, 0, 0, time.perf_counter(), True, prepared.digest
            )
            return hit
        request = ProviderRequest(
            model=prepared.model,
            instructions=(INSTRUCTIONS + " " + extra_instructions).strip(),
            user_input=prepared.user_input,
            max_output_tokens=prepared.max_output_tokens,
            temperature=temperature,
            json_schema=json_schema,
            schema_name=schema_name,
            tools=tools,
        )
        started = time.perf_counter()
        try:
            completion = self.provider.complete(request)
        except Exception as exc:
            code = provider_failure(exc)
            self._record(feature, user_id, "error", code, prepared.model, 0, 0, 0, started, False, prepared.digest)
            return self._result(feature, ok=False, error_code=code, model=prepared.model)
        cost = estimate_cost_usd(prepared.model, completion.input_tokens, completion.output_tokens)
        data = {"tool_calls": completion.tool_calls} if completion.tool_calls else None
        result = self._result(
            feature,
            ok=True,
            text=completion.text.strip() or None,
            data=data,
            model=completion.model,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            estimated_cost_usd=cost,
        )
        self.cache.set(prepared.digest, result, prepared.feature.cache_ttl_seconds)
        self._record(
            feature,
            user_id,
            "success",
            None,
            completion.model,
            completion.input_tokens,
            completion.output_tokens,
            cost,
            started,
            False,
            prepared.digest,
        )
        logger.info(
            "ai_gateway.request feature=%s status=success model=%s input_tokens=%s output_tokens=%s",
            feature,
            completion.model,
            completion.input_tokens,
            completion.output_tokens,
        )
        return result

    def _prepare(
        self,
        feature_key: str,
        *,
        user_id: str | None,
        payload: str,
        model_override: str | None,
        max_output_tokens: int | None = None,
    ) -> AiCallResult | _Prepared:
        config = self.config
        feature = config.feature(feature_key)
        if feature is None:
            return self._blocked(feature_key, "feature_disabled", user_id, None, payload)
        if config.config_errors:
            return self._blocked(feature_key, "configuration_invalid", user_id, config.model, payload)
        legacy_staff = self._legacy_staff_allowed(feature_key, config)
        if not config.admin_enabled:
            return self._blocked(feature_key, "disabled", user_id, config.model, payload)
        if not config.environment_enabled and not legacy_staff:
            return self._blocked(feature_key, "disabled", user_id, config.model, payload)
        if not feature.enabled:
            return self._blocked(feature_key, "feature_disabled", user_id, config.model, payload)
        if not config.api_key_configured and self._provider is None:
            return self._blocked(feature_key, "missing_api_key", user_id, config.model, payload)
        if estimate_tokens(payload) > config.max_input_tokens:
            return self._blocked(feature_key, "input_rejected", user_id, config.model, payload)
        model = config.model_for(feature, model_override)
        user_limit = self.store.user_request_limit(user_id)
        user_max, user_window = user_limit or (config.user_requests_per_minute, 60)
        if user_id and self.store.recent_user_count(user_id, user_window) >= user_max:
            return self._blocked(feature_key, "rate_limited", user_id, model, payload)
        if self.store.recent_global_count(60) >= config.global_requests_per_minute:
            return self._blocked(feature_key, "rate_limited", user_id, model, payload)
        if self.store.feature_count_today(feature_key) >= feature.max_requests_per_day:
            return self._blocked(feature_key, "rate_limited", user_id, model, payload)
        now = self._clock()
        start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_month = start_day.replace(day=1)
        if self.store.spend_since(start_day) >= config.daily_budget_usd:
            return self._blocked(feature_key, "budget_exhausted", user_id, model, payload)
        if self.store.spend_since(start_month) >= config.monthly_budget_usd:
            return self._blocked(feature_key, "budget_exhausted", user_id, model, payload)
        output_cap = min(
            feature.max_output_tokens,
            config.max_output_tokens,
            max_output_tokens or feature.max_output_tokens,
        )
        return _Prepared(
            feature=feature,
            model=model,
            user_input=payload,
            max_output_tokens=max(16, output_cap),
            input_tokens=estimate_tokens(payload),
            digest=request_hash(feature_key, model, payload),
        )

    def _legacy_staff_allowed(self, feature_key: str, config: AiRuntimeConfig) -> bool:
        if feature_key != "staff_dialogue":
            return False
        if os.getenv("OPENAI_ENABLED", "").strip().lower() in {"0", "false", "no", "off"}:
            return False
        if os.getenv("GTEX_ENABLE_LIVE_LLM_COMMS", "0").strip() != "1":
            return False
        return config.api_key_configured or self._provider is not None

    def _blocked(
        self,
        feature: str,
        code: str,
        user_id: str | None,
        model: str | None,
        payload: str,
    ) -> AiCallResult:
        self._record(
            feature,
            user_id,
            "blocked",
            code,
            model,
            0,
            0,
            0,
            time.perf_counter(),
            False,
            request_hash(feature, model or "", payload),
        )
        logger.info("ai_gateway.request feature=%s status=blocked error_code=%s", feature, code)
        return self._result(feature, ok=False, error_code=code, model=model)

    def _validate_json_text(self, result: AiCallResult, validator: type[BaseModel]) -> AiCallResult:
        raw = _strip_json(result.text or "")
        try:
            parsed = json.loads(raw)
            validated = validator.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError, TypeError):
            return self._result(result.feature, ok=False, error_code="schema_invalid", model=result.model)
        data = validated.model_dump()
        return self._result(
            result.feature,
            ok=True,
            text=result.text,
            data=data,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
            cache_hit=result.cache_hit,
        )

    def _validate_tool_payload(
        self, result: AiCallResult, validator: type[BaseModel], allowlist: set[str]
    ) -> AiCallResult:
        calls = list((result.data or {}).get("tool_calls") or [])
        if len(calls) != 1 or not tool_is_allowed(str(calls[0].get("name")), allowlist):
            return self._result(result.feature, ok=False, error_code="invalid_tool", model=result.model)
        try:
            arguments = json.loads(calls[0].get("arguments") or "{}")
            validated = validator.model_validate(arguments)
        except (json.JSONDecodeError, ValidationError, TypeError):
            return self._result(result.feature, ok=False, error_code="schema_invalid", model=result.model)
        data = validated.model_dump()
        data["tool"] = calls[0]["name"]
        data["executed"] = False
        return self._result(
            result.feature,
            ok=True,
            text=result.text,
            data=data,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        )

    def _record(
        self,
        feature: str,
        user_id: str | None,
        status: str,
        error_code: str | None,
        model: str | None,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        started: float,
        cache_hit: bool,
        digest: str,
    ) -> None:
        try:
            self.store.record(
                UsageEntry(
                    feature=feature,
                    user_id=user_id,
                    status=status,
                    error_code=error_code,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=cost,
                    latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
                    cache_hit=cache_hit,
                    request_hash=digest,
                    created_at=self._clock(),
                )
            )
        except Exception:
            logger.warning("ai_gateway.usage_record_failed feature=%s", feature)

    @staticmethod
    def _result(feature: str, **kwargs: Any) -> AiCallResult:
        return AiCallResult(feature=feature, authoritative=False, **kwargs)


@dataclass(slots=True)
class _Prepared:
    feature: FeatureSetting
    model: str
    user_input: str
    max_output_tokens: int
    input_tokens: int
    digest: str


def _strip_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()
