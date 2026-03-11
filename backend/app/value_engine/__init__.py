from __future__ import annotations

from importlib import import_module

__all__ = [
    "DemandSignal",
    "GlobalScoutingIndexService",
    "InMemoryValueSnapshotRepository",
    "IngestionValueEngineBridge",
    "IngestionValueSnapshotRepository",
    "PlayerValueInput",
    "ScoutingIndexBreakdown",
    "ScoutingSignal",
    "TradePrint",
    "ValueBreakdown",
    "ValueEngine",
    "ValueEngineConfig",
    "ValueSnapshot",
    "ValueSnapshotJob",
    "ValueSnapshotRepository",
    "credits_from_real_world_value",
]


def __getattr__(name: str):
    if name == "ValueEngineConfig":
        module = import_module("backend.app.value_engine.config")
        return getattr(module, name)
    if name in {"InMemoryValueSnapshotRepository", "ValueSnapshotJob", "ValueSnapshotRepository"}:
        module = import_module("backend.app.value_engine.jobs")
        return getattr(module, name)
    if name in {
        "DemandSignal",
        "PlayerValueInput",
        "ScoutingIndexBreakdown",
        "ScoutingSignal",
        "TradePrint",
        "ValueBreakdown",
        "ValueSnapshot",
    }:
        module = import_module("backend.app.value_engine.models")
        return getattr(module, name)
    if name in {"GlobalScoutingIndexService", "ValueEngine", "credits_from_real_world_value"}:
        module = import_module("backend.app.value_engine.scoring")
        return getattr(module, name)
    if name in {"IngestionValueEngineBridge", "IngestionValueSnapshotRepository"}:
        module = import_module("backend.app.value_engine.service")
        return getattr(module, name)
    raise AttributeError(name)
