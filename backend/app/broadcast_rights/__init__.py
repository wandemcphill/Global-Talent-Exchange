from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["BroadcastRightsError", "BroadcastRightsService", "router"]


def __getattr__(name: str) -> Any:
    if name == "router":
        return import_module("app.broadcast_rights.router").router
    if name in {"BroadcastRightsError", "BroadcastRightsService"}:
        service = import_module("app.broadcast_rights.service")
        return getattr(service, name)
    raise AttributeError(name)
