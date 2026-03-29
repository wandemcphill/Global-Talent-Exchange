from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime_config.router import router
    from app.runtime_config.schemas import RuntimeConfigSnapshot, RuntimeConfigUpdateRequest
    from app.runtime_config.service import RuntimeConfigLoader, RuntimeConfigService, ensure_runtime_config_loader

__all__ = [
    "RuntimeConfigLoader",
    "RuntimeConfigService",
    "RuntimeConfigSnapshot",
    "RuntimeConfigUpdateRequest",
    "ensure_runtime_config_loader",
    "router",
]


def __getattr__(name: str):
    if name == "router":
        return import_module("app.runtime_config.router").router
    if name in {"RuntimeConfigSnapshot", "RuntimeConfigUpdateRequest"}:
        return getattr(import_module("app.runtime_config.schemas"), name)
    if name in {"RuntimeConfigLoader", "RuntimeConfigService", "ensure_runtime_config_loader"}:
        return getattr(import_module("app.runtime_config.service"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
