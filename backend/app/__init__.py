from __future__ import annotations

import sys


sys.modules.setdefault("app", sys.modules[__name__])


def __getattr__(name: str):
    if name in {"app", "create_app"}:
        from .main import app, create_app

        return {"app": app, "create_app": create_app}[name]
    raise AttributeError(name)


__all__ = ["app", "create_app"]
