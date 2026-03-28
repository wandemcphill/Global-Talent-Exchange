from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, tuple[str, str]] = {
    "BaseWorker": ("backend.app.workers.base_worker", "BaseWorker"),
    "RetryPolicy": ("backend.app.workers.base_worker", "RetryPolicy"),
    "WorkerEvent": ("backend.app.workers.base_worker", "WorkerEvent"),
    "RewardWorker": ("backend.app.workers.reward_worker", "RewardWorker"),
    "SimulationWorker": ("backend.app.workers.simulation_worker", "SimulationWorker"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, attribute_name)


__all__ = list(_EXPORTS)
