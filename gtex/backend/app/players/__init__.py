from __future__ import annotations

from importlib import import_module

__all__ = [
    "FootballPosition",
    "PlayerSummaryProjector",
    "PlayerSummaryQueryService",
    "PlayerSummaryReadModel",
    "calculate_gsi",
    "repairPlayerPositions",
    "repair_gsi_clusters",
]


def __getattr__(name: str):
    if name == "PlayerSummaryReadModel":
        module = import_module("app.players.read_models")
        return getattr(module, name)
    if name in {"PlayerSummaryProjector", "PlayerSummaryQueryService"}:
        module = import_module("app.players.service")
        return getattr(module, name)
    if name in {
        "FootballPosition",
        "calculate_gsi",
        "repairPlayerPositions",
        "repair_gsi_clusters",
    }:
        module = import_module("app.players.football_integrity")
        return getattr(module, name)
    raise AttributeError(name)
