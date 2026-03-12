from __future__ import annotations

from backend.app.core.module import DomainModule
from backend.app.fast_cups.api.router import router

FAST_CUPS_MODULE = DomainModule(name="fast_cups", router=router)

__all__ = ["FAST_CUPS_MODULE"]
