from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}
_MODEL_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_SECRET_PREFIXES = ("sk-", "sk-proj-", "rk-")

SAFE_MESSAGES = {
    "disabled": "OpenAI is turned off.",
    "missing_api_key": "OpenAI is not configured on the server.",
    "configuration_invalid": "OpenAI configuration is invalid.",
    "feature_disabled": "This AI feature is turned off.",
    "rate_limited": "Too many AI requests. Try again shortly.",
    "budget_exhausted": "The AI spending limit is reached. Recommendations are paused.",
    "insufficient_credits": "The AI provider has insufficient credits. Recommendations are paused.",
    "authentication_failed": "The AI provider rejected the server credentials.",
    "timeout": "The AI provider timed out. Nothing in GTEX was changed.",
    "service_outage": "The AI provider is unavailable. Nothing in GTEX was changed.",
    "invalid_request": "The AI provider rejected the request.",
    "schema_invalid": "The AI response did not match the required format.",
    "invalid_tool": "The AI response asked for an action GTEX will not run.",
    "input_rejected": "That request is too large or contains fields the AI service will not send.",
}


@dataclass(frozen=True, slots=True)
class FeatureSetting:
    feature_key: str
    enabled: bool
    audience: str
    complexity: str
    max_requests_per_day: int
    max_output_tokens: int
    cache_ttl_seconds: int
    model: str | None = None


DEFAULT_FEATURES: dict[str, FeatureSetting] = {
    "match_report": FeatureSetting("match_report", True, "user", "complex", 200, 500, 600),
    "scouting_brief": FeatureSetting("scouting_brief", True, "user", "complex", 200, 500, 600),
    "competition_summary": FeatureSetting("competition_summary", True, "user", "complex", 200, 400, 600),
    "youth_development": FeatureSetting("youth_development", True, "user", "complex", 200, 400, 600),
    "club_announcement": FeatureSetting("club_announcement", True, "user", "simple", 100, 320, 0),
    "community_moderation": FeatureSetting("community_moderation", True, "admin", "simple", 500, 120, 0),
    "admin_ops_summary": FeatureSetting("admin_ops_summary", True, "admin", "complex", 100, 400, 120),
    "market_insight": FeatureSetting("market_insight", True, "admin", "complex", 100, 400, 120),
    "fraud_review": FeatureSetting("fraud_review", True, "admin", "complex", 100, 400, 0),
    "staff_dialogue": FeatureSetting("staff_dialogue", False, "internal", "complex", 500, 220, 0),
    "live_commentary": FeatureSetting("live_commentary", True, "internal", "simple", 8000, 120, 0),
    "social_caption": FeatureSetting("social_caption", True, "internal", "simple", 4000, 80, 0),
    "social_debate": FeatureSetting("social_debate", True, "internal", "complex", 2000, 220, 0),
    "social_analytics": FeatureSetting("social_analytics", True, "internal", "simple", 2000, 160, 0),
    "reporter_polish": FeatureSetting("reporter_polish", False, "internal", "simple", 200, 400, 0),
}


@dataclass(frozen=True, slots=True)
class AiRuntimeConfig:
    environment_enabled: bool
    admin_enabled: bool
    api_key_configured: bool
    model: str
    complex_model: str
    max_retries: int
    timeout_ms: int
    max_input_tokens: int
    max_output_tokens: int
    user_requests_per_minute: int
    global_requests_per_minute: int
    daily_budget_usd: float
    monthly_budget_usd: float
    route_legacy_clients: bool
    config_errors: tuple[str, ...] = ()
    features: dict[str, FeatureSetting] = field(default_factory=lambda: dict(DEFAULT_FEATURES))

    @property
    def effective_enabled(self) -> bool:
        return self.environment_enabled and self.admin_enabled and not self.config_errors

    @property
    def integration_status(self) -> str:
        if self.config_errors:
            return "misconfigured"
        if not self.environment_enabled or not self.admin_enabled:
            return "disabled"
        if not self.api_key_configured:
            return "missing_api_key"
        return "ready"

    def feature(self, key: str) -> FeatureSetting | None:
        return self.features.get(key)

    def model_for(self, feature: FeatureSetting, override: str | None = None) -> str:
        if override and _MODEL_RE.fullmatch(override) and not override.startswith(_SECRET_PREFIXES):
            return override
        if feature.model and _MODEL_RE.fullmatch(feature.model):
            return feature.model
        if feature.complexity == "complex" and self.complex_model:
            return self.complex_model
        return self.model

    def with_overlay(
        self,
        *,
        admin_enabled: bool | None = None,
        model: str | None = None,
        daily_budget_usd: float | None = None,
        monthly_budget_usd: float | None = None,
        max_input_tokens: int | None = None,
        max_output_tokens: int | None = None,
        user_requests_per_minute: int | None = None,
        global_requests_per_minute: int | None = None,
        features: dict[str, FeatureSetting] | None = None,
    ) -> AiRuntimeConfig:
        return replace(
            self,
            admin_enabled=self.admin_enabled if admin_enabled is None else admin_enabled,
            model=model or self.model,
            daily_budget_usd=self.daily_budget_usd if daily_budget_usd is None else daily_budget_usd,
            monthly_budget_usd=self.monthly_budget_usd if monthly_budget_usd is None else monthly_budget_usd,
            max_input_tokens=self.max_input_tokens if max_input_tokens is None else max_input_tokens,
            max_output_tokens=self.max_output_tokens if max_output_tokens is None else max_output_tokens,
            user_requests_per_minute=(
                self.user_requests_per_minute if user_requests_per_minute is None else user_requests_per_minute
            ),
            global_requests_per_minute=(
                self.global_requests_per_minute if global_requests_per_minute is None else global_requests_per_minute
            ),
            features=features if features is not None else self.features,
        )


