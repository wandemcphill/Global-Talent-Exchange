from __future__ import annotations

from app.club_sale_market.service import ClubSaleMarketError, ClubSaleMarketService


class ClubSalePermissionError(ClubSaleMarketError, PermissionError):
    pass


class ClubSaleConflictError(ClubSaleMarketError):
    pass


class ClubSaleNotFoundError(ClubSaleMarketError, LookupError):
    pass


class ClubSaleService(ClubSaleMarketService):
    """Compatibility shim for legacy imports.

    Canonical club-sale business logic lives in backend.app.club_sale_market.service.
    """


__all__ = [
    "ClubSaleConflictError",
    "ClubSaleMarketError",
    "ClubSaleNotFoundError",
    "ClubSalePermissionError",
    "ClubSaleService",
]
