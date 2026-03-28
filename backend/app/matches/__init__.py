from __future__ import annotations

__all__ = ["router"]


def __getattr__(name: str):
    if name == "router":
        from app.matches.router import router

        return router
    raise AttributeError(f"module 'app.matches' has no attribute {name!r}")