def central_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or os.getenv("GTEX_AI_API_KEY") or "").strip()


def from_env() -> AiRuntimeConfig:
    errors: list[str] = []
    environment_enabled, enabled_error = _bool_env("OPENAI_ENABLED", False)
    if enabled_error:
        errors.append(enabled_error)
    route_legacy, route_error = _bool_env("OPENAI_ROUTE_LEGACY_CLIENTS", False)
    if route_error:
        errors.append(route_error)
    max_retries, retry_error = _int_env("OPENAI_MAX_RETRIES", 3, 0, 8)
    if retry_error:
        errors.append(retry_error)
    timeout_ms, timeout_error = _int_env("OPENAI_TIMEOUT_MS", 60_000, 1_000, 180_000)
    if timeout_error:
        errors.append(timeout_error)
    max_input, input_error = _int_env("OPENAI_MAX_INPUT_TOKENS", 2_000, 64, 8_000)
    if input_error:
        errors.append(input_error)
    max_output, output_error = _int_env("OPENAI_MAX_OUTPUT_TOKENS", 800, 16, 4_000)
    if output_error:
        errors.append(output_error)
    user_rpm, user_rpm_error = _int_env("OPENAI_USER_REQUESTS_PER_MINUTE", 12, 1, 1_000)
    if user_rpm_error:
        errors.append(user_rpm_error)
    global_rpm, global_rpm_error = _int_env("OPENAI_GLOBAL_REQUESTS_PER_MINUTE", 300, 1, 5_000)
    if global_rpm_error:
        errors.append(global_rpm_error)
    daily_budget, daily_error = _float_env("OPENAI_DAILY_BUDGET_USD", 25.0, 0.0, 10_000.0)
    if daily_error:
        errors.append(daily_error)
    monthly_budget, monthly_error = _float_env("OPENAI_MONTHLY_BUDGET_USD", 400.0, 0.0, 100_000.0)
    if monthly_error:
        errors.append(monthly_error)
    model = _model_env("OPENAI_MODEL", os.getenv("GTEX_AI_MODEL") or "gpt-4o-mini", errors)
    complex_model = _optional_model_env("OPENAI_MODEL_COMPLEX", errors) or model
    if monthly_budget < daily_budget:
        errors.append("OPENAI_MONTHLY_BUDGET_USD must be at least the daily budget")
    features = {key: value for key, value in DEFAULT_FEATURES.items()}
    if os.getenv("GTEX_ENABLE_LIVE_LLM_COMMS", "0").strip() == "1":
        features["staff_dialogue"] = replace(features["staff_dialogue"], enabled=True)
    return AiRuntimeConfig(
        environment_enabled=environment_enabled,
        admin_enabled=True,
        api_key_configured=bool(central_api_key()),
        model=model,
        complex_model=complex_model,
        max_retries=max_retries,
        timeout_ms=timeout_ms,
        max_input_tokens=max_input,
        max_output_tokens=max_output,
        user_requests_per_minute=user_rpm,
        global_requests_per_minute=global_rpm,
        daily_budget_usd=daily_budget,
        monthly_budget_usd=monthly_budget,
        route_legacy_clients=route_legacy,
        config_errors=tuple(errors),
        features=features,
    )


def _bool_env(name: str, default: bool) -> tuple[bool, str | None]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default, None
    lowered = raw.strip().lower()
    if lowered in _TRUE:
        return True, None
    if lowered in _FALSE:
        return False, None
    return default, f"{name} must be true or false"


def _int_env(name: str, default: int, minimum: int, maximum: int) -> tuple[int, str | None]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default, None
    try:
        value = int(raw.strip())
    except ValueError:
        return default, f"{name} must be an integer"
    if value < minimum or value > maximum:
        return default, f"{name} must be between {minimum} and {maximum}"
    return value, None


def _float_env(name: str, default: float, minimum: float, maximum: float) -> tuple[float, str | None]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default, None
    try:
        value = float(raw.strip())
    except ValueError:
        return default, f"{name} must be a number"
    if value < minimum or value > maximum:
        return default, f"{name} must be between {minimum} and {maximum}"
    return value, None


def _model_env(name: str, default: str, errors: list[str]) -> str:
    raw = (os.getenv(name) or "").strip() or default
    if raw.startswith(_SECRET_PREFIXES) or not _MODEL_RE.fullmatch(raw):
        errors.append(f"{name} is not a valid model name")
        return default if _MODEL_RE.fullmatch(default) else "gpt-4o-mini"
    return raw


def _optional_model_env(name: str, errors: list[str]) -> str | None:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return None
    if raw.startswith(_SECRET_PREFIXES) or not _MODEL_RE.fullmatch(raw):
        errors.append(f"{name} is not a valid model name")
        return None
    return raw
