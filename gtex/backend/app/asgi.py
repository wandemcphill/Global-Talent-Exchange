from __future__ import annotations

from app.main import get_asgi_app

app = get_asgi_app()

__all__ = ["app"]
