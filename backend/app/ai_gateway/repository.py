from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_gateway.config import DEFAULT_FEATURES, AiRuntimeConfig, from_env
from app.models.ai_gateway import AiFeatureSetting, AiProviderSetting, AiRequestLimit

logger = logging.getLogger(__name__)

_CACHE: tuple[float, AiRuntimeConfig] | None = None
_CACHE_SECONDS = 10.0


def clear_config_cache() -> None:
    global _CACHE
    _CACHE = None


def load_effective_config(*, force: bool = False) -> AiRuntimeConfig:
    global _CACHE
    now = time.monotonic()
    if not force and _CACHE is not None and now - _CACHE[0] < _CACHE_SECONDS:
        return _CACHE[1]
    base = from_env()
    try:
        overlay = _read_overlay()
    except Exception:
        logger.warning("ai_gateway.settings_unavailable")
        return base
    if overlay is None:
        _CACHE = (now, base)
        return base
    merged = base.with_overlay(**overlay)
    _CACHE = (now, merged)
    return merged


def _read_overlay() -> dict[str, Any] | None:
    from app.core.database import get_session_factory

    with get_session_factory()() as session:
        return overlay_from_session(session)


def overlay_from_session(session: Session) -> dict[str, Any] | None:
    provider = session.scalar(select(AiProviderSetting).where(AiProviderSetting.provider == "openai"))
    feature_rows = list(session.scalars(select(AiFeatureSetting)).all())
    if provider is None and not feature_rows:
        return None
    features = {key: value for key, value in DEFAULT_FEATURES.items()}
    for row in feature_rows:
        current = features.get(row.feature_key)
        if current is None:
            continue
        features[row.feature_key] = replace(
            current,
            enabled=bool(row.enabled),
            model=(row.model_override or None),
            max_requests_per_day=int(row.max_requests_per_day),
            max_output_tokens=int(row.max_output_tokens),
            cache_ttl_seconds=int(row.cache_ttl_seconds),
        )
    if provider is None:
        return {"features": features}
    return {
        "admin_enabled": bool(provider.enabled),
        "model": provider.model or None,
        "daily_budget_usd": float(provider.daily_budget_usd),
        "monthly_budget_usd": float(provider.monthly_budget_usd),
        "max_input_tokens": int(provider.max_input_tokens),
        "max_output_tokens": int(provider.max_output_tokens),
        "user_requests_per_minute": int(provider.user_requests_per_minute),
        "global_requests_per_minute": int(provider.global_requests_per_minute),
        "features": features,
    }


class AiSettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_provider(self, payload: dict[str, Any], user_id: str | None) -> AiProviderSetting:
        row = self.session.scalar(select(AiProviderSetting).where(AiProviderSetting.provider == "openai"))
        if row is None:
            row = AiProviderSetting(provider="openai", enabled=True, daily_budget_usd=25, monthly_budget_usd=400)
            self.session.add(row)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_by_user_id = user_id
        self.session.flush()
        clear_config_cache()
        return row

    def upsert_feature(self, feature_key: str, payload: dict[str, Any], user_id: str | None) -> AiFeatureSetting:
        if feature_key not in DEFAULT_FEATURES:
            raise KeyError(feature_key)
        row = self.session.scalar(select(AiFeatureSetting).where(AiFeatureSetting.feature_key == feature_key))
        default = DEFAULT_FEATURES[feature_key]
        if row is None:
            row = AiFeatureSetting(
                feature_key=feature_key,
                enabled=default.enabled,
                max_requests_per_day=default.max_requests_per_day,
                max_output_tokens=default.max_output_tokens,
                cache_ttl_seconds=default.cache_ttl_seconds,
            )
            self.session.add(row)
        for key, value in payload.items():
            setattr(row, key, value)
        row.updated_by_user_id = user_id
        self.session.flush()
        clear_config_cache()
        return row

    def upsert_limit(self, payload: dict[str, Any], user_id: str | None) -> AiRequestLimit:
        row = self.session.scalar(
            select(AiRequestLimit).where(
                AiRequestLimit.subject_type == payload["subject_type"],
                AiRequestLimit.subject_key == payload["subject_key"],
            )
        )
        if row is None:
            row = AiRequestLimit(
                subject_type=payload["subject_type"],
                subject_key=payload["subject_key"],
                max_requests=payload["max_requests"],
                window_seconds=payload["window_seconds"],
            )
            self.session.add(row)
        else:
            row.max_requests = payload["max_requests"]
            row.window_seconds = payload["window_seconds"]
        row.updated_by_user_id = user_id
        self.session.flush()
        return row

    def list_limits(self) -> list[dict[str, Any]]:
        rows = list(
            self.session.scalars(
                select(AiRequestLimit).order_by(AiRequestLimit.subject_type, AiRequestLimit.subject_key)
            ).all()
        )
        return [
            {
                "subject_type": row.subject_type,
                "subject_key": row.subject_key,
                "max_requests": int(row.max_requests),
                "window_seconds": int(row.window_seconds),
            }
            for row in rows
        ]
