from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["LiveMatchError", "LiveMatchHub", "ensure_live_match_hub", "router"]


def __getattr__(name: str) -> Any:
    if name == "router":
        return import_module("app.live_matches.router").router
    if name in {"LiveMatchError", "LiveMatchHub", "ensure_live_match_hub"}:
        service = import_module("app.live_matches.service")
        return getattr(service, name)
    raise AttributeError(name)
