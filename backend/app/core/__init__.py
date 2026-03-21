from __future__ import annotations

from importlib import import_module

__all__ = ["ApplicationContext", "DomainModule", "build_application_context"]


def __getattr__(name: str):
    if name in {"ApplicationContext", "build_application_context"}:
        module = import_module("app.core.container")
        return getattr(module, name)
    if name == "DomainModule":
        module = import_module("app.core.module")
        return getattr(module, name)
    raise AttributeError(name)
