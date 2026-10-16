from __future__ import annotations

def __getattr__(name: str):
    if name == "app":
        from . import app as backend_app

        return backend_app
    raise AttributeError(name)

__all__ = ["app"]
