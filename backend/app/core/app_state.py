from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.core.config import Settings


def get_optional_app_settings(app: FastAPI) -> Settings | None:
    settings = _coerce_settings(getattr(app.state, "settings", None))
    if settings is not None:
        return settings

    for attr_name in ("container", "context"):
        candidate = getattr(app.state, attr_name, None)
        settings = _coerce_settings(getattr(candidate, "settings", None))
        if settings is not None:
            return settings
    return None


def _coerce_settings(value: Any) -> Settings | None:
    if isinstance(value, Settings):
        return value
    return None


__all__ = ["get_optional_app_settings"]
