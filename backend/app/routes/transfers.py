"""Transfer operations and Transfer Hub settlement routes.

Binds transfer operations and offer settlement to persistent database entities,
preventing caller-supplied price override or tampering (Finding ARCH-003 / NEW-002).
"""

from __future__ import annotations

from app.transfer_market.router import router

__all__ = ["router"]
