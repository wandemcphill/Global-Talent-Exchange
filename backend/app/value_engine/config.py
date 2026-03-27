from __future__ import annotations

from app.core.config import Settings, ValueEngineWeightingConfig, get_settings

ValueEngineConfig = ValueEngineWeightingConfig


def get_value_engine_config(settings: Settings | None = None) -> ValueEngineConfig:
    resolved_settings = settings or get_settings()
    return resolved_settings.value_engine_weighting


__all__ = ["ValueEngineConfig", "get_value_engine_config"]
