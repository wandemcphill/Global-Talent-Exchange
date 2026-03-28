from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, tuple[str, str]] = {
    "IntegrityScanWorker": ("app.workers.integrity_scan_worker", "IntegrityScanWorker"),
    "MediaRetentionWorker": ("app.workers.media_retention_worker", "MediaRetentionWorker"),
    "RewardWorker": ("app.workers.reward_worker", "RewardWorker"),
    "SimulationWorker": ("app.workers.simulation_worker", "SimulationWorker"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, attribute_name)


__all__ = list(_EXPORTS)
