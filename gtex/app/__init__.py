from __future__ import annotations

import importlib

_backend_app = importlib.import_module("backend.app")

__all__ = getattr(_backend_app, "__all__", [])
__path__ = list(getattr(_backend_app, "__path__", []))

if __spec__ is not None:
    __spec__.submodule_search_locations = __path__


def __getattr__(name: str):
    return getattr(_backend_app, name)
