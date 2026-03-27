from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["RegenUniverseError", "RegenUniverseService", "admin_router", "router"]


def __getattr__(name: str) -> Any:
    if name in {"router", "admin_router"}:
        module = import_module("app.regen_universe.router")
        return getattr(module, name)
    if name in {"RegenUniverseError", "RegenUniverseService"}:
        module = import_module("app.regen_universe.service")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
