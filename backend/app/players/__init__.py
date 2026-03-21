from __future__ import annotations

from importlib import import_module

__all__ = ["PlayerSummaryProjector", "PlayerSummaryQueryService", "PlayerSummaryReadModel"]


def __getattr__(name: str):
    if name == "PlayerSummaryReadModel":
        module = import_module("app.players.read_models")
        return getattr(module, name)
    if name in {"PlayerSummaryProjector", "PlayerSummaryQueryService"}:
        module = import_module("app.players.service")
        return getattr(module, name)
    raise AttributeError(name)
